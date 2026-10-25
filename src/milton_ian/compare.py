"""Lightweight coverage comparison. No source writes, downloads or price effects.

Shares mapping, eligibility, class, exposure and trade metrics with sample.py.
All contract IDs and nested metadata searched with word boundaries; named
matches are manually rule-screened below. Missing local history is not evidence
that a market or NHC product never existed.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import pandas as pd
import yaml
from . import load
from .paths import ROOT, load_config, output_dir
from .sample import select_mapping, class_mapping, exposure, metrics
from .contracts import stamps, outcome_map, observation_dates


def reviewed_contract_category(row, storm, year, location):
    cid=row['contract_id'];m=json.loads(row['metadata_json']);market=m.get('market',m)
    question=str(row['title']).lower()
    # Read the archived rules: first Idalia Florida landfall, NHC initial advisory,
    # Cat >=3 or exactly Cat 4. FEMA declarations do not measure landfall probability.
    if storm=='idalia' and row['platform']=='polymarket' and cid in {'252104','252115'}:
        return 'storm_specific'
    if storm=='beryl' and row['platform']=='polymarket' and cid in {'503112','503117'}:
        return 'storm_specific'
    prefix='(?:TB|ORL|MIA|JACKFL)' if location=='florida' else '(?:NO)' if location in {'louisiana','gulf_coast'} else '(?:HOU|GAL)' if location=='texas' else r'(?!)'
    if row['platform']=='kalshi' and re.match(r'HUR'+prefix+rf'-{str(year)[2:]}NOV30-',cid):
        return 'geographic_seasonal_proxy'
    if storm in {'helene','milton'} and row['platform']=='polymarket' and cid=='509459':
        return 'geographic_multistorm_proxy'
    return 'other_or_uncertain'


def contract_screen(con, contracts, storm, definition, start, end):
    year=pd.Timestamp(definition['landfall']).year;location=definition['region']
    t0=pd.Timestamp(definition['landfall']);event_start=t0-pd.Timedelta(days=4);event_end=t0+pd.Timedelta(days=3)
    same_year=contracts.opened_at.fillna('').str.startswith(str(year)) | contracts.closed_at.fillna('').str.startswith(str(year))
    opened=contracts['_opened_utc'];closed=contracts['_closed_utc']
    active=opened.le(pd.Timestamp(end,tz='UTC')+pd.Timedelta(days=1)) & closed.ge(pd.Timestamp(start,tz='UTC'))
    # Do not discard a named contract because a scheduled close precedes actual opening.
    hurricane=contracts.classification.str.contains('hurricane_or_named_storm',na=False)
    pool=contracts[same_year | (active & hurricane)]
    if pool.empty:
        return pd.DataFrame(),{},{}
    text=pool[['contract_id','event_id','series_id','title','metadata_json']].fillna('').agg(' '.join,axis=1)
    named=text.str.contains(r'\b'+re.escape(storm)+r'\b',case=False,regex=True)
    candidates=pool[named | (active.loc[pool.index] & hurricane.loc[pool.index])].copy()
    rows=[];date_sets={};near_sets={}
    for r in candidates.to_dict('records'):
        cat=reviewed_contract_category(r,storm,year,location)
        searchable=' '.join(str(r.get(k,'')) for k in ['contract_id','event_id','series_id','title','metadata_json'])
        is_named=bool(re.search(r'\b'+re.escape(storm)+r'\b',searchable,re.I))
        if cat=='other_or_uncertain' and not is_named:
            continue
        m=json.loads(r['metadata_json']);market=m.get('market',m);outcomes=outcome_map(r)
        p=pd.read_sql_query('SELECT outcome_id,timestamp,price FROM price_points WHERE platform=? AND contract_id=?',con,params=(r['platform'],r['contract_id']))
        p['ts']=pd.to_datetime(p.timestamp,unit='s',utc=True);p['price_numeric']=pd.to_numeric(p.price,errors='coerce');p['date']=observation_dates(p,r['platform']);p['label']=p.outcome_id.map(outcomes)
        yes=p[p.label.eq('Yes') & p.price_numeric.notna() & p.price_numeric.between(0,1)]
        w=yes[yes.date.between(str(start.date()),str(end.date()))];near=w[w.date.between(str(event_start.date()),str(event_end.date()))]
        key=r['platform']+':'+r['contract_id'];date_sets[key]=set(w.date);near_sets[key]=set(near.date)
        rows.append({'storm':storm,'platform':r['platform'],'contract_id':r['contract_id'],'exact_question':r['title'],'classification':r['classification'],'category':cat,'opened_at':r['opened_at'],'closed_at':r['closed_at'],'yes_outcome_id':next((k for k,v in outcomes.items() if v=='Yes'),''),'outcome':'Yes','rules': '\n'.join(str(market.get(k,'')) for k in ['description','rules_primary','rules_secondary']).strip(),'price_rows_all_outcomes':len(p),'yes_non_null_window':len(w),'yes_distinct_dates_window':w.date.nunique(),'yes_non_null_event8':len(near),'yes_distinct_dates_event8':near.date.nunique(),'first_window_observation_utc':w.ts.min(),'last_window_observation_utc':w.ts.max(),'window_observation_dates_et':';'.join(sorted(set(w.date))),'event8_observation_dates_et':';'.join(sorted(set(near.date))),'history_kind':'daily candle Yes close; close assigned to preceding Eastern day' if r['platform']=='kalshi' else 'token price-history samples, timestamps mapped to Eastern date','review_status':'rules reviewed; named storm-specific landfall outcome' if cat=='storm_specific' else 'city wind threshold over season; not storm-specific' if cat=='geographic_seasonal_proxy' else 'US any-storm Cat5 before election; not storm-specific' if cat=='geographic_multistorm_proxy' else 'named in metadata but not a verified storm-landfall outcome'})
    return pd.DataFrame(rows),date_sets,near_sets


def run():
    cfg=load_config();out=output_dir(cfg)
    with open(ROOT/'config_comparison.yaml') as f: storms=yaml.safe_load(f)['storms']
    t=load.read_trace_clean();b=load.read_bridge();pr=load.read_bridge_program();d=load.read_deals();tr=load.read_tranches();h=load.read_hazard_map();n=load.read_nport_holdings()
    assert not b.duplicated(['cusip_id','deal_url']).any()
    di=d.set_index('deal_url').to_dict('index');summaries=[];metadata=[];details=[]
    with load._connect() as con:
        # Full local archive search, including unclassified contracts and nested event metadata.
        contracts=pd.read_sql_query('SELECT * FROM contracts',con)
        contracts['_opened_utc']=stamps(contracts.opened_at)
        contracts['_closed_utc']=stamps(contracts.closed_at)
        for storm,definition in storms.items():
            t0=pd.Timestamp(definition['landfall']);start=t0-pd.Timedelta(days=cfg['windows']['pre_days']);end=t0+pd.Timedelta(days=cfg['windows']['post_days']);event_start=t0-pd.Timedelta(days=4);event_end=t0+pd.Timedelta(days=3)
            w=t[t.trade_date.between(start,end)];rows=[]
            inventory,dates,near_dates=contract_screen(con,contracts,storm,definition,start,end)
            if len(inventory):metadata.append(inventory)
            region_tags=cfg['exposure']['florida_regions'] if definition['region']=='florida' else ['us','gulf_coast']
            for cusip,g in w.groupby('cusip_id'):
                mapping,eligible,status,_,_=select_mapping(cusip,b,pr)
                if not eligible:continue
                deal=di.get(mapping['deal_url']);dh=h[h.deal_url.eq(mapping['deal_url'])]
                e=exposure(dh,deal.get('perils_covered','') if deal else '',region_tags,definition['region'],'relevant_region_hurricane_exposed')
                r={'storm':storm,'cusip':cusip,'deal_url':mapping['deal_url'],'exposure':e,**metrics(g,t0,event_start,event_end),**class_mapping(cusip,deal,tr,n)}
                trade_dates=set(g.trade_date.dt.strftime('%Y-%m-%d'))
                for cat,col in [('storm_specific','specific'),('geographic_seasonal_proxy','seasonal_proxy'),('geographic_multistorm_proxy','multistorm_proxy')]:
                    ids=[];overlap_dates=set();event_dates=set();repeated_contracts=[]
                    if len(inventory):
                        for c in inventory[inventory.category.eq(cat)].to_dict('records'):
                            key=c['platform']+':'+c['contract_id'];overlap=dates[key] & trade_dates;near_overlap=near_dates[key] & trade_dates
                            if overlap:ids.append(key);overlap_dates |= overlap
                            event_dates |= near_overlap
                            if len(near_overlap)>=2:repeated_contracts.append(key)
                    r[col+'_contracts_with_trade_overlap']=len(ids);r[col+'_overlap_dates']=len(overlap_dates);r[col+'_event8_overlap_dates']=len(event_dates);r[col+'_repeated_contracts']=len(repeated_contracts)
                rows.append(r)
            s=pd.DataFrame(rows);details.extend(rows)
            assert not s.cusip.duplicated().any()
            e=s.exposure
            count=lambda col:int(s[col].gt(0).sum())
            inv_count=lambda cat: int((inventory.category.eq(cat)&inventory.yes_non_null_window.gt(0)).sum()) if len(inventory) else 0
            repeated=s.event8_customer_trade_dates.ge(2)
            nhc_id=definition['nhc_id']
            row={'storm':storm,'landfall':str(t0.date()),'region':definition['region'],'landfall_status':definition.get('landfall_status','hurricane'),'window_start':str(start.date()),'window_end':str(end.date()),'eligible_cusips':len(s),'relevant_region_exposed':int(e.eq('relevant_region_hurricane_exposed').sum()),'mapped_no_hurricane_unexposed':int(e.eq('unexposed').sum()),'other_hurricane_region':int(e.eq('other_hurricane_region').sum()),'unknown_ambiguous_exposure':int(e.isin(['unknown','ambiguous']).sum()),'three_customer_trades_each_side':int(s.three_customer_trades_each_side.sum()),'median_event8_customer_density':float(s.event8_customer_trading_density.median()),'event8_customer_trade_days_total':int(s.event8_customer_trade_dates.sum()),'event8_density_denominator':len(s)*8,'event8_repeated_customer_cusips':int(repeated.sum()),'title_supported_class_cusips':int(s.class_match_status.eq('matched_explicit_nport_class').sum()),'class_and_relevant_exposure_cusips':int((s.class_match_status.eq('matched_explicit_nport_class') & e.eq('relevant_region_hurricane_exposed')).sum()),'hand_verified_tranche_exposure_cusips':0,'specific_contracts_non_null_window':inv_count('storm_specific'),'specific_contracts_with_trade_overlap':0,'specific_overlap_cusips':count('specific_contracts_with_trade_overlap'),'specific_event8_overlap_cusips':count('specific_event8_overlap_dates'),'specific_repeated_event8_overlap_cusips':count('specific_repeated_contracts'),'seasonal_proxy_contracts_non_null_window':inv_count('geographic_seasonal_proxy'),'seasonal_proxy_overlap_cusips':count('seasonal_proxy_contracts_with_trade_overlap'),'seasonal_proxy_repeated_event8_overlap_cusips':count('seasonal_proxy_repeated_contracts'),'multistorm_proxy_contracts_non_null_window':inv_count('geographic_multistorm_proxy'),'multistorm_proxy_overlap_cusips':count('multistorm_proxy_contracts_with_trade_overlap'),'nhc_local_forecasts':'not in project or sibling-repository local file inventory','nhc_local_wind_probabilities':'not in project or sibling-repository local file inventory','nhc_remote_status':'official storm archive pages indexed for selected high-priority events; full per-advisory inventory and QA pending','nhc_advisory_archive':f"https://www.nhc.noaa.gov/archive/{t0.year}/{nhc_id[:4]}/",'prediction_status':'local full-metadata search complete; delisted/uncollected markets not confirmed unavailable'}
            assert sum(row[k] for k in ['relevant_region_exposed','mapped_no_hurricane_unexposed','other_hurricane_region','unknown_ambiguous_exposure'])==len(s)
            # Count contracts with an actual eligible CUSIP trade-date overlap, independent of title/lifespan.
            if len(inventory):
                all_dates=set(w[w.cusip_id.isin(s.cusip)].trade_date.dt.strftime('%Y-%m-%d'))
                row['specific_contracts_with_trade_overlap']=sum(bool(dates[r['platform']+':'+r['contract_id']] & all_dates) for r in inventory[inventory.category.eq('storm_specific')].to_dict('records'))
            for other,od in storms.items():
                if other==storm:continue
                ot=pd.Timestamp(od['landfall']);os=ot-pd.Timedelta(days=45);oe=ot+pd.Timedelta(days=60)
                if max(start,os)<=min(end,oe):row.setdefault('overlapping_candidate_windows',[]).append(other)
            row['overlapping_candidate_windows']=';'.join(row.get('overlapping_candidate_windows',[]))
            summaries.append(row)
            print(storm,len(s),row['specific_contracts_non_null_window'],flush=True)
    pd.DataFrame(summaries).to_csv(out/'hurricane_coverage_comparison.csv',index=False)
    pd.concat(metadata,ignore_index=True).to_csv(out/'comparison_contracts.csv',index=False)
    pd.DataFrame(details).to_csv(out/'comparison_cusip_details.csv',index=False)
    print(pd.DataFrame(summaries)[['storm','eligible_cusips','relevant_region_exposed','three_customer_trades_each_side','event8_repeated_customer_cusips','specific_contracts_non_null_window','specific_overlap_cusips','specific_repeated_event8_overlap_cusips','seasonal_proxy_contracts_non_null_window']].to_string(index=False))

if __name__=='__main__':run()
