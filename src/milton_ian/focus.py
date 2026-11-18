"""Targeted, source-prose geography checks across all four storms.

Selection uses available trading on both sides or named-market overlap, not price
changes. Registry decisions concern geography only, never impairment or risk weights.
"""
import hashlib
from pathlib import Path
import re
import pandas as pd
from . import load
from .paths import output_dir, load_config
from .review import REVIEWS, paragraphs

FOCUS = {
 ('ian','floodsmart-re-ltd-series-2021-1'): ('us_named_storm_flood', r'flood losses.*named storm|named storm.*flood', 'Flood trigger is distinct from wind probability'),
 ('ian','catahoula-ii-re-pte-ltd-series-2022-1'): ('other_state_scope', r'affecting the State of Louisiana', ''),
 ('milton','first-coast-re-iii-pte-ltd-series-2021-1'): ('explicit_target_state', r'exposed to Florida named storms', 'Verify prior Ian losses and remaining risk/collateral'),
 ('milton','aquila-re-i-ltd-series-2023-1'): ('broad_us_scope', r'including U.S. named storm', ''),
 ('milton','titania-re-ltd-series-2021-2'): ('broad_us_scope', r'U.S. 50 state', 'Annual aggregate; earlier 2024 events may matter'),
 ('idalia','everglades-re-ii-ltd-series-2021-1-2021-2'): ('explicit_target_state', r'losses from Florida named storms', 'Dual-series deal page requires exact series verification'),
 ('idalia','matterhorn-re-ltd-series-2022-2'): ('explicit_target_state_with_broader_scope', r'Gulf Coast, including Florida', 'Industry loss weights remain unverified'),
 ('idalia','locke-tavern-re-ltd-series-2023-1'): ('other_state_scope', r'Connecticut, Illinois, Maine', 'Northeastern scope; not a mapped no-hurricane control'),
 ('idalia','titania-re-ltd-series-2021-1'): ('broad_us_scope', r'U.S., Puerto Rico, U.S. Virgin Islands', ''),
 ('idalia','alamo-re-ltd-series-2023-1'): ('other_state_scope', r'protection is for Texas named storms', ''),
 ('beryl','alamo-re-ltd-series-2024-1'): ('explicit_target_state', r'all three tranches is for Texas named storms', 'Annual aggregate'),
 ('beryl','merna-re-ii-ltd-series-2023-2'): ('explicit_target_state', r'specifically for the state of Texas', ''),
 ('beryl','gateway-re-ltd-series-2023-1'): ('explicit_target_state', r'Louisiana, Mississippi, Texas', ''),
}
for slug, (status, pattern, notes) in REVIEWS.items():
    general = {'explicit_texas':'explicit_target_state', 'regional_scope_outside_texas':'other_state_scope',
               'broad_us_scope_weights_unverified':'broad_us_scope', 'texas_explicitly_excluded':'target_state_excluded',
               'no_us_named_storm_peril':'no_us_named_storm_peril'}[status]
    FOCUS[('beryl',slug)] = (general,pattern,notes)


def run():
    out=output_dir(); queue=pd.read_csv(out/'study_mapping_review_queue.csv',dtype={'cusip':str})
    selected=queue[(queue.customer_trades_pre.gt(0)&queue.customer_trades_post.gt(0)) | queue.specific_contracts_with_trade_overlap.gt(0)]
    deals=load.read_deals(); rows=[]; raw=Path(load_config()['siblings']['issuance'])/'raw'
    for r in selected.merge(deals,on='deal_url',validate='many_to_one').to_dict('records'):
        key=(r['storm'],r['deal_slug']); decision=FOCUS.get(key)
        status='pending_source_review'; notes=''; evidence=''; digest=''; source=''
        if decision:
            status,pattern,notes=decision; paths=list(raw.glob('*'+r['deal_slug']+'__*.html'))
            if len(paths)!=1: raise ValueError(f'Nonunique source for {key}')
            path=paths[0]; excerpts=[p for p in paragraphs(path.read_text()) if re.search(pattern,p,re.I)]
            if not excerpts: raise ValueError(f'Missing reviewed evidence for {key}')
            evidence='\n'.join(excerpts); source=str(path); digest=hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({**r,'scope_review_status':status,'scope_review_notes':notes,'scope_evidence':evidence,
                     'source_cache':source,'source_sha256':digest,'hand_verified_tranche_exposure':False,
                     'review_limit':'secondary reporting; amendments, remaining coverage and offering terms unverified'})
    result=pd.DataFrame(rows); result.to_csv(out/'study_focus_source_review.csv',index=False)
    summary=result.groupby(['storm','scope_review_status']).size().rename('cusips').reset_index()
    summary.to_csv(out/'study_focus_review_summary.csv',index=False)
    print(summary.to_string(index=False))


if __name__=='__main__': run()
