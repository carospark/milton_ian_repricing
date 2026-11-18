# Current status: four-storm research pipeline

The selected sample is Ian, Milton, Idalia and Beryl. The dated updates at the end supersede historical recommendations and availability statements below. The public briefing is aggregate-only; detailed local examples are preserved under ignored data/derived/Hurricane_Options_Story_private.html.

# Milton and Ian research handoff

## Objective and scope

Descriptive, exploratory CUSIP-level study of Milton (Florida landfall 2024-10-09), focused on changing expectations, repricing and possible recovery, and Ian (Florida landfall 2022-09-28), focused on concentrated downside losses. This session built local sample audits and a small coverage comparison across other US hurricane landfalls. No regressions or figures were run. Case selection in the comparison is based on geography and data coverage, not bond-price movements.

## Verified project state

At session start on 2026-10-25 the project was at clean scaffold commit `aaf4c04`; README, `config.yaml`, `pyproject.toml`, `src/milton_ian/paths.py`, and `load.py` existed, while `sample.py` did not. The configured local source paths resolve except NHC archives, which are not configured. Initial state verified from Git and `./.venv/bin/python -m milton_ian.paths`. This session added sample, contract and comparison modules, tests, compact whitelisted summaries, documentation and this handoff. The resulting commit ID is recorded in Git after this handoff is committed.

## Inputs and schemas

Read-only repositories: `/Users/caropark/projects/cat-bond-issuance` and `/Users/caropark/projects/cat-bond-flow-analysis`. The project readers/config specify TRACE trade-level `trace_trades_clean.csv`, strict bridge `data/bridge.csv`, separate programme bridge `bridge_program.csv`, deals/perils/triggers, `issuance/data/tranches.csv`, N-PORT holdings/title data, hazard-region mapping, weekly market activity and prediction-market archive. Prediction SQLite is `/Users/caropark/cat-bond-flow-analysis/data/raw/tier1/prediction_market_history.sqlite3`, opened read-only. Flow source was traced to `src/event_check.py::weekly_market` and `build_deal_panel.py::aggregate_market_classes`.

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

## Story briefing deliverable (2026-10-26)

Created `docs/Hurricane_Options_Story.html`, a self-contained HTML briefing with the twelve-storm comparison, selected literal TRACE trade records for the Milton and Ian event intervals, one-row-per-CUSIP summary teasers, and archived Yes-outcome observation teasers for Beryl, Idalia and the Tampa seasonal proxy. It is generated from the committed comparison/contract outputs plus a read-only refresh of the configured TRACE sample and prediction SQLite. The file includes scope, interpretation and selection limitations; it deliberately shows only representative rows, not the complete licensed/trade-derived sample. It is under `docs/`, outside the existing `notebooks/*.html` ignore pattern.

Rebuild prerequisites and command: run `./.venv/bin/python -m milton_ian.sample` first, then run `PYTHONPATH=src ./.venv/bin/python scripts/build_story_report.py`. HTML parser sanity check confirmed eight tables and 57 table rows. Main interpretation: Beryl has the best local storm-specific market/bond-date overlap, but repeat event-week overlap is only two CUSIPs; Milton’s local contract histories are seasonal proxies; Ian has source loss evidence while Ida has wider bond coverage and also merits an audit. The sample teasers use actual records and clearly separate broad-window price ranges from dated trade observations.

## Confirmed versus unresolved

Confirmed: original scaffold state/commit; source schemas and trade-side definitions; bridge eligibility and uniqueness; Milton/Ian coverage counts; trade and value reconciliation; eight-day configured interval; source definition and volume reconciliation of chart week zero; local archive search outcome; contract probability outcome semantics and date overlap; no NHC files in the local inventories checked; comparison tests passed.

Approximated or source-limited: chart duplicated region activity is explained and numerically reproduced; platform size units are not dollar volume. N-PORT class matches use parsed titles; exposure tags are broad. Calendar-day contract/trade overlap cannot establish intraday precedence. Comparison is targeted, not exhaustive.

Unresolved: full NHC archive snapshot inventory and QA; any delisted/uncollected prediction contracts; hand-verified CUSIP-to-tranche/exposure linkage; whether to acquire more named-storm prediction histories; and final case choice after NHC coverage review.

## Session continuity instructions

At session start, read this handoff and verify relevant files/state before relying on it. Before ending, update this handoff with completed work, reproducible commands, verified findings, unresolved items and next actions. Do not place personal user-level context here.


## Four-storm study started (2026-11-17)

