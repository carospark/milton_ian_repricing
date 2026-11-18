"""Conservative named-market matching without assuming TRACE clock timezone.

Use only actual observations on the preceding Eastern calendar date. No same-day
information, synthetic prices or carry across missing observation dates. This is
a temporal screen, not a claim that market price causes bond-price movement.
"""
from __future__ import annotations
import pandas as pd
from .paths import output_dir

TRACE_CLOCK_SOURCE = 'https://www.finra.org/sites/default/files/CA-CTCI-specs-v3.4.pdf'


def execution_times(trades):
    """Source cleaner maps trd_exctn_dt/tm; FINRA specifies Eastern clocks.

    Localize the wall clock before converting to UTC. Missing, invalid or DST
    ambiguous/nonexistent times remain missing, never midnight or UTC by default.
    """
    clocks = trades.trade_time.fillna('').astype(str)
    valid = clocks.str.fullmatch(r'\d{2}:\d{2}:\d{2}(?:\.\d+)?')
    wall = pd.to_datetime(trades.trade_date.astype(str).str[:10]+' '+clocks.where(valid), errors='coerce')
    return wall.dt.tz_localize('America/New_York', ambiguous='NaT', nonexistent='NaT').dt.tz_convert('UTC')


def intraday_prices(trades, observations, max_age_hours=24):
    """Strictly earlier token samples, with a predeclared freshness limit.

    Timestamp ordering establishes neither market liquidity nor an actionable
    quote. Timestamp ties are excluded; samples are not executions.
    """
    left = trades.copy()
    left['execution_time_utc'] = execution_times(left)
    left = left[left.execution_time_utc.notna()].sort_values('execution_time_utc')
    right = observations.copy()
    right['market_observation_utc'] = pd.to_datetime(right.timestamp_utc, utc=True)
    right = right[right.price.notna()].sort_values('market_observation_utc')
    pieces = []
    for (storm, cid), market in right.groupby(['storm','source_id']):
        bond = left[left.storm.eq(storm)]
        if bond.empty:
            continue
        market = market.drop_duplicates('market_observation_utc', keep='last')
        joined = pd.merge_asof(bond, market[['market_observation_utc','price']],
                               left_on='execution_time_utc', right_on='market_observation_utc',
                               direction='backward', allow_exact_matches=False,
                               tolerance=pd.Timedelta(hours=max_age_hours), suffixes=('_bond','_market'))
        joined = joined[joined.market_observation_utc.notna()].copy()
        joined['source_id'] = cid
        joined['market_sample_age_hours'] = (joined.execution_time_utc-joined.market_observation_utc).dt.total_seconds()/3600
        assert joined.market_sample_age_hours.gt(0).all()
        joined['clock_source'] = TRACE_CLOCK_SOURCE
        joined['freshness_limit_hours'] = max_age_hours
        pieces.append(joined)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def prior_day_prices(trades, observations):
    candidates = observations.copy()
    candidates['observed_at_utc'] = pd.to_datetime(candidates.timestamp_utc, utc=True)
    candidates['observation_date_et'] = candidates.observed_at_utc.dt.tz_convert('America/New_York').dt.tz_localize(None).dt.normalize()
    candidates = candidates.sort_values('observed_at_utc').drop_duplicates(['storm', 'source_id', 'observation_date_et'], keep='last')
    candidates['trade_date'] = candidates.observation_date_et+pd.Timedelta(days=1)
    trade_rows = trades.copy(); trade_rows['trade_date'] = pd.to_datetime(trade_rows.trade_date)
    # One output per trade and observed named contract; row multiplication here
    # represents distinct contracts and must never be counted as distinct trades.
    result = trade_rows.merge(candidates[['storm','source_id','trade_date','observation_date_et','observed_at_utc','price']],
                              on=['storm','trade_date'], how='inner', suffixes=('_bond','_market'))
    midnight = result.trade_date.dt.tz_localize('America/New_York').dt.tz_convert('UTC')
    assert result.observed_at_utc.lt(midnight).all()
    result['hours_before_trade_day_start'] = (midnight-result.observed_at_utc).dt.total_seconds()/3600
    assert result.hours_before_trade_day_start.gt(0).all()
    result['match_status'] = 'observed previous ET date only; no same-day information'
    return result


def run():
    out = output_dir()
    trades = pd.read_csv(out/'study_observed_trades.csv', dtype={'cusip_id':str})
    trades['local_trade_row_id'] = range(len(trades))
    customer = trades[trades.contra_party.eq('C')]
    timeline = pd.read_csv(out/'study_information_timeline.csv')
    observations = timeline[timeline.event_type.eq('named_storm_yes_price')]
    matched = prior_day_prices(customer, observations)
    matched.to_csv(out/'study_prior_day_market_matches.csv', index=False)
    summaries = []
    for storm, frame in matched.groupby('storm'):
        event = frame[frame.days_from_landfall.between(-4,3)]
        pre = event[event.days_from_landfall.lt(0)]
        summaries.append({'storm': storm, 'matched_customer_trades_window':frame.local_trade_row_id.nunique(),
                          'matched_cusips_window':frame.cusip_id.nunique(),
                          'matched_customer_trades_event8':event.local_trade_row_id.nunique(),
                          'matched_cusips_event8':event.cusip_id.nunique(),
                          'matched_cusips_prelandfall_event8':pre.cusip_id.nunique()})
    summary = pd.DataFrame(summaries); summary.to_csv(out/'study_prior_day_match_summary.csv',index=False)
    print(summary.to_string(index=False))
    sensitivity = []
    for age in (1, 6, 24):
        intraday = intraday_prices(customer, observations, age)
        if age == 24:
            intraday.to_csv(out/'study_intraday_market_matches.csv', index=False)
        for storm in ('beryl','idalia'):
            frame = intraday[intraday.storm.eq(storm)] if len(intraday) else intraday
            for label, low, high in [('window',-45,60),('event8',-4,3),('prelandfall_event8',-4,-1)]:
                w = frame[frame.days_from_landfall.between(low,high)] if len(frame) else frame
                sensitivity.append({'storm':storm,'max_age_hours':age,'period':label,
                                    'customer_trades':w.local_trade_row_id.nunique() if len(w) else 0,
                                    'cusips':w.cusip_id.nunique() if len(w) else 0})
    pd.DataFrame(sensitivity).to_csv(out/'study_intraday_match_summary.csv', index=False)
    print(pd.DataFrame(sensitivity).to_string(index=False))


if __name__ == '__main__':
    run()
