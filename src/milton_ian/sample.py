"""CUSIP-level usable-sample audit. No bridge join is applied to trade rows.

Dates: inclusive [-45,+60]; pre < landfall, post > landfall, day zero separate.
Event8: inclusive [-4,+3], distinct observed trade dates / 8 calendar days.
Customer imbalance = customer buys minus customer sells in reported face volume.
All CUSIPs in the cleaned extract trading in the window are retained, including
unmapped CUSIPs. Eligibility is identity mapping only, separate from exposure.
"""
from __future__ import annotations
import json
import re
import math
import pandas as pd
from . import load
from .paths import load_config, output_dir, resolve_inputs

CLASS=re.compile(r'\bCLASS\s+([A-Z0-9]+(?:-[A-Z0-9]+)*)', re.I)
EXCLUDES=re.compile(r'(?:exclud\w*|ex-?|excl\.?|without)\s+(?:\w+\s+){0,3}florida|florida\s+(?:is\s+)?exclud',re.I)


def exposure(hazards, peril, regions, location='florida', exposed_label='florida_hurricane_exposed'):
    if hazards.empty or not str(peril).strip():
        return 'unknown'
    hurricanes=hazards[hazards.hazard_class.eq('hurricane_or_named_storm')]
    if hurricanes.empty:
        # This is a mapped no-hurricane group, not an inference from missing rows.
        return 'unexposed'
    excludes = re.compile(EXCLUDES.pattern.replace('florida', re.escape(location)), re.I)
    if excludes.search(peril):
        return 'ambiguous'
    if set(hurricanes.region) & set(regions):
        return exposed_label
    # Explicit geography away from Florida is kept separate, never guessed from missing geography.
    if set(hurricanes.region) & {'global','caribbean',''}:
        return 'unknown'
    return 'other_hurricane_region'


def class_mapping(cusip, deal, tranches, holdings):
    titles=sorted(set(holdings.loc[holdings.cusip.eq(cusip),'title']))
    classes=sorted(set('Class '+m.upper() for title in titles for m in CLASS.findall(title)))
    result={'tranche_class':'','class_match_status':'unknown_no_explicit_class','class_match_provenance':'N-PORT explicit Class token linked by exact CUSIP; exact deal_slug/tranche_id required','class_title_evidence':' | '.join(titles),'class_candidates':';'.join(classes),'expected_loss':'','attachment_probability':''}
    for field in ['expected_loss','attachment_probability']:
        result[field+'__conf']='';result[field+'__flags']=''
    if len(classes)>1:
        result['class_match_status']='conflicting_nport_classes';return result
    if len(classes)==0 or deal is None:
        return result
    # A title's explicit series must not contradict the bridged deal series.
    expected=re.findall(r'(20\d{2})-(\d+)',deal.get('deal_slug',''))
    observed=set(x for title in titles for x in re.findall(r'\b(20\d{2})-(\d+)\b',title))
    if expected and observed and any(x!=expected[0] for x in observed):
        result['class_match_status']='conflicting_nport_series';return result
    candidates=tranches[tranches.deal_slug.eq(deal['deal_slug']) & tranches.tranche_id.str.upper().eq(classes[0].upper())]
    if len(candidates)!=1:
        result['class_match_status']='unknown_class_not_unique_in_deal';return result
    result.update({'tranche_class':classes[0],'class_match_status':'matched_explicit_nport_class'})
    r=candidates.iloc[0]
    for field in ['expected_loss','attachment_probability']:
        for col in [field,field+'__conf',field+'__flags']:
            result[col]=r[col]
    return result


def select_mapping(cusip, bridge, program):
    strict=bridge[bridge.cusip_id.eq(cusip)]
    prog=program[program.cusip_id.eq(cusip)]
    if len(strict)>1:
        return None,False,'ambiguous_strict_mapping',strict,prog
    if len(strict)==1:
        r=strict.iloc[0].to_dict()
        eligible=r['match_confidence']=='high' and r['title_evidence']!='propagated'
        return r,eligible,('eligible' if eligible else 'excluded_'+r['bridge_level']+'_'+r['match_confidence']),strict,prog
    if len(prog)==1 and prog.iloc[0].deal_url and prog.iloc[0].get('level','') in {'program_nearest','program_maturity_split','program_nport_title'}:
        return prog.iloc[0].to_dict(),False,'excluded_programme',strict,prog
    return None,False,('ambiguous_programme_mapping' if len(prog) else 'unmapped'),strict,prog


