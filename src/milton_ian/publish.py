"""Export an explicit allowlist of aggregate results for the public repository.

No trade IDs, CUSIPs, prices by bond, holdings, source excerpts or cache paths.
Price-change cells with fewer than five paired CUSIPs remain suppressed.
"""
import pandas as pd
from .paths import output_dir


def run():
    out=output_dir()
    coverage=pd.read_csv(out/'study_coverage.csv')
    validation=pd.read_json(out/'study_validation.json')
    coverage=coverage[['storm','landfall','eligible_cusips','three_customer_trades_each_side',
                       'event8_customer_trade_days_total','event8_repeated_customer_cusips',
                       'specific_contracts_non_null_window','specific_overlap_cusips']]
    coverage.merge(validation,on=['storm','eligible_cusips'],validate='one_to_one').to_csv(out/'public_study_coverage.csv',index=False)
    timing=pd.read_csv(out/'study_intraday_match_summary.csv')
    timing.to_csv(out/'public_timing_summary.csv',index=False)
    inventory=pd.read_csv(out/'wsp_inventory.csv')
    inventory.groupby(['storm_context','status']).size().rename('cycles').reset_index().to_csv(out/'public_wsp_inventory.csv',index=False)
    focus=pd.read_csv(out/'study_focus_review_summary.csv')
    focus.to_csv(out/'public_focus_review_summary.csv',index=False)
    repricing=pd.read_csv(out/'study_repricing_summary.csv')
    if repricing.loc[repricing.paired_cusips.lt(5),'median_change_price_points'].notna().any():
        raise ValueError('Small-cell price statistic would be published')
    repricing.to_csv(out/'public_repricing_summary.csv',index=False)
    nhc=pd.read_csv(out/'nhc_intensity_timeline.csv')
    nhc[['storm','advisory_number','issue_time_utc','corrected','current_max_sustained_wind_knots',
         'near24h_forecast_wind_knots','near24h_actual_lead_hours','forecast_point_count','source_url']].to_csv(out/'public_nhc_intensity.csv',index=False)
    pd.read_csv(out/'study_loss_audit_summary.csv').to_csv(out/'public_loss_audit_summary.csv',index=False)
    pd.read_csv(out/'beryl_mapping_review_summary.csv').to_csv(out/'public_beryl_scope_summary.csv',index=False)
    print('Exported eight aggregate/official-NOAA tables; detailed data remains ignored')


if __name__=='__main__': run()
