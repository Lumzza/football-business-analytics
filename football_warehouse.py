"""Build a small star-schema data mart from the European Soccer Database."""

from __future__ import annotations

import argparse
import math
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ATTRIBUTES = (
    "overall_rating", "finishing", "volleys", "positioning", "reactions",
    "vision", "ball_control", "short_passing", "long_passing", "marking",
    "standing_tackle", "sliding_tackle", "interceptions",
)


def season_for(date_text: str) -> str:
    year, month = int(date_text[:4]), int(date_text[5:7])
    start = year if month >= 7 else year - 1
    return f"{start}/{start + 1}"


def xml_values(xml_text: str | None):
    if not xml_text:
        return []
    try:
        return ET.fromstring(xml_text).findall(".//value")
    except ET.ParseError:
        return []


def final_possession(xml_text: str | None) -> tuple[int | None, int | None]:
    observations = []
    for value in xml_values(xml_text):
        try:
            elapsed = int(value.findtext("elapsed") or -1)
            extra = int(value.findtext("elapsed_plus") or 0)
            home_text = value.findtext("homepos")
            away_text = value.findtext("awaypos")
            home = int(home_text if home_text is not None else value.findtext("stats/homepos"))
            away = int(away_text if away_text is not None else value.findtext("stats/awaypos"))
            if 0 <= home <= 100 and 0 <= away <= 100:
                observations.append(((elapsed, extra), home, away))
        except (TypeError, ValueError):
            continue
    if not observations:
        return None, None
    _, home, away = max(observations, key=lambda item: item[0])
    return home, away


def goal_events(xml_text: str | None):
    for value in xml_values(xml_text):
        if value.findtext("type") != "goal":
            continue
        if (value.findtext("comment") or "").strip().lower() in {"o", "own goal"}:
            continue
        try:
            scorer = int(value.findtext("player1"))
        except (TypeError, ValueError):
            continue
        try:
            assist = int(value.findtext("player2"))
        except (TypeError, ValueError):
            assist = None
        yield scorer, assist


SCHEMA = """
CREATE TABLE dim_player (player_id INTEGER PRIMARY KEY, player_name TEXT NOT NULL);
CREATE TABLE dim_team (team_id INTEGER PRIMARY KEY, team_name TEXT NOT NULL);
CREATE TABLE dim_league (league_id INTEGER PRIMARY KEY, league_name TEXT NOT NULL);
CREATE TABLE dim_season (season TEXT PRIMARY KEY);
CREATE TABLE fact_player_season (
    player_id INTEGER NOT NULL, season TEXT NOT NULL,
    attribute_snapshots INTEGER NOT NULL, goals INTEGER NOT NULL, assists INTEGER NOT NULL,
    overall_rating REAL, finishing REAL, volleys REAL, positioning REAL,
    reactions REAL, vision REAL, ball_control REAL, short_passing REAL,
    long_passing REAL, marking REAL, standing_tackle REAL, sliding_tackle REAL,
    interceptions REAL,
    PRIMARY KEY (player_id, season)
);
CREATE TABLE fact_match_team (
    match_id INTEGER NOT NULL, team_id INTEGER NOT NULL, league_id INTEGER NOT NULL,
    season TEXT NOT NULL, match_date TEXT NOT NULL, venue TEXT NOT NULL,
    goals_for INTEGER NOT NULL, goals_against INTEGER NOT NULL,
    result TEXT NOT NULL, possession INTEGER,
    PRIMARY KEY (match_id, team_id)
);
CREATE INDEX idx_player_season ON fact_player_season(season);
CREATE INDEX idx_match_season ON fact_match_team(season);
CREATE INDEX idx_match_league ON fact_match_team(league_id);
"""