Selected research sample: Ian, Milton, Idalia and Beryl only, defined in config_study.yaml. Historical twelve-storm comparison retained for screening and competing-event context. Existing working-tree changes to config.yaml and this handoff were preserved.

Rebuilt sample and comparison from configured read-only sources. Fixed story generation to show only selected storms and corrected full-window versus eight-day trade-total labels, Milton example count (eight trades, four dates), and inclusive window length (106 days). README now distinguishes proposed research questions from findings.

Added milton_ian.nhc: official forecast-advisory cache with source URL, SHA256, number, stated UTC issue time and correction flag. Acquired all index-listed forecast advisories: Ian 1-38, Milton 1-23, Idalia 1-29, Beryl 1-50 (140 total). Three are corrected archive versions; issue times do not establish first public availability. WSP products not yet acquired.

Added milton_ian.study: gitignored observed-trade panel, information-event inventory, four-storm coverage, mapping review queue and reconciliation JSON. Timeline contains 808 events. Eligible customer trades in event-8: Ian 19 on 5 CUSIP-days; Milton 8 on 4; Idalia 22 on 11; Beryl 103 on 41. Full-window eligible customer trades: 440, 719, 702, 1443 respectively. These are not all-extract trade counts.

Reproduce: ./.venv/bin/python -m milton_ian.compare; ./.venv/bin/python -m milton_ian.sample; ./.venv/bin/python -m milton_ian.nhc; ./.venv/bin/python -m milton_ian.study; ./.venv/bin/python scripts/build_story_report.py. All ten unittest cases passed; observed trades reconcile to CUSIP details and event-day coverage; HTML parser and whitespace checks passed.

Next: WSP inventory and numerical forecast parsing; verify TRACE clock semantics before intraday joins; manually verify prioritized CUSIP/tranche/exposure mappings. The current timeline is an inventory, not a verified information-before-trade match or causal study. Detailed outputs and raw caches remain gitignored. No source-repository writes, commits, or regressions.


## Wind-probability acquisition and Beryl source review (2026-11-17)

Added milton_ian.wsp with pyshp dependency. Cached official GIS archive index and 141 half-degree 0-120h cumulative WSP ZIPs over nine UTC dates per selected storm (-7 through +1). Ian/Milton/Idalia each have 36/36 expected cycles; Beryl has 33/36. July 9 2024 06/12/18 UTC are not listed in cached index, not confirmed globally unavailable. ZIP thresholds 34/50/64 knots sampled at two prespecified exact grid points per storm: 846 rows, 471 observed and 375 missing. Missing points and absent entire threshold layers are not imputed zero. Source metadata states these are ALL-BASIN, ALL-ACTIVE-STORM products, not named-storm probabilities. Cycle initialization is not publication time. Location samples are contextual, not bond exposure weights. Threshold monotonicity passes wherever both values are observed.

Added milton_ian.review. Read cached Artemis deal prose in issuance/raw without source writes. Original 23 Beryl same-date-overlap bonds: explicit Texas scope 3; broad US scope/weights unverified 8; regional scope outside Texas 10; Texas excluded 1; no US named-storm peril 1. Both repeat event-week bonds are in broad-US category, neither in explicit Texas. Evidence, hashes, bridge rows and dated N-PORT class support stored in gitignored beryl_mapping_source_review.csv. Broad-screen misclassifications include Texas-only Alamo as other-region, Louisiana-only Bayou as relevant, and Astro broad-US peril text omitting southeastern state scope. Montoya parsed trigger says Indemnity but cached prose says PCS industry loss index: unresolved conflict. No hand-verified CUSIP/tranche/exposure pairs claimed; offering terms, amendments and active coverage remain unverified. Original coverage table intentionally retained as historical broad screen.

Added milton_ian.match. Only actual named-market Yes observations on preceding Eastern date matched to customer trades; no same-day information, forward fill, or carry across missing dates. Output has explicit trade-row IDs for deduplication across contracts. Beryl window: 81 distinct customer trades/27 CUSIPs; event-8 79/26; prelandfall event-8 only 2 trades/1 CUSIP. Idalia: 18 trades/8 CUSIPs, all event-8; prelandfall 6 trades/3 CUSIPs. These timing-rule samples differ from original 23/9 same-date samples; source review is not complete for newly matched bonds. SOURCE cleaner proves trade_time maps execution-time field, not report time; timezone still unverified. No intraday joins asserted.

