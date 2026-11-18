"""Reproducible Beryl geography review against read-only cached deal prose.

Reviewed source descriptions are secondary reporting, not offering documents.
No CUSIP/tranche pair is promoted to hand-verified status. Detailed evidence and
holdings dates remain in ignored outputs, never written to source repositories.
"""
from __future__ import annotations
import hashlib
import html
import json
import re
from pathlib import Path

import pandas as pd

from . import load
from .paths import load_config, output_dir

# Decisions from reading the cached deal paragraphs. Patterns anchor the
# supporting evidence; changed or missing text fails rather than silently passing.
REVIEWS = {
 'alamo-re-ltd-series-2023-1': ('explicit_texas', r'protection is for Texas named storms', ''),
 'armor-re-ii-ltd-series-2024-1': ('regional_scope_outside_texas', r'three.year source of Florida named storm', ''),
 'astro-re-pte-ltd-series-2021-1': ('regional_scope_outside_texas', r'states of Florida, Alabama, Georgia, North Carolina and South Carolina', 'Broad US peril field omits stated regional scope'),
 'bayou-re-ltd-series-2023-1': ('regional_scope_outside_texas', r'home state over a three year period', 'Louisiana-only source scope'),
 'bayou-re-ltd-series-2024-1': ('regional_scope_outside_texas', r'Louisiana named storm reinsurance', 'Louisiana-only source scope'),
 'citrus-re-ltd-series-2024-1': ('regional_scope_outside_texas', r'initially be for the US states of Alabama, Florida, Georgia, Mississippi, North Carolina and South Carolina', 'Possible later Maryland/Virginia expansion; verify amendments'),
 'claveau-re-ltd-series-2021-1': ('broad_us_scope_weights_unverified', r'US & Canada named storm and earthquake', 'Aggregate trigger; US named-storm contribution cap'),
 'everglades-re-ii-ltd-series-2024-1': ('regional_scope_outside_texas', r'annual aggregate named storm reinsurance for the state of Florida', ''),
 'first-coast-re-iii-pte-ltd-series-2021-1': ('regional_scope_outside_texas', r'exposed to Florida named storms', ''),
 'frontline-re-ltd-series-2018-1': ('regional_scope_outside_texas', r'initially for the states of Florida, North & South Carolina and Alabama', 'Original four-year term; extension, trapped collateral and regional amendments need review'),
 'galileo-re-ltd-series-2023-1': ('broad_us_scope_weights_unverified', r'weighted industry loss index trigger', 'Do not infer geographic index weights'),
 'gateway-re-ltd-series-2024-1': ('explicit_texas', r'Louisiana, Mississippi, and Texas', 'Verify tranche-specific coverage term'),
 'gateway-re-ii-ltd-series-2023-1': ('explicit_texas', r'South Carolina, Texas, and Virginia', ''),
 'merna-re-ii-ltd-series-2023-1': ('texas_explicitly_excluded', r'excluding California and Texas', ''),
 'mona-lisa-re-ltd-series-2021-1': ('broad_us_scope_weights_unverified', r'U.S., Puerto Rico, U.S. Virgin Islands and D.C. named storms', 'Industry loss index; annual aggregate'),
 'montoya-re-ltd-series-2022-1': ('broad_us_scope_weights_unverified', r'PCS industry loss index trigger', 'Parsed trigger says Indemnity; source prose says industry loss index: unresolved conflict'),
 'sanders-re-iii-ltd-series-2023-2': ('regional_scope_outside_texas', r'perils of Florida named storm', ''),
 'sanders-re-ii-ltd-series-2021-2': ('broad_us_scope_weights_unverified', r'across all states except for Florida', ''),
 'solomon-re-ltd-series-2023-1': ('broad_us_scope_weights_unverified', r'certain losses from US named storms', 'Industry loss trigger; index weights not verified'),
 '2001-cat-re-ltd-series-2023-1': ('broad_us_scope_weights_unverified', r'losses from U.S named storms', 'Class A in deal prose is not a verified CUSIP-to-Class-A mapping'),
 'umigame-re-pte-ltd-series-2021-1': ('no_us_named_storm_peril', r'Japanese typhoons or Japanese flood', ''),
}


def paragraphs(page):
    return [' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', p)).split())
            for p in re.findall(r'<p\b[^>]*>(.*?)</p>', page, re.S | re.I)]


def run():
    out = output_dir(); cfg = load_config()
    queue = pd.read_csv(out/'study_mapping_review_queue.csv', dtype={'cusip': str})
    queue = queue[queue.storm.eq('beryl') & queue.specific_contracts_with_trade_overlap.gt(0)]
    deals = load.read_deals(); bridge = load.read_bridge(); holdings = load.read_nport_holdings()
    joined = queue.merge(deals, on='deal_url', validate='many_to_one')
    if set(joined.deal_slug) != set(REVIEWS):
        raise ValueError('Candidate set changed; explicit review required')
    raw = Path(cfg['siblings']['issuance'])/'raw'; rows = []
    for r in joined.to_dict('records'):
        slug = r['deal_slug']; status, pattern, notes = REVIEWS[slug]
        paths = list(raw.glob('*'+slug+'__*.html'))
        if len(paths) != 1:
            raise ValueError(f'Expected one source cache for {slug}, found {len(paths)}')
        path = paths[0]; evidence = [p for p in paragraphs(path.read_text()) if re.search(pattern, p, re.I)]
        if not evidence:
            raise ValueError(f'Review evidence changed for {slug}')
        identity = bridge[bridge.cusip_id.eq(r['cusip']) & bridge.deal_url.eq(r['deal_url'])]
        if len(identity) != 1:
            raise ValueError('Nonunique bridge evidence')
        h = holdings[holdings.cusip.eq(r['cusip'])]
        class_titles = h[h.title.str.contains(r'\bClass\s+'+re.escape(str(r['tranche_class']).replace('Class ',''))+r'\b', case=False, regex=True, na=False)] if pd.notna(r['tranche_class']) else h.iloc[:0]
        rows.append({**r, 'reviewed_texas_scope': status, 'review_notes': notes,
                     'review_basis': 'cached secondary deal reporting; offering terms and amendments unverified',
                     'source_cache': str(path), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'scope_evidence': '\n'.join(evidence), 'bridge_evidence_json': json.dumps(identity.iloc[0].to_dict()),
                     'class_title_first_period_end': class_titles.period_end.min() if len(class_titles) else '',
                     'class_title_first_filing_date': class_titles.filing_date.min() if len(class_titles) else '',
                     'class_title_accessions': ';'.join(sorted(set(class_titles.accession))),
                     'class_title_timing_note': 'identity evidence may postdate Beryl; not contemporaneous risk data',
                     'hand_verified_tranche_exposure': False})
    reviewed = pd.DataFrame(rows)
    reviewed.to_csv(out/'beryl_mapping_source_review.csv', index=False)
    summary = reviewed.groupby('reviewed_texas_scope').agg(cusips=('cusip','size'),
                  event8_overlap_cusips=('specific_event8_overlap_dates', lambda x: int(x.gt(0).sum())),
                  repeat_event8_overlap_cusips=('specific_event8_overlap_dates', lambda x: int(x.ge(2).sum())))
    summary.to_csv(out/'beryl_mapping_review_summary.csv')
    print(summary.to_string())


if __name__ == '__main__':
    run()
