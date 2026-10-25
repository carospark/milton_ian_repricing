# Milton and Ian research handoff

## Objective and scope

Descriptive, exploratory CUSIP-level study of Milton (Florida landfall 2024-10-09), focused on changing expectations, repricing and possible recovery, and Ian (Florida landfall 2022-09-28), focused on concentrated downside losses. This session built local sample audits and a small coverage comparison across other US hurricane landfalls. No regressions or figures were run. Case selection in the comparison is based on geography and data coverage, not bond-price movements.

## Verified project state

At session start on 2026-10-25 the project was at clean scaffold commit `aaf4c04`; README, `config.yaml`, `pyproject.toml`, `src/milton_ian/paths.py`, and `load.py` existed, while `sample.py` did not. The configured local source paths resolve except NHC archives, which are not configured. Initial state verified from Git and `./.venv/bin/python -m milton_ian.paths`. This session added sample, contract and comparison modules, tests, compact whitelisted summaries, documentation and this handoff. The resulting commit ID is recorded in Git after this handoff is committed.

## Inputs and schemas

Read-only repositories: `/Users/caropark/cat-bond-issuance` and `/Users/caropark/cat-bond-flow-analysis`. The project readers/config specify TRACE trade-level `trace_trades_clean.csv`, strict bridge `data/bridge.csv`, separate programme bridge `bridge_program.csv`, deals/perils/triggers, `issuance/data/tranches.csv`, N-PORT holdings/title data, hazard-region mapping, weekly market activity and prediction-market archive. Prediction SQLite is `/Users/caropark/cat-bond-flow-analysis/data/raw/tier1/prediction_market_history.sqlite3`, opened read-only. Flow source was traced to `src/event_check.py::weekly_market` and `build_deal_panel.py::aggregate_market_classes`.

Verified source facts: strict bridge keys are deal URL and CUSIP; no duplicate bridge pairs in the audited input. High/medium/low rows: 870/322/4. `title_evidence == propagated` marks propagated pairs. TRACE cleaner documentation and source use confirm `contra_party=C` customer, `D` inter-dealer; `A` and `T` are left other/unknown. `dealer_side=S` means dealer sold/customer bought; `B` means customer sold. The audited TRACE extract has 68,759 rows (C 67,049; A 1,011; D 698; T 1). Event-window inter-dealer count is zero for Milton and Ian; this describes this extract only. N-PORT title classes are parser-supported mappings, not hand verification. Unresolved/conflicting class stays unknown; no unsupported EL or attachment probability is assigned.

Project plan and walkthrough were treated as background. They were not copied into the repository.

## Definitions and implementation

All storm windows are inclusive landfall-45 through landfall+60 calendar days. Pre trades are strictly before landfall; landfall day is separate; post trades strictly after. The configured event interval is landfall-4 through +3 inclusive (eight days), not a seven-day week. Sample rows are one per CUSIP. Strict eligibility requires a single high-confidence non-programme bridge match and excludes title-propagated pairs. Trade metrics aggregate by CUSIP before bridge attribution to prevent join multiplication. At least three customer trades on each side uses these strict pre/post counts. Buy and sell volume use customer-side interpretation above; net customer imbalance is buys minus sells. Prices are observed TRACE trade prices only; no forward fill or synthetic trade days. Storm-week density is observed customer CUSIP-trade-days / (eligible CUSIPs × 8). Missing/unknown exposure is distinct from mapped no-hurricane exposure.

Prediction probability observations are actual non-null Yes-outcome prices. Polymarket token IDs are mapped using outcome metadata; points are token prices, not trades. Kalshi observations are daily Yes candle closes, not executions, assigned to the prior Eastern calendar date. CUSIP overlap compares the Eastern observation date with an actual bond trade date; this does not establish intraday ordering. The chart activity measure is not a probability. Platform activity sizes (Kalshi contract counts and Polymarket token-share sizes) are not dollar notional.

## Completed outputs and reproducible commands

