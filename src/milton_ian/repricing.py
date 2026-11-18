"""Descriptive, same-CUSIP/same-customer-side observed price changes.

Equal-weight daily median prices, then median across observed dates in each
window. Differences are price points, not total returns or causal storm effects.
The reference is [-45,-8]; comparison windows are prespecified. No forward fill.
"""
import pandas as pd
import yaml
from .paths import ROOT, output_dir

WINDOWS={'anticipation':(-7,-1),'impact':(0,7),'aftermath':(8,30),'late':(31,60)}
REFERENCE=(-45,-8)
PUBLIC_MIN_CUSIPS=5


def paired_changes(trades, definitions):
    data=trades[trades.contra_party.eq('C') & trades.dealer_side.isin(['B','S']) & trades.price.notna()].copy()
    if data.price.lt(0).any(): raise ValueError('Negative bond price requires source review')
    data['trade_date']=pd.to_datetime(data.trade_date)
    keys=['storm','cusip_id','dealer_side','trade_date','days_from_landfall']
    daily=data.groupby(keys,as_index=False).agg(daily_median_price=('price','median'),prints=('price','size'))
    rows=[]
    for (storm,cusip,side), frame in daily.groupby(['storm','cusip_id','dealer_side']):
        ref=frame[frame.days_from_landfall.between(*REFERENCE)]
        if ref.empty: continue
        t0=pd.Timestamp(definitions[storm]['landfall'])
        for label,(lo,hi) in WINDOWS.items():
            comparison=frame[frame.days_from_landfall.between(lo,hi)]
            if comparison.empty: continue
            competing=[]
            for other, definition in definitions.items():
                if other==storm: continue
                day=(pd.Timestamp(definition['landfall'])-t0).days
                if REFERENCE[0]<=day<=REFERENCE[1] or lo<=day<=hi: competing.append(other)
            rows.append({'storm':storm,'cusip_id':cusip,'dealer_side':side,
                         'customer_action':'buy' if side=='S' else 'sell','comparison_window':label,
                         'reference_days':len(ref),'comparison_days':len(comparison),
                         'reference_price':ref.daily_median_price.median(),
                         'comparison_price':comparison.daily_median_price.median(),
                         'change_price_points':comparison.daily_median_price.median()-ref.daily_median_price.median(),
                         'reference_first_trade':str(ref.trade_date.min().date()),
                         'reference_last_trade':str(ref.trade_date.max().date()),
                         'comparison_first_trade':str(comparison.trade_date.min().date()),
                         'comparison_last_trade':str(comparison.trade_date.max().date()),
                         'other_catalog_landfalls_in_windows':';'.join(sorted(competing))})
    return pd.DataFrame(rows),daily


def aggregate_pairs(pairs, selected):
    rows=[]
    for storm in selected:
        for action in ('buy','sell'):
            for period in WINDOWS:
                for support in (1,2):
                    for restriction in ('all_strict','no_other_catalog_landfall'):
                        for sample in ('all_identity_eligible','reviewed_target_scope'):
                            p=pairs[pairs.storm.eq(storm)&pairs.customer_action.eq(action)&pairs.comparison_window.eq(period)]
                            p=p[p.reference_days.ge(support)&p.comparison_days.ge(support)]
                            if restriction=='no_other_catalog_landfall': p=p[p.other_catalog_landfalls_in_windows.eq('')]
                            if sample=='reviewed_target_scope':
                                p=p[p.scope_review_status.isin(['explicit_target_state','explicit_target_state_with_broader_scope','us_named_storm_flood'])]
                            n=p.cusip_id.nunique()
                            assert n==len(p)
                            rows.append({'storm':storm,'customer_action':action,'comparison_window':period,
                                         'minimum_observed_days_each_window':support,'restriction':restriction,'sample':sample,
                                         'paired_cusips':n,'reported':n>=PUBLIC_MIN_CUSIPS,
                                         'median_change_price_points':p.change_price_points.median() if n>=PUBLIC_MIN_CUSIPS else None})
    return pd.DataFrame(rows)


def run():
    out=output_dir(); definitions=yaml.safe_load((ROOT/'config_comparison.yaml').read_text())['storms']
    selected=yaml.safe_load((ROOT/'config_study.yaml').read_text())['storms']
    trades=pd.read_csv(out/'study_observed_trades.csv',dtype={'cusip_id':str})
    pairs,daily=paired_changes(trades,definitions)
    scope=pd.read_csv(out/'study_focus_source_review.csv',dtype={'cusip':str})
    pairs=pairs.merge(scope[['storm','cusip','scope_review_status']],left_on=['storm','cusip_id'],right_on=['storm','cusip'],how='left',validate='many_to_one')
    pairs['scope_review_status']=pairs.scope_review_status.fillna('pending_source_review')
    pairs.to_csv(out/'study_paired_price_changes.csv',index=False)
    daily.to_csv(out/'study_observed_daily_prices.csv',index=False)
    aggregate=aggregate_pairs(pairs,selected)
    aggregate.to_csv(out/'study_repricing_summary.csv',index=False)
    preview=aggregate[aggregate.minimum_observed_days_each_window.eq(2)&aggregate.restriction.eq('all_strict')&aggregate['sample'].eq('all_identity_eligible')]
    print(preview[['storm','customer_action','comparison_window','paired_cusips','median_change_price_points']].to_string(index=False))


if __name__=='__main__': run()
