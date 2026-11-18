# Ian / Milton / Idalia / Beryl repricing study

Descriptive catastrophe-bond repricing around hurricane forecasts, landfall and loss developments.
The selected sample is **Ian, Milton, Idalia and Beryl**, recorded in
`config_study.yaml`. Research roles:

- **Milton** (landfall 9 Oct 2024): expectations, repricing and possible recovery.
  The local archive has no verified Milton-specific contract; its city wind markets
  are seasonal proxies. NHC products supply a separate forecast-information source.
- **Ian** (landfall 28 Sep 2022): concentrated losses, subject to tranche and loss-timing
  verification. No market-wide price effect has yet been established.
- **Idalia**: Florida-specific named-storm intensity market histories, with sparse bond overlap.
- **Beryl**: named-storm US landfall market histories and the first joint-timeline pilot.

The twelve-storm comparison remains a historical coverage screen and a source of
competing-event flags; it does not expand the selected research sample.

Start with the [current research briefing](docs/Hurricane_Options_Story.html),
the [forecast context figure](figures/nhc_information_context.png), and the
explicit `public_*.csv` aggregate tables under `data/derived/`.
GitHub displays HTML source; download the HTML and adjacent `figures/` directory
and open it locally to read the formatted briefing. No website deployment is configured.

The original plan is `docs/Hurricane_Repricing_Study_Plan.pdf`; the current sample
is governed by `config_study.yaml`. Coverage has been counted and descriptive
comparisons built. No regression or causal storm-effect claim is supported yet.

## Current findings

- All 140 index-listed NHC forecast advisories are cached and parsed into 1,022
  forecast-valid-time records. Three advisory archive versions are corrected.
- 141 GIS probability snapshots were acquired over nine dates per storm. They
  combine active storms and must not be labeled named-storm or bond-loss probabilities.
- The original 23 Beryl same-date-overlap bonds include only three with explicit
  Texas scope in secondary-source prose. Broader US scope and other-state scope
  need separate treatment; the historical broad exposure screen is not a Texas measure.
- FINRA documentation confirms Eastern execution clocks. Intraday matching
  excludes future samples and timestamp ties and tests 1/6/24-hour freshness limits.
  Pre-landfall calendar days −4/−1 contain only two matched customer trades in one
  Beryl bond, versus six trades in three Idalia bonds, even at the 24-hour limit.
- Same-bond, same-side price comparisons are sparse. Two-date support in both
  windows leaves few Ian/Milton pairs; later Beryl windows overlap other storms.
  Public price statistics are suppressed below five paired CUSIPs.
- One Ian total-loss label conflicts with provisional mark-to-market prose.
  Two terminal-loss prose candidates remain, but neither currently has exact
  source-class support in the strict eligible sample. They are not verified bond losses.

## Data statement

This project reads the outputs of two sibling repositories read-only and rebuilds
none of their pipelines:

| Source | Repository | Used for |
|---|---|---|
| Strict bridge (`bridge.csv`) and programme bridge (`bridge_program.csv`) | `cat-bond-flow-analysis` | CUSIP to deal identity with confidence and evidence |
| Cleaned TRACE 144A trades (`trace_trades_clean.csv`) | `cat-bond-flow-analysis` | CUSIP-level trades, dealer side, customer vs inter-dealer |
| Deal hazard map, N-PORT fund holdings | `cat-bond-flow-analysis` | Exposure as mapped; fund-reported titles carry the tranche Class |
| Prediction-market SQLite archive | `cat-bond-flow-analysis` | Kalshi and Polymarket contract metadata, price histories, trades |
| Parsed deal and tranche tables (`deals.csv`, `tranches.csv`) | `cat-bond-issuance` | Peril, trigger, class, expected loss, attachment probability |
| Loss-source table (`losses.csv`) | `cat-bond-issuance` | Source labels checked against prose; no automatic tranche propagation |

Official NHC advisory pages and GIS wind-probability archives are cached locally,
with URLs and file hashes. Only official NOAA intensity observations, small
aggregate exports and the aggregate briefing/figure are published.

Licensed inputs (Artemis page caches, WRDS/TRACE exports, N-PORT filings, market snapshots)
are never committed here. Only code, small whitelisted summary tables under `data/derived/`,
and figures go in git. `.gitignore` enforces this.

## Exclusions

- Programme-bridge and title-propagated CUSIP pairs are listed in the sample table and
  excluded from every figure and model. Only strict high-confidence pairs count.
- Tranches are never pooled into deals. Everything is at CUSIP level.
- Prices are never forward-filled. A CUSIP that did not trade on a day has no row for that day.
- Seasonal storm-count contracts are not storm-specific and are not used as probability paths.
- No claim about total investor flows, fund subscriptions, or substitution from reinsurance.