Code: `src/milton_ian/sample.py`, `contracts.py`, `compare.py`; tests in `tests/test_audit.py`. Comparison storm selection and event definitions are in `config_comparison.yaml`. Compact tracked outputs: `data/derived/coverage_summary_milton.csv`, `coverage_summary_ian.csv`, `hurricane_coverage_comparison.csv`, and `comparison_contracts.csv`. Definitions, compact comparison table and recommendations are in `docs/Hurricane_Coverage_Comparison.md`. Detailed trade/CUSIP tables and other raw-derived outputs remain gitignored. `.gitignore` whitelists only the small named summaries/contract metadata inventory; raw, licensed and trade-derived detailed outputs remain ignored.

Reproduce from project root:

```sh
./.venv/bin/python -m milton_ian.sample
./.venv/bin/python -m milton_ian.compare
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python -m compileall -q src tests
git diff --check
```

Checks include unique CUSIP rows, no bridge row multiplication, strict eligibility, exposure partition, trade count/volume reconciliation, directional/missing-data behavior, class ambiguity, outcome identity, Eastern date overlap, and timestamp/category behavior. The eight focused tests passed. Compile and whitespace checks passed.

## Milton and Ian sample coverage

| Storm | Window | Unique traded CUSIPs | Strict eligible CUSIPs | Eligible deals (distinct) | ≥3 customer trades before and after | Relevant Florida-hurricane exposed | Mapped no-hurricane unexposed | Other hurricane region | Unknown/ambiguous exposure | Parsed N-PORT class match |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Milton | 2024-08-25–2024-12-08 | 115 | 89 | 70 | 4 | 41 | 18 | 17 | 13 | 79 |
| Ian | 2022-08-14–2022-11-27 | 106 | 81 | 64 | 7 | 40 | 20 | 12 | 9 | 67 |

CUSIPs, bridge pairs and deals are separate counts. The eight-day density is 4/712 = 0.0056 customer CUSIP-days per eligible-CUSIP-day for Milton and 5/648 = 0.0077 for Ian; zero CUSIPs trade on at least two event-interval dates in either eligible sample. All 924 Milton window TRACE trades reconcile to 915 C plus 9 A; value totals `$4,486,472,459.12`. Ian's 617 trades reconcile to 596 C plus 21 A; value totals `$1,409,490,000`. D count is zero in both windows. No trade is multiplied by mapping joins.

## Milton activity chart and contract audit

The archived chart's hurricane filter, Florida/US region selection, date range, weekly bin and traded-size definitions were traced to source functions. Chart week zero is seven UTC dates from the landfall date through +6; it is distinct from the eight-day event interval. Saved chart volume of 2,370,453.948228 equals the recomputed weekly class/region-expanded value within 2.4e-10. Unique source contract activity is 2,256,239.948228; 114,214 is duplicated because Florida contracts tagged both Florida and US are expanded and counted twice. The approx 2.3m chart figure is reproduced, with this duplicate-tag explanation. Week zero has 36 contributors. Broad seasonal counts dominate (about 2.068m expanded size); 20 geographic seasonal strike contracts contribute 228,428 expanded vs 114,214 unique; a broad multi-storm Cat 5 market contributes about 73,857; other geographic strikes about 524. Units combine Kalshi contract counts and Polymarket token-share size, not notional dollars.

A full local metadata search covered 328,663 SQLite contracts and nested IDs/event/group/title/rules. It found no Milton metadata matches. This means no explicit Milton contract in the local archive, not confirmed market nonexistence. Tampa Kalshi thresholds such as `HURTB-24NOV30-T74` resolve to a season-long city wind report between June 18 and Nov 30, 2024, not a Milton outcome. The 19 applicable local seasonal city-strike contracts are proxies; one broad Cat 5 before-election market is multi-storm, not Milton-specific. Seasonal price histories overlap actual trade dates for 72 eligible Milton CUSIPs; no storm-specific contract overlap exists. Do not substitute the seasonal city-strike probability for a Milton-specific probability.