Story generator and HTML updated with acquisition/review/timing sections; README has commands. Reproduce after prior sample/study steps: ./.venv/bin/python -m milton_ian.wsp --download; ./.venv/bin/python -m milton_ian.review; ./.venv/bin/python -m milton_ian.match; ./.venv/bin/python scripts/build_story_report.py. Twelve unittests pass, including missing-layer handling and same-day/stale observation exclusion. Next: establish execution clock timezone and publication times, targeted offering/lifecycle review for Texas bonds and newly matched sample, then comparable geography review for Ian/Milton/Idalia. No regressions or source-repository writes.


## Expanded analysis and public release preparation (2026-11-18)

Added documented Eastern execution-clock conversion (FINRA corporate/agency TRACE specification https://www.finra.org/sites/default/files/CA-CTCI-specs-v3.4.pdf; cleaner maps trd_exctn_dt/tm). Intraday named-market matching excludes timestamp ties/future observations and has 1/6/24-hour freshness sensitivity. Prelandfall calendar-day event-8 support remains Beryl 2 trades/1 CUSIP and Idalia 6/3, including at 24 hours. Day-zero intraday landfall classification is not attempted.

Added forecast.py: 1,022 forecast-valid-time records across 140 advisories, including explicit dissipation records with missing values. Month rollover, forecast completeness and correction provenance checked. Added official-NOAA context figure and visually inspected its rendered PNG. GIS remains all-basin, all-active-storm with initialization rather than availability time.

Added focus.py: targeted source-prose geography checks across all four storms using both-side trading/market overlap, never price changes. These remain secondary-source geography reviews, not hand-verified CUSIP/tranche/active-risk-period assignments. Pending assets remain labeled. Added repricing.py: same-CUSIP/customer-side daily medians then window medians, reference -45/-8, anticipation -7/-1, impact 0/7, aftermath 8/30, late 31/60. Support sensitivities one/two observed dates each window; catalogued competing-landfall sensitivity. Public price-change statistics suppressed below five pairs. Changes are price points, not total returns or causal effects.

Added loss.py: source-label versus prose audit. Ian: 13 rows, 11 single-storm and 2 multi-event, six provisional-prose rows, one total-loss/provisional-prose conflict. Two terminal-loss prose candidates remain but neither has exact source-class support in eligible sample. Milton: three source rows, one single-storm, two multi-event; no terminal candidate. No Idalia/Beryl rows in this source is not evidence of no losses. No deal-level outcome propagated to every class. Announcement timestamps remain unavailable.

Public GitHub release: user explicitly requested publication to origin. Repository is public and remote initially has no refs. Preserve detailed original HTML at ignored data/derived/Hurricane_Options_Story_private.html and old detailed generator at ignored data/cache/build_story_report_private.py. Replaced public story generator with aggregate-only inputs. Seven public CSV exports, official NOAA figure, code/tests and documentation are publishable; raw trades, CUSIP-level paths, source excerpts, holdings and caches remain ignored. Public artifact checker enforces schemas, small-cell suppression and tracked-file allowlist. No GitHub Pages deployment requested.

Added offline-by-default scripts/run_study.py (--acquire for NHC, --figures optional) and GitHub Actions offline tests. Runner fingerprints small sources and compares source size/mtime across rebuild; no source changes permitted within a release rebuild. Source refresh on Nov 18 reduced Beryl eligible count to 176 from historical 177 (event8 unchanged: 103 customer prints/41 CUSIP-days); historical twelve-storm Markdown labeled as snapshot. Current briefing and public CSVs are authoritative for refreshed counts.

Validation so far: 21 unittests pass, compileall and whitespace checks pass; full stable-source rebuild/publication and remote CI verification recorded in subsequent update. Remaining research: offering/lifecycle/amendment evidence, source geography and class review for pending assets, publication/version histories, exact landfall times for day-zero phase classification, loss-announcement chronology. No pooled model yet. No source-repository writes or CSS/team-brain mutations.


## Concurrent prediction archive isolated (2026-11-18)

Stable-source check correctly rejected a full rebuild because the separate prediction collector changed the live SQLite and WAL during analysis. Did not stop or modify that process. Added snapshot.py and a test: freeze all contract metadata and study-relevant prices in a single source read-only SQLite transaction. Local snapshot contains 330,689 metadata rows, 465 selected price contracts and 245,969 price observations; excludes unrelated price histories, raw price JSON and execution tables. SHA256 and explicit scope recorded in ignored prediction_snapshot_manifest.json. Runner now reuses this snapshot and sets HURRICANE_PREDICTION_DB for subprocesses; --refresh-prediction-snapshot explicitly captures a new view. Source CSVs remain read in place and fingerprinted. Snapshot and all detailed outputs remain ignored. Twenty-two tests pass including source file unchanged after snapshot. Stable full rebuild now being checked against frozen input.


## Release validation completed (2026-11-18)

Full offline pipeline with figures completed successfully at 2026-11-18T10:39:46Z using the frozen prediction view. study_run_manifest.json reports sources_stable_during_run=true; all required source CSV fingerprints and snapshot identity stayed unchanged. Twenty-two unit tests pass; compileall, public-artifact schema/suppression checks, HTML parsing and whitespace checks pass. Public NOAA figure was visually inspected. Git staging allowlist contains code, tests, aggregate exports, official NOAA figure and aggregate-only briefing; no raw caches, detailed bond records, machine history or source excerpts. Publishing to origin main and checking remote CI follows this validation. Exact commit SHA and CI results are discoverable from Git/GitHub.


## GitHub credential constraint (2026-11-18)

Initial push was rejected by GitHub because the OAuth credential lacks workflow scope for creating .github/workflows/tests.yml. Verified origin still had no refs. Moved the authored workflow to ci/offline-checks.yml as an inactive template, documented the restriction, and updated the unpublished release commit before retrying. No repository visibility, auth scopes or credentials changed. Local 22-test suite and stable full rebuild have passed; remote Actions cannot be claimed as run.


## Verified GitHub publication (2026-11-18)

Published analysis commit fe5a25a7e3be71809f2a30e7d5caaf6f36895255 to https://github.com/carospark/milton_ian_repricing on main. Verified git ls-remote SHA equals local HEAD and GitHub default branch is main. Working tree was clean after publication. Workflow remains an inactive ci/offline-checks.yml template because the credential lacks workflow scope; no remote CI success claimed. Local 22 tests, stable full offline rebuild, compile, public-artifact validation and whitespace checks passed. Raw data, source caches, frozen SQLite snapshot and detailed audit outputs were not published. This final publication record is committed separately after the analysis release.


## Project title and visual summary (2026-11-18)

Renamed displayed project title to Hurricane repricing study in README, package description and public briefing. Added a case-flexible ignore pattern for the local study-plan PDF and removed docs/Hurricane_Repricing_Study_Plan.pdf from current Git tracking while retaining its local file. Historical commits are not rewritten. Added scripts/build_visual_summary.py, a reproducible one-page PNG/SVG from public aggregate tables, linked in README and briefing. Visual covers acquisition totals, repeated event-window trading, original Beryl Texas-scope review, prelandfall timing support, descriptive Beryl price screen and Ian loss-source conflict. Exported original Beryl scope counts as eighth public CSV and updated publication checks. Runner --figures now also builds the summary. Visual inspected; title/links/local PDF and public artifact checks pass. GitHub repository URL unchanged; rename applies to displayed study title.


## Scrollable HTML replaces image summary (2026-11-18)

User clarified the summary should be scrollable HTML with more information. Replaced the static PNG/SVG summary and its generator with a self-contained HTML report at docs/Hurricane_Repricing_Summary.html; the earlier docs/Hurricane_Options_Story.html URL builds the identical page. Added scripts/templates/research_briefing.html and rebuilt from eight public aggregate CSVs. No image, CDN or network dependencies. Nine sections cover overview, completed work, four storm profiles, coverage, forecasts/markets, geography, interactive repricing, losses and next steps. Native forecast SVG, responsive coverage bars, timing-age buttons and price filters (storm, customer side, observed-date support, reviewed-scope screen and competing-landfall restriction) run locally. README now points to HTML; runner no longer builds the removed image summary.

Corrected earlier narrative: Helene is outside Beryl plus60 days, not inside its late window. Existing date-based competing-landfall calculations were already correct and are unchanged.

Validation: 24 unit tests pass, including standalone HTML structure, internal anchor integrity, absence of external assets and both output URLs matching the generator. Node syntax check passed. Real headless Chrome verified 14 interaction/layout checks at a true 430px phone viewport (page width 430, scroll height 16147, no page-wide horizontal overflow). Desktop and phone renderings visually inspected, including price explorer. Browser used only isolated temporary profiles and was closed after checks. Aggregate-publication validation and whitespace checks pass. Temporary QA screenshots are not deliverables or tracked repository assets. Detailed data remains local.


## Removed redundant options report (2026-11-18)

Removed docs/Hurricane_Options_Story.html at user request. The generator now writes only docs/Hurricane_Repricing_Summary.html. Updated publication validation, README, historical comparison link and report tests; regression check ensures the removed options file stays absent. Historical notes above describe prior states.
