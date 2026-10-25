"""Readers for the sibling-repo outputs. Each reader returns a pandas DataFrame with the
source's own column names; nothing is renamed, pooled or forward-filled here.

Sources (as found 2026-10-25):
  bridge.csv            strict bridge; match_confidence in {high, medium, low}; title_evidence marks
                        'propagated' pairs (title-propagated, excluded from the study).
  bridge_program.csv    programme bridge; match_confidence == 'program'; level in {program_nearest,
                        program_maturity_split, program_tied, program_only, program_absent}.
  trace_trades_clean.csv one row per cleaned trade; dealer_side S = dealer sold (customer bought),
                        B = dealer bought (customer sold); contra_party C = customer, D = inter-dealer,
                        A/T rare and undocumented in the cleaner.
  tranches.csv          one row per tranche; tranche_id is the Class label; EL and attachment
                        probability are text percentages with __conf columns.
  deals.csv             one row per deal; perils_covered, trigger_type, deal_url.
  prediction_market_history.sqlite3  contracts / price_points / trades (see read_contracts).
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from .paths import require

STRICT_CONFIDENCE = {"high", "medium", "low"}


def read_bridge() -> pd.DataFrame:
    frame = pd.read_csv(require("bridge"), dtype=str, keep_default_na=False)
    frame["bridge_level"] = frame["title_evidence"].map(
        lambda v: "title-propagated" if v == "propagated" else "strict")
    return frame


def read_bridge_program() -> pd.DataFrame:
    frame = pd.read_csv(require("bridge_program"), dtype=str, keep_default_na=False)
    frame["bridge_level"] = "programme"
    return frame


def read_trace_clean() -> pd.DataFrame:
    frame = pd.read_csv(require("trace_clean"), dtype={"cusip_id": str, "msg_seq_nb": str})
    frame["trade_date"] = pd.to_datetime(frame["trade_date"])
    return frame


def read_tranches() -> pd.DataFrame:
    return pd.read_csv(require("tranches"), dtype=str, keep_default_na=False)


def read_deals() -> pd.DataFrame:
    return pd.read_csv(require("deals"), dtype=str, keep_default_na=False)


def read_hazard_map() -> pd.DataFrame:
    return pd.read_csv(require("deal_hazard_map"), dtype=str, keep_default_na=False)


def read_nport_holdings() -> pd.DataFrame:
    return pd.read_csv(require("nport_holdings"), dtype=str, keep_default_na=False)


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{require('prediction_db')}?mode=ro", uri=True)


def read_contracts(classification_prefix: str | None = "hurricane_or_named_storm") -> pd.DataFrame:
    """Contract metadata. classification is 'class;region:x;region:y' text."""
    sql = ("SELECT platform, contract_id, event_id, series_id, classification, title, "
           "opened_at, closed_at, metadata_json FROM contracts")
    params: tuple = ()
    if classification_prefix:
        sql += " WHERE classification LIKE ?"
        params = (classification_prefix + "%",)
    with _connect() as con:
        return pd.read_sql_query(sql, con, params=params)


def read_price_points(platform: str, contract_id: str) -> pd.DataFrame:
    """Per-contract price history. Kalshi rows are daily candles (price may be null when no
    trade); Polymarket rows are tick-level with one outcome_id per outcome token."""
    with _connect() as con:
        frame = pd.read_sql_query(
            "SELECT platform, contract_id, outcome_id, timestamp, price FROM price_points "
            "WHERE platform = ? AND contract_id = ? ORDER BY timestamp",
            con, params=(platform, contract_id))
    frame["ts"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    return frame


def read_trades(platform: str, contract_id: str) -> pd.DataFrame:
    with _connect() as con:
        frame = pd.read_sql_query(
            "SELECT platform, contract_id, trade_id, timestamp, side, price, size FROM trades "
            "WHERE platform = ? AND contract_id = ?", con, params=(platform, contract_id))
    frame["ts"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    return frame


def read_nhc_archive() -> pd.DataFrame:
    """NHC advisory / wind-speed-probability archive. Not present locally yet; raises."""
    return pd.read_csv(require("nhc_archive"))