Beryl is a comparison case with two storm-specific Polymarket markets: “Will Beryl hit US as a hurricane?” and “Will Beryl hit the US as a tropical storm?” Each has 123 non-null Yes price-history observations during the event interval; 23 eligible CUSIPs overlap a probability date, two repeatedly within the eight-day interval. Those markets measure conterminous-US landfall status, not Texas loss severity. Idalia has two storm-specific Florida landfall/intensity markets, but only nine eligible CUSIPs overlap any observed probability date and none repeatedly overlaps during the event interval. Exact metadata, rules, timestamps, outcome IDs and coverage are saved in `comparison_contracts.csv`.

## Cross-storm screen and recommendations

The targeted screen includes Hermine, Irma, Michael, Laura, Ida, Ian, Nicole, Idalia, Debby (tropical storm landfall), Helene, Milton and Beryl. Full counts and definitions are in the compact comparison CSV and Markdown note. Beryl has the strongest local storm-specific expectations-market availability, but only two repeatedly matched CUSIPs, broad US geography, and windows overlapping Debby, Helene and Milton. Idalia is the strongest Florida-specific market alternative with sparse matched probability coverage. Milton remains suitable for descriptive repricing/recovery, but an expectations leg needs targeted archived NHC forecast/wind-probability snapshots or suitable newly acquired market data. Ian remains suitable for concentrated loss analysis, although its window overlaps Nicole and has seven balanced-trading CUSIPs. Ida merits a closer audit: 127 eligible CUSIPs, 51 relevant exposure, 44 title class plus relevant exposure, and seven balanced CUSIPs; the local issuance loss table records direct high-confidence total-loss entries across three Ida deals and three Ian deals. These are loss-source labels, not results from bond-price analysis. Do not automatically replace Milton or Ian.

No NHC forecast or wind-probability files were found in local project, source repositories or Downloads inventory checked. Official timestamped archives are indexed for priority storms, including [Beryl](https://www.nhc.noaa.gov/archive/2024/al02/), [Idalia](https://www.nhc.noaa.gov/archive/2023/al10/), [Ian](https://www.nhc.noaa.gov/archive/2022/al09/), [Helene](https://www.nhc.noaa.gov/archive/2024/al09/) and [Milton](https://www.nhc.noaa.gov/archive/2024/al14/); NHC describes [wind-probability graphics](https://www.nhc.noaa.gov/aboutnhcgraphics.shtml) and provides a [GIS wind-probability archive](https://www.nhc.noaa.gov/gis/archive_wsp.php). The files are potentially obtainable; per-advisory completeness, timestamps and horizon definitions are not yet verified. No NHC product is confirmed unavailable.

Next: (1) inventory and validate a small NHC advisory/WSP panel for Beryl, Idalia, Milton, Ian and Ida; preserve release time, location and cumulative horizon; (2) manually verify tranche/class and deal exposure for CUSIPs prioritized by observed relevant exposure; (3) decide whether the expectations question requires market-implied named-storm probability specifically, and only then plan targeted additional market collection. Maintain the distinction between “not in the local archive,” “not searched,” and “confirmed unavailable.”

## Confirmed versus unresolved

Confirmed: original scaffold state/commit; source schemas and trade-side definitions; bridge eligibility and uniqueness; Milton/Ian coverage counts; trade and value reconciliation; eight-day configured interval; source definition and volume reconciliation of chart week zero; local archive search outcome; contract probability outcome semantics and date overlap; no NHC files in the local inventories checked; comparison tests passed.

Approximated or source-limited: chart duplicated region activity is explained and numerically reproduced; platform size units are not dollar volume. N-PORT class matches use parsed titles; exposure tags are broad. Calendar-day contract/trade overlap cannot establish intraday precedence. Comparison is targeted, not exhaustive.

Unresolved: full NHC archive snapshot inventory and QA; any delisted/uncollected prediction contracts; hand-verified CUSIP-to-tranche/exposure linkage; whether to acquire more named-storm prediction histories; and final case choice after NHC coverage review.

## Session continuity instructions

At session start, read this handoff and verify relevant files/state before relying on it. Before ending, update this handoff with completed work, reproducible commands, verified findings, unresolved items and next actions. Do not place personal user-level context here.
