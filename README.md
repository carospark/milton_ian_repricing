# Milton / Ian repricing study

How catastrophe bonds reprice as a feared Florida hurricane becomes more or less likely.
Two storms, two jobs:

- **Milton** (landfall 9 Oct 2024) is the *expectations* story: Tampa was feared, Tampa was
  spared, and prediction markets were liquid enough to give a probability path.
- **Ian** (landfall 28 Sep 2022) is the *concentrated-loss* story: a market-wide move at the
  median with two deals destroyed in the tail. Ian is not a replication of the Milton design.

The plan is `docs/Hurricane_Repricing_Study_Plan.pdf`. The first deliverable is a usable-sample
table, not a figure; the model (if any) is chosen after that table has been counted.

## Data statement

This project reads, in place and read-only, the outputs of two sibling repositories and
rebuilds none of their pipelines:

| Source | Repository | Used for |
|---|---|---|
| Strict bridge (`bridge.csv`) and programme bridge (`bridge_program.csv`) | `cat-bond-flow-analysis` | CUSIP to deal identity with confidence and evidence |
| Cleaned TRACE 144A trades (`trace_trades_clean.csv`) | `cat-bond-flow-analysis` | CUSIP-level trades, dealer side, customer vs inter-dealer |
| Deal hazard map, N-PORT fund holdings | `cat-bond-flow-analysis` | Exposure as mapped; fund-reported titles carry the tranche Class |
| Prediction-market SQLite archive | `cat-bond-flow-analysis` | Kalshi and Polymarket contract metadata, price histories, trades |
| Parsed deal and tranche tables (`deals.csv`, `tranches.csv`) | `cat-bond-issuance` | Peril, trigger, class, expected loss, attachment probability |

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

```bash
python3 -m venv .venv && ./.venv/bin/python -m pip install -e .
./.venv/bin/python -m milton_ian.paths      # checks every configured input exists
./.venv/bin/python -m milton_ian.sample     # builds the usable-sample tables into data/derived/
```

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
figures/               empty until the sample has been counted
notebooks/             empty
```