## How to run

Public checkout, no licensed inputs needed:

```bash
python3 -m venv .venv && ./.venv/bin/python -m pip install -e .
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python scripts/build_story_report.py
./.venv/bin/python scripts/check_public_artifacts.py
```

The optional GitHub Actions configuration is provided as
[`ci/offline-checks.yml`](ci/offline-checks.yml). It is a template, not an active
workflow: the publication credential lacks GitHub's `workflow` scope. A credential
with that permission can install it at `.github/workflows/tests.yml` later.
Local checks require no GitHub permission.

Full source-data rebuild requires the configured sibling outputs, read-only
prediction SQLite, cached issuance source pages, and NHC caches:

```bash
./.venv/bin/python -m milton_ian.paths
./.venv/bin/python -m pip install -e '.[figures]'
./.venv/bin/python scripts/run_study.py --figures
```

The runner is offline by default. Add `--acquire` to allow official NHC downloads;
it does not download or rebuild licensed sibling data. All individual modules also
run with `python -m milton_ian.<module>`: `compare`, `sample`, `nhc`, `wsp`,
`forecast`, `study`, `review`, `focus`, `loss`, `match`, `repricing`, `publish`.

The live prediction archive can be updated by a separate process. On first run,
the runner freezes a local research SQLite snapshot in one read-only source
transaction: all contract metadata, plus study-relevant price rows. Unrelated
price histories, raw price payloads and execution tables are omitted. It reuses
that ignored snapshot until `--refresh-prediction-snapshot` is requested. The
snapshot manifest records its scope and SHA256; it is never uploaded. Other
source fingerprints must remain stable throughout a rebuild. Individual modules
use the configured live database unless `HURRICANE_PREDICTION_DB` explicitly points
to a snapshot; the runner sets that override for every subprocess.

`study_observed_trades.csv`, `study_information_timeline.csv`, `study_coverage.csv`,
`study_mapping_review_queue.csv`, and `study_validation.json` are local, gitignored
outputs in `data/derived/`. Raw NHC pages and extracted text are cached under
`data/raw/nhc/`; `nhc_advisories.csv` records source URLs, hashes, advisory numbers,
issue times and correction flags. The collector caches existing pages; it does not
silently refresh them. Run `nhc --storms beryl` for a single selected storm.

The information timeline inventories observed events. The dedicated market matcher
uses execution clocks localized to Eastern time, as specified by
[FINRA](https://www.finra.org/sites/default/files/CA-CTCI-specs-v3.4.pdf).
The source cleaner directly maps `trd_exctn_dt`/`trd_exctn_tm`; these are not report
timestamps. Archived corrected advisories can replace earlier versions, and stated
NHC issue times are not verified publication times. Forecast advisories are not
wind-probability observations or bond-loss probabilities.
The WSP collector records every expected six-hour cycle, including cycles not
listed in the cached index. Its 0–120-hour cumulative 34/50/64-knot fields are
all-basin, all-active-storm products. Exact half-degree locations are contextual
grid samples; missing points and missing threshold layers are not assigned zero.
Initialization times are not publication times, and these probabilities must not
be labeled named-storm landfall or bond-loss probabilities.

The Beryl review checks cached secondary-source geography against the original
23 same-date-overlap bonds and records source hashes, excerpts, bridge evidence
and dated N-PORT class support in ignored CSVs. It does not verify offering terms
or promote any CUSIP/tranche pair to hand-verified status. It is a separate layer
from the historical broad-region comparison, which remains unchanged. In particular,
the broad screen should not be used as a Texas exposure designation.

`study_prior_day_market_matches.csv` uses actual Yes-price samples from the
preceding Eastern calendar date only, with no gap filling. Different timing rules
produce different bond samples; the Beryl 23-bond review does not cover the whole
preceding-day matched sample. Trade/contract pairs are not independent trades.
The intraday sensitivity is in `study_intraday_market_matches.csv`; aggregate
support counts are exported publicly. No NHC availability-time match is asserted.
Next: verify product-publication/version evidence, offering terms, active risk
periods and amendments; extend source review and loss-announcement timelines.
No regressions yet.

`config.yaml` holds the sibling-repo paths, storm dates and window lengths. The resolver in
`src/milton_ian/paths.py` fails loudly if any configured file is missing.

## Layout

```
config.yaml            sibling paths, input files, storm dates, windows
docs/                  the study plan
src/milton_ian/
  paths.py             resolve and verify sibling-repo paths
  load.py              readers: bridge, TRACE, tranches, deals, hazard map, N-PORT, prediction SQLite
  sample.py            builds the usable-sample tables
data/derived/          outputs (gitignored except whitelisted summaries)
figures/               official NOAA forecast and geographic wind context
notebooks/             empty
```
