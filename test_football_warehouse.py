"""Focused checks for the XML transformations used by the data mart."""

import unittest

from football_warehouse import final_possession, goal_events, season_for


class WarehouseParsingTests(unittest.TestCase):
    def test_season_boundary(self):
        self.assertEqual(season_for("2012-06-30"), "2011/2012")
        self.assertEqual(season_for("2012-07-01"), "2012/2013")

    def test_final_possession_uses_latest_valid_event(self):
        xml = (
            "<possession><value><elapsed>90</elapsed><homepos>0</homepos>"
            "<awaypos>100</awaypos></value><value><elapsed>45</elapsed>"
            "<homepos>60</homepos><awaypos>40</awaypos></value></possession>"
        )
        self.assertEqual(final_possession(xml), (0, 100))
        self.assertEqual(final_possession("<broken"), (None, None))

    def test_goal_parser_ignores_own_goals_and_bad_ids(self):
        xml = (
            "<goal><value><type>goal</type><comment>n</comment><player1>42</player1>"
            "<player2>7</player2></value><value><type>goal</type><comment>o</comment>"
            "<player1>9</player1></value><value><type>goal</type>"
            "<player1>invalid</player1></value></goal>"
        )
        self.assertEqual(list(goal_events(xml)), [(42, 7)])
        self.assertEqual(list(goal_events("<broken")), [])


if __name__ == "__main__":
    unittest.main()
