# Football Business Analytics - descriptive results

Generated with `python football_warehouse.py report --warehouse outputs/warehouse.sqlite` after building from `database.sqlite` (SHA-256 `4df8569777d59fdd690754b1cc8ca1f7989baf65f2eaddd0f1368285f11139a9`). See the README for source and interpretation limits.

Match-team rows: 51,958; player-season rows: 70,250.

Recorded possession is available for 8,419 of 25,979 matches. Parsed player events yield 38,557 goals and 16,998 assists.

## Home possession by result

| Result | Matches with possession | Mean home possession |
| --- | ---: | ---: |
| Draw | 2,101 | 51.2% |
| Loss | 2,415 | 49.5% |
| Win | 3,903 | 52.9% |

## Average total goals per match by season

| Season | Matches | Mean goals |
| --- | ---: | ---: |
| 2008/2009 | 3,326 | 2.61 |
| 2009/2010 | 3,230 | 2.67 |
| 2010/2011 | 3,260 | 2.68 |
| 2011/2012 | 3,220 | 2.72 |
| 2012/2013 | 3,260 | 2.77 |
| 2013/2014 | 3,032 | 2.77 |
| 2014/2015 | 3,325 | 2.68 |
| 2015/2016 | 3,326 | 2.75 |

## Player attributes and recorded goals

Pearson correlation across player-season rows with an attribute snapshot; zero recorded goals may include missing XML events.

| Attribute | Rows | Correlation with goals |
| --- | ---: | ---: |
| overall_rating | 70,215 | 0.325 |
| finishing | 70,215 | 0.301 |
| reactions | 70,215 | 0.293 |
| volleys | 68,697 | 0.286 |
| positioning | 70,215 | 0.261 |
| ball_control | 70,215 | 0.256 |
| vision | 68,697 | 0.224 |
| short_passing | 70,215 | 0.220 |
| long_passing | 70,215 | 0.126 |
| interceptions | 70,215 | -0.024 |
| standing_tackle | 70,215 | -0.066 |
| sliding_tackle | 68,697 | -0.082 |
| marking | 70,215 | -0.095 |

These are associations, not causal effects. XML event coverage varies across the dataset.
