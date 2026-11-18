"""Four-storm observed-trade and information inventories; no synthetic days.

Outputs are detailed source-derived data and remain gitignored. Date-level event
inventory does not claim that an advisory or market observation preceded a trade.
"""
from __future__ import annotations

import json
import pandas as pd
import yaml

from . import load
from .contracts import outcome_map
from .match import execution_times, TRACE_CLOCK_SOURCE
from .paths import ROOT, output_dir, load_config


def run():
    out = output_dir(); cfg = load_config()
    selected = yaml.safe_load((ROOT/'config_study.yaml').read_text())['storms']
    definitions = yaml.safe_load((ROOT/'config_comparison.yaml').read_text())['storms']
    coverage = pd.read_csv(out/'hurricane_coverage_comparison.csv').set_index('storm').loc[selected].reset_index()
    details = pd.read_csv(out/'comparison_cusip_details.csv', dtype={'cusip': str})
    details = details[details.storm.isin(selected)]
    contracts = pd.read_csv(out/'comparison_contracts.csv', dtype={'contract_id': str})
    trace = load.read_trace_clean()
    events = []; panels = []; checks = []
    nhc_path = out/'nhc_advisories.csv'
    nhc = pd.read_csv(nhc_path) if nhc_path.exists() else pd.DataFrame()
    with load._connect() as con:
        for storm in selected:
            t0 = pd.Timestamp(definitions[storm]['landfall'])
            start = t0-pd.Timedelta(days=cfg['windows']['pre_days'])
            end = t0+pd.Timedelta(days=cfg['windows']['post_days'])
            bonds = details[details.storm.eq(storm)]
            trades = trace[trace.cusip_id.isin(bonds.cusip) & trace.trade_date.between(start, end)].copy()
            trades['storm'] = storm
            trades['days_from_landfall'] = (trades.trade_date-t0).dt.days
            trades['customer_action'] = trades.dealer_side.map({'S': 'buy', 'B': 'sell'}).fillna('unknown_side').where(trades.contra_party.eq('C'), 'not_customer')
            trades['execution_time_utc'] = execution_times(trades)
            trades['trade_time_status'] = 'execution field; Eastern wall clock per FINRA; invalid/ambiguous stays missing'
            trades['trade_clock_source'] = TRACE_CLOCK_SOURCE
            trades = trades.merge(bonds[['cusip', 'deal_url', 'exposure', 'tranche_class', 'class_match_status']], left_on='cusip_id', right_on='cusip', validate='many_to_one')
            assert len(trades) == bonds.all_trade_count.sum()
            customer = trades[trades.contra_party.eq('C')]
            assert len(customer) == bonds.customer_trades_total.sum()
            event = customer[customer.days_from_landfall.between(-4, 3)]
            trade_days = event[['cusip_id', 'trade_date']].drop_duplicates()
            row = coverage[coverage.storm.eq(storm)].iloc[0]
            assert len(trade_days) == row.event8_customer_trade_days_total
            panels.append(trades)
            for day, group in customer.groupby('trade_date'):
                events.append({'storm': storm, 'event_type': 'observed_customer_trading', 'date_et': str(day.date()),
                               'timestamp_utc': '', 'observations': len(group), 'cusips': group.cusip_id.nunique(),
                               'source_id': 'configured cleaned TRACE', 'ordering_status': 'date only; no intraday precedence established'})
            inv = contracts[contracts.storm.eq(storm) & contracts.category.eq('storm_specific')]
            for contract in inv.to_dict('records'):
                platform = contract['platform']; cid = contract['contract_id']
                meta = pd.read_sql_query('SELECT * FROM contracts WHERE platform=? AND contract_id=?', con, params=(platform, cid)).iloc[0]
                p = load.read_price_points(platform, cid)
                p['outcome'] = p.outcome_id.map(outcome_map(meta))
                p = p[p.outcome.eq('Yes') & p.price.between(0, 1)].copy()
                p['date_et'] = p.ts.dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
                p = p[p.date_et.between(str(start.date()), str(end.date()))]
                for observation in p.to_dict('records'):
                    events.append({'storm': storm, 'event_type': 'named_storm_yes_price', 'date_et': observation['date_et'],
                                   'timestamp_utc': observation['ts'].isoformat(), 'price': observation['price'],
                                   'source_id': platform+':'+cid, 'ordering_status': 'token price sample; inventory only; use dedicated intraday matcher'})
            if len(nhc):
                for advisory in nhc[nhc.storm.eq(storm)].to_dict('records'):
                    issued = pd.Timestamp(advisory['issue_time_utc'])
                    events.append({'storm': storm, 'event_type': 'nhc_forecast_advisory',
                                   'date_et': str(issued.tz_convert('America/New_York').date()),
                                   'timestamp_utc': issued.isoformat(), 'source_id': advisory['source_url'],
                                   'corrected': advisory['corrected'], 'ordering_status': advisory['timing_status']})
            checks.append({'storm': storm, 'eligible_cusips': len(bonds), 'eligible_customer_trades_window': len(customer),
                           'eligible_customer_trades_event8': len(event), 'eligible_customer_cusip_days_event8': len(trade_days),
                           'nhc_advisories': int(nhc.storm.eq(storm).sum()) if len(nhc) else 0})
    pd.concat(panels, ignore_index=True).to_csv(out/'study_observed_trades.csv', index=False)
    pd.DataFrame(events).sort_values(['storm', 'date_et', 'event_type', 'timestamp_utc']).to_csv(out/'study_information_timeline.csv', index=False)
    coverage.to_csv(out/'study_coverage.csv', index=False)
    details.to_csv(out/'study_mapping_review_queue.csv', index=False)
    (out/'study_validation.json').write_text(json.dumps(checks, indent=2)+'\n')
    print(pd.DataFrame(checks).to_string(index=False))


if __name__ == '__main__':
    run()
