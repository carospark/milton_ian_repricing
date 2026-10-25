"""Read-only audit of Figure 14 activity and Milton probability candidates.

Run with python -m milton_ian.contracts. Detailed local tables remain ignored.
UTC calendar dates define probability overlap; no interpolation or forward fill.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import pandas as pd
from .paths import require, load_config, output_dir
from .load import _connect

KEY = ['platform', 'contract_id']


def stamps(values):
    """Mixed ISO and epoch-second timestamps, without treating seconds as nanoseconds."""
    numeric = pd.to_numeric(values, errors='coerce').astype('float64')
    numeric = numeric.where(numeric.between(0, 4102444800))
    parsed = pd.to_datetime(values.where(numeric.isna()), format='mixed', utc=True, errors='coerce')
    epoch = pd.Series(pd.NaT, index=values.index, dtype='datetime64[ns, UTC]')
    valid = numeric.notna()
    if valid.any():
        epoch.loc[valid] = pd.to_datetime(numeric.loc[valid], unit='s', utc=True, errors='coerce')
    return parsed.fillna(epoch)


def array(value):
    return json.loads(value) if isinstance(value, str) else (value or [])


def category(row):
    """Conservative, auditable local categorization; broad counts never substitute."""
    text = ' '.join(str(row.get(k, '')) for k in ['contract_id','event_id','series_id','title','metadata_json']).lower()
    if 'milton' in text:
        return 'explicitly_milton_specific'
    if row['platform'] == 'kalshi' and re.match(r'HUR(?:TB|ORL|MIA|JACKFL)-24NOV30-', row['contract_id']):
        return 'geographic_seasonal_strike'
    if row['platform'] == 'polymarket' and row['contract_id'] == '509459':
        return 'geographic_multistorm_strike'
    if '2024' in text or '-24' in row['contract_id']:
        if re.search(r'named storms|atlantic hurricanes|major atlantic|hurricane season|tropical storms', str(row['title']).lower()):
            return 'broad_seasonal_count'
        if row['contract_id'].startswith('HUR') and 'hit ' in str(row['title']).lower():
            return 'other_geographic_strike'
    return 'irrelevant_or_uncertain'


def outcome_map(row):
    m = json.loads(row['metadata_json']); market = m.get('market', m)
    if row['platform'] == 'kalshi':
        return {'yes': 'Yes'}
    tokens = array(market.get('clobTokenIds', row['outcome_ids_json']))
    labels = array(market.get('outcomes', []))
    return dict(zip(tokens, labels)) if len(tokens) == len(labels) else {}


def observation_dates(frame, platform):
    """Map archive timestamps to TRACE Eastern trading dates.

    Polymarket timestamps are actual UTC observations. Kalshi timestamps are
    daily candle end boundaries at midnight Eastern; assign the close to the
    Eastern calendar day that just ended.
    """
    eastern = frame.ts.dt.tz_convert('America/New_York')
    if platform == 'kalshi':
        eastern = eastern - pd.Timedelta(days=1)
    return eastern.dt.strftime('%Y-%m-%d')


def audit():
    config = load_config(); out = output_dir(config); flow = Path(config['siblings']['flow'])
    t0 = pd.Timestamp(config['storms']['milton']['landfall']); start=t0-pd.Timedelta(days=config['windows']['pre_days']); end=t0+pd.Timedelta(days=config['windows']['post_days'])
    with _connect() as con:
        # Search every contract's IDs and full nested event/market metadata, not just classified titles.
        contracts = pd.read_sql_query('SELECT * FROM contracts', con)
        fields=['contract_id','event_id','series_id','title','metadata_json']
        milton = contracts[fields].fillna('').apply(lambda s:s.str.contains('milton',case=False,regex=False)).any(axis=1)
        hurricane=contracts.classification.str.contains('hurricane_or_named_storm',na=False)
        opened=stamps(contracts.opened_at); closed=stamps(contracts.closed_at)
        active=opened.le(pd.Timestamp(end,tz='UTC')+pd.Timedelta(days=1)) & closed.ge(pd.Timestamp(start,tz='UTC'))
        # Include misclassified contracts whose full metadata is hurricane-related in this window.
        metadata_hurricane=contracts.metadata_json.str.contains(r'hurricane|tropical cyclone|named storm',case=False,regex=True)
        selected=contracts[milton | ((hurricane | metadata_hurricane) & active)].copy()
        selected['category']=selected.apply(category,axis=1)
        selected['matched_milton_full_metadata']=milton.loc[selected.index]
        selected[KEY+['title','classification','category','matched_milton_full_metadata']].to_csv(out/'contract_search_audit.csv',index=False)
        # Source saved contract-day file is the precise precursor to the saved class-day chart.
        daily=pd.read_csv(flow/'data/market_contract_daily.csv',dtype={'contract_id':str})
        daily['day']=pd.to_datetime(daily.date)
        daily['week']=((daily.day-t0).dt.days//7).astype(int)
        daily=daily[daily.day.between(start,end) & daily.hazard_classes.fillna('').str.split(';').map(lambda x:'hurricane_or_named_storm' in x)].copy()
        daily['region_multiplier']=daily.regions.fillna('').str.split(';').map(lambda rs:sum(r in {'florida','us'} for r in rs))
        daily=daily[daily.region_multiplier.gt(0)]
        daily['expanded_size']=daily.traded_size.fillna(0)*daily.region_multiplier
        daily['expanded_n_trades']=daily.n_trades.fillna(0)*daily.region_multiplier
        weekly=daily.groupby('week').agg(unique_contract_day_size=('traded_size','sum'),expanded_size=('expanded_size','sum'),expanded_n_trades=('expanded_n_trades','sum')).reset_index()
        saved=pd.read_csv(flow/'data/event_checks/milton_market_weekly.csv')
        weekly=weekly.merge(saved,on='week',validate='one_to_one')
        weekly['expanded_minus_saved']=weekly.expanded_size-weekly.traded_size
        classes=pd.read_csv(flow/'data/market_class_daily.csv')
        classes['day']=pd.to_datetime(classes.date)
        classes=classes[classes.hazard_class.eq('hurricane_or_named_storm') & classes.region.isin(['florida','us']) & classes.day.between(start,end)].copy()
        classes['week']=((classes.day-t0).dt.days//7).astype(int)
        class_week=classes.groupby('week').traded_size.sum()
        weekly['class_daily_size']=weekly.week.map(class_week)
        weekly['class_minus_saved']=weekly.class_daily_size-weekly.traded_size
        weekly.to_csv(out/'activity_reconciliation.csv',index=False)
        contributors=daily[daily.week.eq(0)].groupby(KEY).agg(saved_unique_size=('traded_size','sum'),chart_expanded_size=('expanded_size','sum'),saved_n_trades=('n_trades','sum'),region_multiplier=('region_multiplier','max')).reset_index()
        contributors=contributors[contributors.chart_expanded_size.gt(0)]
        ids=set(map(tuple,contributors[KEY].values))
        selected=pd.concat([selected,contracts[contracts[KEY].apply(tuple,axis=1).isin(ids)]]).drop_duplicates(KEY)
        selected['category']=selected.apply(category,axis=1)
        inventory=[]; observations=[]; local_trade_totals=[]
        for r in selected.to_dict('records'):
            m=json.loads(r['metadata_json']); market=m.get('market',m); event=m.get('event',{})
            rules='\n'.join(str(market.get(k,'')) for k in ['description','rules_primary','rules_secondary']).strip()
            outcomes=outcome_map(r)
            prices=pd.read_sql_query('SELECT outcome_id,timestamp,price FROM price_points WHERE platform=? AND contract_id=?',con,params=(r['platform'],r['contract_id']))
            prices['ts']=pd.to_datetime(prices.timestamp,unit='s',utc=True)
            prices['price_numeric']=pd.to_numeric(prices.price,errors='coerce')
            prices['utc_date']=prices.ts.dt.strftime('%Y-%m-%d')
            prices['date']=observation_dates(prices,r['platform'])
            prices['outcome']=prices.outcome_id.map(outcomes).fillna('Unknown')
            relevant=prices[prices.price_numeric.notna() & prices.price_numeric.between(0,1)]
            yes=relevant[relevant.outcome.eq('Yes')]
            window=yes[yes.date.between(str(start.date()),str(end.date()))]
            event8=window[window.date.between(str((t0-pd.Timedelta(days=4)).date()),str((t0+pd.Timedelta(days=3)).date()))]
            chart7=yes[yes.utc_date.between(str(t0.date()),str((t0+pd.Timedelta(days=6)).date()))]
            trades=pd.read_sql_query('SELECT timestamp,size FROM trades WHERE platform=? AND contract_id=?',con,params=(r['platform'],r['contract_id']))
            ts=stamps(trades.timestamp); dates=ts.dt.strftime('%Y-%m-%d'); size=pd.to_numeric(trades['size'],errors='coerce')
            land=dates.between('2024-10-09','2024-10-15')
            local_trade_totals.append({**{k:r[k] for k in KEY},'archive_week0_size':float(size[land].sum()),'archive_week0_n_trades':int(land.sum()),'archive_invalid_timestamps':int(ts.isna().sum()),'archive_invalid_sizes':int(size.isna().sum())})
            for oid,g in prices.groupby('outcome_id'):
                valid=g[g.price_numeric.notna()]
                observations.append({**{k:r[k] for k in KEY},'outcome_id':oid,'outcome':outcomes.get(oid,'Unknown'),'rows':len(g),'non_null':len(valid),'first_non_null_utc':valid.ts.min(),'last_non_null_utc':valid.ts.max(),'min_price':valid.price_numeric.min(),'max_price':valid.price_numeric.max(),'observation_kind':'daily candle close, end_period_ts' if r['platform']=='kalshi' else 'token price-history sample'})
            inventory.append({**{k:r[k] for k in KEY},'exact_question':r['title'],'classification':r['classification'],'category':r['category'],'event_id':r['event_id'],'series_id':r['series_id'],'event_title':event.get('title',''),'event_slug':event.get('slug',''),'slug':market.get('slug',''),'opened_at':r['opened_at'],'closed_at':r['closed_at'],'scheduled_close_or_end':market.get('close_time',market.get('endDate','')),'outcome':'Yes' if 'Yes' in outcomes.values() else 'Unknown','yes_outcome_id':next((k for k,v in outcomes.items() if v=='Yes'),''),'resolution_rules':rules,'resolution_source':market.get('resolutionSource','NWS' if r['platform']=='kalshi' else ''),'yes_non_null_window':len(window),'yes_non_null_event8':len(event8),'yes_non_null_chart7_utc':len(chart7),'yes_trade_date_candidates_et':';'.join(sorted(set(window.date))),'yes_first_window_utc':window.ts.min(),'yes_last_window_utc':window.ts.max(),'limitations':('season-long city wind threshold; not Milton-specific; Kalshi close mapped to Eastern trading date for overlap' if r['category']=='geographic_seasonal_strike' else 'any US Category 5 landfall Oct 8-Nov 4; opened Oct 9 late UTC; not Milton-specific' if r['contract_id']=='509459' else 'not a Milton-specific probability; inspect rules and horizon')})
        inventory=pd.DataFrame(inventory).sort_values(KEY)
        inventory.to_csv(out/'milton_contracts.csv',index=False)
        pd.DataFrame(observations).to_csv(out/'contract_outcome_coverage.csv',index=False)
        contributors=contributors.merge(pd.DataFrame(local_trade_totals),on=KEY,how='left',validate='one_to_one').merge(inventory,on=KEY,how='left',validate='one_to_one')
        contributors['archive_expanded_size']=contributors.archive_week0_size*contributors.region_multiplier
        contributors['archive_minus_saved_unique']=contributors.archive_week0_size-contributors.saved_unique_size
        contributors.to_csv(out/'activity_contributors.csv',index=False)
        # Metadata-only compact, safe-to-track inventory is explicitly whitelisted by existing policy.
        assert not inventory.duplicated(KEY).any()
        assert (relevant.price_numeric.dropna().between(0,1)).all()
        report={'full_metadata_milton_matches':int(milton.sum()),'archive_contract_count':len(contracts),'selected_contract_count':len(inventory),'week0_contributor_count':len(contributors),'week0_saved_chart_size':float(saved.loc[saved.week.eq(0),'traded_size'].iloc[0]),'week0_saved_unique_size':float(contributors.saved_unique_size.sum()),'week0_saved_expanded_size':float(contributors.chart_expanded_size.sum()),'week0_archive_unique_size':float(contributors.archive_week0_size.sum()),'week0_archive_expanded_size':float(contributors.archive_expanded_size.sum()),'max_weekly_class_vs_saved_absolute_difference':float(weekly.class_minus_saved.abs().max()),'max_weekly_contract_vs_saved_absolute_difference':float(weekly.expanded_minus_saved.abs().max()),'category_counts':inventory.groupby('category').size().to_dict()}
        (out/'contract_audit.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        return inventory

if __name__=='__main__':
    audit()