def metrics(g, t0, event_start, event_end):
    customer=g[g.contra_party.eq('C')]
    buy=customer[customer.dealer_side.eq('S')]; sell=customer[customer.dealer_side.eq('B')]
    other=customer[~customer.dealer_side.isin(['S','B'])]
    npre=int(customer.trade_date.lt(t0).sum());npost=int(customer.trade_date.gt(t0).sum());non=int(customer.trade_date.eq(t0).sum())
    event=g[g.trade_date.between(event_start,event_end)]
    event_c=customer[customer.trade_date.between(event_start,event_end)]
    nday=(event_end-event_start).days+1
    counts=g.contra_party.fillna('missing').value_counts()
    def volume(frame):
        return float('nan') if frame.volume.isna().any() else float(frame.volume.sum())
    bv=volume(buy); sv=volume(sell)
    result={'first_trade_date':g.trade_date.min().date(),'last_trade_date':g.trade_date.max().date(),'all_trade_count':len(g),'customer_trades_pre':npre,'customer_trades_post':npost,'customer_trades_landfall':non,'customer_trades_total':len(customer),'interdealer_trades':int(counts.get('D',0)),'counterparty_A_trades':int(counts.get('A',0)),'counterparty_T_trades':int(counts.get('T',0)),'other_unknown_counterparty_trades':int((~g.contra_party.isin(['C','D'])).sum()),'counterparty_counts_json':json.dumps(counts.to_dict(),sort_keys=True),'event8_observed_trade_dates':event.trade_date.nunique(),'event8_customer_trade_dates':event_c.trade_date.nunique(),'event8_calendar_day_denominator':nday,'event8_all_trading_density':event.trade_date.nunique()/nday,'event8_customer_trading_density':event_c.trade_date.nunique()/nday,'customer_buy_volume':bv,'customer_sell_volume':sv,'net_customer_imbalance_buy_minus_sell':bv-sv,'customer_unknown_side_count':len(other),'customer_unknown_side_volume':other.volume.sum(),'customer_volume':customer.volume.sum(),'all_volume':g.volume.sum(),'missing_volume_count':int(g.volume.isna().sum()),'capped_volume_count':int(g.volume_capped.fillna(False).sum()),'min_observed_price':g.price.min(),'max_observed_price':g.price.max(),'missing_price_count':int(g.price.isna().sum()),'three_customer_trades_each_side':npre>=3 and npost>=3}
    assert npre+npost+non==len(customer)
    result.update({'customer_trade_dates_pre':customer.loc[customer.trade_date.lt(t0),'trade_date'].nunique(),'customer_trade_dates_post':customer.loc[customer.trade_date.gt(t0),'trade_date'].nunique(),'customer_buy_missing_volume_count':int(buy.volume.isna().sum()),'customer_sell_missing_volume_count':int(sell.volume.isna().sum()),'customer_min_observed_price':customer.price.min(),'customer_max_observed_price':customer.price.max()})
    assert len(customer)+result['interdealer_trades']+result['other_unknown_counterparty_trades']==len(g)
    assert math.isclose(float(buy.volume.sum()+sell.volume.sum()+other.volume.sum()),float(customer.volume.sum()),abs_tol=1e-6)
    return result


