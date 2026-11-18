"""Audit source loss labels without propagating deal outcomes to every tranche.

Dates in the source are event dates, not verified information-release dates.
Source labels are screened against their prose before being used as evidence.
"""
import re
import pandas as pd
import yaml
from .paths import ROOT, require, output_dir
from .sample import CLASS


def loss_evidence(row,storm):
    cause=row['cause_of_loss'].strip()
    single=bool(re.fullmatch(r'(?:Hurricane\s+)?'+re.escape(storm)+r'[.\s]*',cause,re.I))
    provisional=bool(re.search(r'mark(?:ed)?[ -]to[ -]market|TBC|implied|expected|possible',row['loss_amount'],re.I))
    contradiction=row['loss_status']=='total_loss' and provisional
    classes=sorted(set('Class '+x.upper() for x in CLASS.findall(row['cat_bond'])))
    return {'attribution_scope':'single_storm_source_label' if single else 'multi_event_source_label',
            'loss_prose_provisional':provisional,'total_loss_label_prose_conflict':contradiction,
            'source_class':classes[0] if len(classes)==1 else '',
            'terminal_loss_prose_candidate':single and row['loss_status']=='total_loss' and row['derived_confidence']=='high' and not provisional,
            'announcement_time_status':'not available; date_of_loss is not announcement time'}


def run():
    out=output_dir(); losses=pd.read_csv(require('losses'),dtype=str,keep_default_na=False)
    selected=yaml.safe_load((ROOT/'config_study.yaml').read_text())['storms']
    bonds=pd.read_csv(out/'study_mapping_review_queue.csv',dtype={'cusip':str},keep_default_na=False)
    rows=[]; summary=[]
    for storm in selected:
        matched=losses[losses.cause_of_loss.str.contains(r'\b'+storm+r'\b',case=False,regex=True)]
        storm_rows=[]
        for r in matched.to_dict('records'):
            evidence=loss_evidence(r,storm)
            linked=bonds[bonds.storm.eq(storm)&bonds.deal_url.eq(r['deal_url'])]
            same_class=linked[linked.tranche_class.eq(evidence['source_class'])&linked.class_match_status.eq('matched_explicit_nport_class')] if evidence['source_class'] else linked.iloc[:0]
            item={**r,**evidence,'storm':storm,'same_deal_eligible_cusips':len(linked),
                  'source_class_supported_cusips':len(same_class),'eligible_cusips':';'.join(linked.cusip),
                  'source_class_supported_cusip_ids':';'.join(same_class.cusip),
                  'mapping_limit':'parsed class support, not offering-document verification; no deal-wide loss propagation'}
            rows.append(item); storm_rows.append(item)
        frame=pd.DataFrame(storm_rows)
        summary.append({'storm':storm,'source_rows':len(frame),
                        'single_storm_source_rows':int(frame.attribution_scope.eq('single_storm_source_label').sum()) if len(frame) else 0,
                        'multi_event_source_rows':int(frame.attribution_scope.eq('multi_event_source_label').sum()) if len(frame) else 0,
                        'provisional_prose_rows':int(frame.loss_prose_provisional.sum()) if len(frame) else 0,
                        'total_loss_label_prose_conflicts':int(frame.total_loss_label_prose_conflict.sum()) if len(frame) else 0,
                        'terminal_loss_prose_candidates':int(frame.terminal_loss_prose_candidate.sum()) if len(frame) else 0,
                        'terminal_candidates_with_exact_class_support':int((frame.terminal_loss_prose_candidate&frame.source_class_supported_cusips.gt(0)).sum()) if len(frame) else 0})
    pd.DataFrame(rows).to_csv(out/'study_loss_source_audit.csv',index=False)
    pd.DataFrame(summary).to_csv(out/'study_loss_audit_summary.csv',index=False)
    print(pd.DataFrame(summary).to_string(index=False))


if __name__=='__main__': run()