def build(source_path: Path, output_path: Path, replace: bool = False) -> None:
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("Source and output paths must differ")
    if output_path.exists() and not replace:
        raise FileExistsError(f"{output_path} already exists; use --replace")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    source = sqlite3.connect(f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True)
    warehouse = sqlite3.connect(output_path)
    try:
        warehouse.executescript(SCHEMA)
        warehouse.executemany("INSERT INTO dim_player VALUES (?, ?)", source.execute(
            "SELECT player_api_id, player_name FROM Player WHERE player_api_id IS NOT NULL"))
        warehouse.executemany("INSERT INTO dim_team VALUES (?, ?)", source.execute(
            "SELECT team_api_id, team_long_name FROM Team WHERE team_api_id IS NOT NULL"))
        warehouse.executemany("INSERT INTO dim_league VALUES (?, ?)", source.execute(
            "SELECT id, name FROM League"))

        goals, assists = Counter(), Counter()
        match_rows = []
        seasons = set()
        for match_id, date, season, league, home_team, away_team, home_goals, away_goals, goal_xml, possession_xml in source.execute(
            "SELECT match_api_id, date, season, league_id, home_team_api_id, away_team_api_id, "
            "home_team_goal, away_team_goal, goal, possession FROM Match"
        ):
            if not all(x is not None for x in (match_id, date, season, league, home_team, away_team, home_goals, away_goals)):
                continue
            seasons.add(season)
            for scorer, assist in goal_events(goal_xml):
                goals[(scorer, season)] += 1
                if assist is not None:
                    assists[(assist, season)] += 1
            home_pos, away_pos = final_possession(possession_xml)
            home_result = "Win" if home_goals > away_goals else "Loss" if home_goals < away_goals else "Draw"
            away_result = "Loss" if home_result == "Win" else "Win" if home_result == "Loss" else "Draw"
            match_rows.extend(((match_id, home_team, league, season, date, "Home", home_goals, away_goals, home_result, home_pos),
                               (match_id, away_team, league, season, date, "Away", away_goals, home_goals, away_result, away_pos)))
        warehouse.executemany("INSERT INTO fact_match_team VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", match_rows)

        season_expr = "(CASE WHEN CAST(substr(date, 6, 2) AS INTEGER) >= 7 THEN substr(date, 1, 4) ELSE CAST(CAST(substr(date, 1, 4) AS INTEGER) - 1 AS TEXT) END)"
        averages = ", ".join(f"AVG({name})" for name in ATTRIBUTES)
        attributes = {}
        for row in source.execute(
            f"SELECT player_api_id, {season_expr}, COUNT(*), {averages} "
            "FROM Player_Attributes WHERE player_api_id IS NOT NULL AND date IS NOT NULL "
            "GROUP BY player_api_id, " + season_expr
        ):
            player_id, year, count, *values = row
            season = f"{year}/{int(year) + 1}"
            attributes[(player_id, season)] = (count, *values)
            seasons.add(season)
        warehouse.executemany("INSERT INTO dim_season VALUES (?)", ((s,) for s in sorted(seasons)))
        keys = set(attributes) | set(goals) | set(assists)
        valid_players = {r[0] for r in warehouse.execute("SELECT player_id FROM dim_player")}
        warehouse.executemany(
            "INSERT INTO fact_player_season VALUES (" + ",".join("?" for _ in range(5 + len(ATTRIBUTES))) + ")",
            ((player, season, (attributes.get((player, season)) or (0, *([None] * len(ATTRIBUTES))))[0],
              goals[(player, season)], assists[(player, season)],
              *(attributes.get((player, season)) or (0, *([None] * len(ATTRIBUTES))))[1:])
             for player, season in sorted(keys) if player in valid_players),
        )
        warehouse.commit()
    finally:
        source.close()
        warehouse.close()


def report(path: Path) -> None:
    with sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True) as db:
        print("# Football Business Analytics - descriptive results\n")
        counts = [db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("fact_match_team", "fact_player_season")]
        print(f"Match-team rows: {counts[0]:,}; player-season rows: {counts[1]:,}.\n")
        covered = db.execute("SELECT COUNT(*) FROM fact_match_team WHERE venue='Home' AND possession IS NOT NULL").fetchone()[0]
        goals, assists = db.execute("SELECT SUM(goals), SUM(assists) FROM fact_player_season").fetchone()
        print(f"Recorded possession is available for {covered:,} of {counts[0] // 2:,} matches. "
              f"Parsed player events yield {goals:,} goals and {assists:,} assists.\n")
        print("## Home possession by result\n")
        print("| Result | Matches with possession | Mean home possession |\n| --- | ---: | ---: |")
        for result, count, mean in db.execute(
            "SELECT result, COUNT(*), AVG(possession) FROM fact_match_team "
            "WHERE venue='Home' AND possession IS NOT NULL GROUP BY result ORDER BY result"
        ):
            print(f"| {result} | {count:,} | {mean:.1f}% |")
        print("\n## Average total goals per match by season\n")
        print("| Season | Matches | Mean goals |\n| --- | ---: | ---: |")
        for season, count, mean in db.execute(
            "SELECT season, COUNT(*), AVG(goals_for + goals_against) FROM fact_match_team "
            "WHERE venue='Home' GROUP BY season ORDER BY season"
        ):
            print(f"| {season} | {count:,} | {mean:.2f} |")
        print("\n## Player attributes and recorded goals\n")
        print("Pearson correlation across player-season rows with an attribute snapshot; zero recorded goals may include missing XML events.\n")
        print("| Attribute | Rows | Correlation with goals |\n| --- | ---: | ---: |")
        correlations = []
        for attribute in ATTRIBUTES:
            pairs = list(db.execute(
                f"SELECT {attribute}, goals FROM fact_player_season "
                f"WHERE attribute_snapshots > 0 AND {attribute} IS NOT NULL"
            ))
            n = len(pairs)
            sx = sum(x for x, _ in pairs)
            sy = sum(y for _, y in pairs)
            sxx = sum(x * x for x, _ in pairs)
            syy = sum(y * y for _, y in pairs)
            sxy = sum(x * y for x, y in pairs)
            denominator = (n * sxx - sx * sx) * (n * syy - sy * sy)
            correlation = (n * sxy - sx * sy) / math.sqrt(denominator) if denominator > 0 else float("nan")
            correlations.append((attribute, n, correlation))
        for attribute, n, correlation in sorted(correlations, key=lambda row: row[2], reverse=True):
            print(f"| {attribute} | {n:,} | {correlation:.3f} |")
        print("\nThese are associations, not causal effects. XML event coverage varies across the dataset.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build")
    build_parser.add_argument("--source", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--replace", action="store_true")
    report_parser = commands.add_parser("report")
    report_parser.add_argument("--warehouse", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        build(args.source, args.output, args.replace)
        print(f"Built {args.output}")
    else:
        report(args.warehouse)


if __name__ == "__main__":
    main()