def run():
    cfg=load_config();out=output_dir(cfg)
    bridge=load.read_bridge();program=load.read_bridge_program();tranches=load.read_tranches();deals=load.read_deals();hazards=load.read_hazard_map();holdings=load.read_nport_holdings();trades=load.read_trace_clean()
    assert not bridge.duplicated(['cusip_id','deal_url']).any(), 'duplicate bridge pair'
    assert not deals.deal_url.duplicated().any(), 'duplicate deal identity'
    assert not tranches.duplicated(['deal_slug','tranche_id']).any(), 'duplicate tranche identity'
    inventory=pd.read_csv(out/'milton_contracts.csv',dtype=str,keep_default_na=False)
    summaries={};validation={};mapping_audit=[];daily=[];overlaps=[]
    deal_index=deals.set_index('deal_url').to_dict('index')
    for storm,definition in cfg['storms'].items():
        t0=pd.Timestamp(definition['landfall']);start=t0-pd.Timedelta(days=cfg['windows']['pre_days']);end=t0+pd.Timedelta(days=cfg['windows']['post_days']);event_start=t0-pd.Timedelta(days=cfg['windows']['storm_week_pre_days']);event_end=t0+pd.Timedelta(days=cfg['windows']['storm_week_post_days'])
        window=trades[trades.trade_date.between(start,end)].copy();rows=[]
        for cusip,g in window.groupby('cusip_id',sort=True):
            mapping,eligible,status,strict,prog=select_mapping(cusip,bridge,program)
            deal=deal_index.get(mapping.get('deal_url','')) if mapping else None
            dh=hazards[hazards.deal_url.eq(mapping.get('deal_url',''))] if mapping else hazards.iloc[:0]
            peril=deal.get('perils_covered','') if deal else ''
            row={'storm':storm,'cusip':cusip,'eligible_strict_high':eligible,'eligibility_status':status,'deal_url':mapping.get('deal_url','') if mapping else '','deal':deal.get('deal_name','') if deal else '','bridge_level':mapping.get('bridge_level','unknown') if mapping else 'unknown','bridge_confidence':mapping.get('match_confidence','') if mapping else '','strict_bridge_pairs':len(strict),'programme_bridge_pairs':len(prog),'bridge_evidence_json':json.dumps({k:v for k,v in (mapping or {}).items() if 'evidence' in k or k in ['match_method','match_basis','level']},sort_keys=True),'peril':peril,'trigger':deal.get('trigger_type','') if deal else '','mapped_hazards':';'.join(sorted(set(dh.hazard_class))),'mapped_regions':';'.join(sorted(set(dh.region))),'exposure':exposure(dh,peril,cfg['exposure']['florida_regions']),'window_start':start.date(),'window_end':end.date(),'event8_start':event_start.date(),'event8_end':event_end.date()}
            row.update(class_mapping(cusip,deal,tranches,holdings));row.update(metrics(g,t0,event_start,event_end))
            if storm=='milton':
                trade_dates=set(g.trade_date.dt.strftime('%Y-%m-%d'))
                for cat,col in [('explicitly_milton_specific','milton_specific_contract_overlap_count'),('geographic_seasonal_strike','geographic_seasonal_strike_overlap_count'),('geographic_multistorm_strike','geographic_multistorm_strike_overlap_count')]:
                    matches=[]
                    for r in inventory[inventory.category.eq(cat)].to_dict('records'):
                        dates=trade_dates & set(r['yes_trade_date_candidates_et'].split(';'))
                        if dates:
                            matches.append(r['platform']+':'+r['contract_id'])
                            overlaps.append({'cusip':cusip,'platform':r['platform'],'contract_id':r['contract_id'],'category':cat,'overlap_utc_dates':';'.join(sorted(dates)),'overlap_date_count':len(dates)})
                    row[col]=len(matches);row[col.replace('_count','_ids')]=';'.join(matches)
            rows.append(row)
            for level,frame in [('strict',strict),('programme',prog)]:
                for r in frame.to_dict('records'):
                    mapping_audit.append({'storm':storm,'cusip':cusip,'audit_source':level,'eligibility_status':status,**r})
        sample=pd.DataFrame(rows)
        assert not sample.cusip.duplicated().any()
        assert sample.all_trade_count.sum()==len(window), 'trade multiplication/loss'
        assert math.isclose(sample.all_volume.sum(),window.volume.sum(),rel_tol=1e-12,abs_tol=.01), 'volume multiplication/loss'
        assert sample.loc[sample.eligible_strict_high,'bridge_confidence'].eq('high').all()
        assert sample.loc[sample.eligible_strict_high,'bridge_level'].eq('strict').all()
        assert sample.loc[~sample.class_match_status.eq('matched_explicit_nport_class'),'expected_loss'].eq('').all()
        sample.to_csv(out/f'usable_sample_{storm}.csv',index=False)
        # CUSIP-day customer activity retains gaps; only observed days written.
        for (cusip,date),g in window.groupby(['cusip_id','trade_date']):
            c=g[g.contra_party.eq('C')];daily.append({'storm':storm,'cusip':cusip,'trade_date':date.date(),'all_trade_count':len(g),'customer_trade_count':len(c),'customer_buy_volume':c.loc[c.dealer_side.eq('S'),'volume'].sum(),'customer_sell_volume':c.loc[c.dealer_side.eq('B'),'volume'].sum(),'observed_min_price':g.price.min(),'observed_max_price':g.price.max()})
        e=sample[sample.eligible_strict_high]
        summary={'storm':storm,'window_start':str(start.date()),'window_end':str(end.date()),'unique_traded_cusips':len(sample),'eligible_strict_high_cusips':len(e),'eligible_distinct_deals':e.deal_url.nunique(),'eligible_at_least_3_customer_trades_each_side':int(e.three_customer_trades_each_side.sum()),'eligible_florida_hurricane_exposed':int(e.exposure.eq('florida_hurricane_exposed').sum()),'eligible_unexposed':int(e.exposure.eq('unexposed').sum()),'eligible_other_hurricane_region':int(e.exposure.eq('other_hurricane_region').sum()),'eligible_unknown_ambiguous_exposure':int(e.exposure.isin(['unknown','ambiguous']).sum()),'all_florida_hurricane_exposed':int(sample.exposure.eq('florida_hurricane_exposed').sum()),'all_unexposed':int(sample.exposure.eq('unexposed').sum()),'all_other_hurricane_region':int(sample.exposure.eq('other_hurricane_region').sum()),'all_unknown_ambiguous_exposure':int(sample.exposure.isin(['unknown','ambiguous']).sum()),'eligible_explicit_class_matches':int(e.class_match_status.eq('matched_explicit_nport_class').sum()),'extract_interdealer_trades':int(sample.interdealer_trades.sum())}
        assert sum(summary[k] for k in ['eligible_florida_hurricane_exposed','eligible_unexposed','eligible_other_hurricane_region','eligible_unknown_ambiguous_exposure'])==len(e)
        if storm=='milton':
            for col in ['milton_specific_contract_overlap_count','geographic_seasonal_strike_overlap_count','geographic_multistorm_strike_overlap_count']:
                summary['eligible_cusips_with_'+col]=int(e[col].gt(0).sum())
        pd.DataFrame([summary]).to_csv(out/f'coverage_summary_{storm}.csv',index=False)
        summaries[storm]=summary
        validation[storm]={'input_window_trades':len(window),'output_summed_trade_count':int(sample.all_trade_count.sum()),'input_window_volume':float(window.volume.sum()),'output_summed_volume':float(sample.all_volume.sum()),'unique_cusip_check':True,'exposure_partition_check':True,'eligibility_and_class_missingness_check':True,'counterparty_counts':window.contra_party.fillna('missing').value_counts().to_dict()}
    pd.DataFrame(mapping_audit).to_csv(out/'mapping_audit.csv',index=False)
    pd.DataFrame(daily).to_csv(out/'cusip_daily_activity.csv',index=False)
    pd.DataFrame(overlaps).to_csv(out/'contract_cusip_overlap.csv',index=False)
    (out/'sample_validation.json').write_text(json.dumps(validation,indent=2))
    # Capture source identity without copying inputs or modifying any source file.
    manifest=[]
    for key,path in resolve_inputs(cfg).items():
        if path and path.exists():
            stat=path.stat();manifest.append({'input':key,'path':str(path),'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns})
    (out/'input_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':
    run()
