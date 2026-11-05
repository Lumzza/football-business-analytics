# Football Business Analytics

Reproducible ETL and descriptive analysis of the [European Soccer Database](https://www.kaggle.com/datasets/hugomathien/soccer). This is a cleaned, independently runnable implementation of the university group project's data warehouse work. My contribution focused on XML extraction, data cleaning, and preparing the analytical tables. The original group notebook and presentation are retained locally outside this repository.

## Questions

1. Which player attributes are associated with goals and assists per season?
2. How does home possession differ across match results?
3. How did average goals per match change by season?

## Run

Python 3.10+ is sufficient; no third-party package is required.

1. Download `database.sqlite` from the dataset page above. Its database is licensed separately from this code. Do not commit the database.
2. Build the star-schema data mart:

   ```bash
   python football_warehouse.py build --source path/to/database.sqlite --output outputs/warehouse.sqlite
   ```

3. Print descriptive results:

   ```bash
   python football_warehouse.py report --warehouse outputs/warehouse.sqlite
   ```

The source database is read-only. `build` creates a new output file and refuses to overwrite one unless `--replace` is given.

## Model

| Table | Grain | Contents |
| --- | --- | --- |
| `dim_player` | player | ID and name |
| `dim_team` | team | ID and name |
| `dim_league` | league | ID and name |
| `dim_season` | season | season label |
| `fact_player_season` | player × season | average attributes, XML-derived goals and assists |
| `fact_match_team` | match × team | score, result, final recorded possession |

The goal parser reads XML elements, skips malformed records, and does not count own goals as a player's scoring contribution. Missing possession remains `NULL`. Player attribute snapshots are averaged within the July–June season. Goals and assists are counted from the recorded XML, which is incomplete for some leagues and seasons.

## Interpretation limits

The analysis is descriptive. Correlations do not establish which skills *cause* scoring. Possession is recorded during a match, so it is not a pre-match predictor, and the data do not establish a possession threshold required to win. The dataset covers historical seasons and may have missing or inconsistent event records. See `RESULTS.md` for figures calculated from the local source file.

## Provenance

Source: Hugo Mathien, [European Soccer Database](https://www.kaggle.com/datasets/hugomathien/soccer), 2008–2016. The source page asks users to avoid commercial use and labels the database and contents separately. This repository contains only original code and derived aggregate results; it does not redistribute the source database or EA Sports assets.
