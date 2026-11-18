"""Public briefing: explicit aggregate exports and official NOAA data only."""
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/derived'


def table(frame):
    return '<div class="scroll">'+frame.to_html(index=False,border=0,na_rep='—',float_format=lambda x:f'{x:.3f}',escape=True)+'</div>'


def run():
    coverage=pd.read_csv(OUT/'public_study_coverage.csv')
    timing=pd.read_csv(OUT/'public_timing_summary.csv')
    inventory=pd.read_csv(OUT/'public_wsp_inventory.csv')
    focus=pd.read_csv(OUT/'public_focus_review_summary.csv')
    repricing=pd.read_csv(OUT/'public_repricing_summary.csv')
    nhc=pd.read_csv(OUT/'public_nhc_intensity.csv')
    losses=pd.read_csv(OUT/'public_loss_audit_summary.csv')
    sample=coverage[['storm','landfall','eligible_cusips','three_customer_trades_each_side',
                     'eligible_customer_trades_event8','event8_customer_trade_days_total',
                     'event8_repeated_customer_cusips','nhc_advisories']]
    counts=inventory.pivot(index='storm_context',columns='status',values='cycles').fillna(0).astype(int).reset_index()
    short=timing[timing.period.eq('prelandfall_event8')]
    reviewed=focus.pivot(index='storm',columns='scope_review_status',values='cusips').fillna(0).astype(int).reset_index()
    price=repricing[repricing.minimum_observed_days_each_window.eq(2)&repricing.restriction.eq('all_strict')&repricing['sample'].eq('all_identity_eligible')&repricing.customer_action.eq('buy')]
    price=price[['storm','comparison_window','paired_cusips','median_change_price_points']]
    figure='<img src="../figures/nhc_information_context.png" alt="Four-storm forecast intensity and all-basin local wind-probability context">' if (ROOT/'figures/nhc_information_context.png').exists() else ''
    overview='<img src="../figures/hurricane_repricing_summary.png" alt="Visual summary of completed research, bond coverage and qualified findings">' if (ROOT/'figures/hurricane_repricing_summary.png').exists() else ''
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hurricane repricing study</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f4f7fa;color:#203346;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:36px 22px 70px}}h1,h2,h3{{line-height:1.2}}h1{{font-size:2.4rem}}h2{{margin-top:42px}}.lede{{font-size:1.2rem;color:#456}}.card{{background:#fff;border:1px solid #d9e2ea;border-radius:12px;padding:22px;margin:18px 0}}.note{{border-left:5px solid #16817a}}.warning{{border-left:5px solid #d19132}}.scroll{{overflow:auto;max-height:520px;margin:18px 0}}table{{border-collapse:collapse;min-width:100%;font-size:14px}}th,td{{padding:9px 12px;border-bottom:1px solid #dce5ed;text-align:left;white-space:nowrap}}th{{background:#e9f0f6;position:sticky;top:0}}img{{width:100%;height:auto}}a{{color:#126a9c}}.small{{font-size:.9rem;color:#53677a}}@media(max-width:650px){{main{{padding:22px 12px}}h1{{font-size:1.8rem}}.card{{padding:16px}}}}</style></head><body><main>
<p class="small">Research update · 18 November 2026 · descriptive analysis</p>
<h1>Hurricane repricing study</h1><p class="lede">Ian, Milton, Idalia and Beryl. Four selected storms, one reproducible pipeline. The first results establish which information and bond observations can be linked, and where trading is too sparse for a persuasive expectations-to-repricing claim.</p>{overview}
<div class="card note">Built: {len(nhc)} official forecast advisories, {int(nhc.forecast_point_count.sum())} forecast-valid-time records and {int(inventory.loc[inventory.status.eq('cached_and_parsed'),'cycles'].sum())} all-basin wind-probability snapshots. Source-prose geography checks, conservative and intraday market matches, and same-bond price comparisons are reproducible. Detailed licensed data remain local.</div>
<h2>The usable bond sample</h2><p>Strict eligibility requires one high-confidence, non-propagated CUSIP-to-deal match. It establishes identity, not verified tranche terms, active coverage or event sensitivity. Full window: inclusive −45/+60 (106 calendar dates). Event interval: −4/+3. Multiple prints on one date do not provide multiple observation dates. “Each side” below means before/after landfall; other panels distinguish customer buys/sells.</p>{table(sample)}
<h2>Official forecasts and geographic wind context</h2><p>All index-listed forecast advisories for the selected storms are cached. Three are corrected versions; stated issue times are not verified first-publication times. Forecast positions, winds and valid times are parsed. Explicit dissipation records retain missing wind and location rather than a zero estimate.</p>{figure}
<div class="card warning"><b>Different probability outcomes:</b> NHC GIS files combine all basins and active storms. They measure cumulative local wind-threshold exceedance over 0–120 hours, not named-storm landfall or bond impairment. Fixed half-degree points provide geographic context, not exposure weights. Missing points and threshold layers remain missing. Cycle times are initialization times, not publication times.</div>{table(counts)}
<p class="small">Nine UTC dates per storm, landfall −7 through +1, every six hours. Beryl's July 9 06/12/18 UTC cycles are not listed in the cached index; this does not prove no copy exists elsewhere.</p>
<h2>Geography changes the Beryl screen</h2><p>Of the original 23 same-date market-overlap CUSIPs, source prose supports explicit Texas scope for three. Eight have broader US scope with unverified weights. Twelve have regional restrictions, Texas exclusions or no US named-storm peril. Neither repeatedly overlapping event-week bond is in the three with explicit Texas scope.</p><p>The expanded source review below includes other bonds with trading on both sides or named-market overlap. It is a different sample from the original 23. Unreviewed bonds remain pending. Reviewed geography does not verify offering amendments, active risk periods or CUSIP/tranche identity.</p>{table(reviewed)}
<div class="card warning">Historical broad-region classifications need care: Alamo is Texas-specific, Bayou Louisiana-specific, and Astro's source prose describes southeastern states despite a broad US peril field. Montoya's parsed trigger says indemnity while source prose says PCS industry loss index. Conflicts are recorded locally without rewriting sibling datasets.</div>
<h2>Market information before execution</h2><p>The source cleaner maps trade execution date/time. <a href="https://www.finra.org/sites/default/files/CA-CTCI-specs-v3.4.pdf">FINRA's TRACE specification</a> defines the execution clock in Eastern Time. The pipeline applies daylight-saving rules before converting to UTC; invalid or ambiguous times remain unmatched.</p><p>Intraday matches select the most recent strictly earlier Yes-price sample, exclude timestamp ties, and test maximum ages of 1, 6 and 24 hours. Samples are archived token prices, not executions, actionable quotes or proof of liquidity. Counts below deduplicate trades across contracts and cover calendar days −4 through −1; they do not classify landfall-day trades by exact landfall time.</p>{table(short)}
<p>The preceding-day-only sensitivity remains available locally. Pre-landfall support is thin under both rules. NHC corrected archives and GIS initialization times are not joined as though first-publication times were verified. Temporal order does not establish causality.</p>
<h2>First descriptive price comparisons</h2><p>For each bond and customer side separately: take the median price within each observed date, then the median of those daily medians within a window. Compare with reference −45/−8. Require two observed dates in each window for the table below. Every observed date gets equal weight; no nontrading dates are filled. Customer buys are shown; sell-side and one-date sensitivities are in the aggregate CSV.</p><p>Windows: anticipation −7/−1; impact 0/+7; aftermath +8/+30; late +31/+60. Changes are price points, not investment returns. Statistics are suppressed below five paired bonds. Counts do not imply target-storm exposure.</p>{table(price)}
<div class="card warning"><b>No storm-effect claim:</b> these comparisons mix exposure groups and do not adjust for coupons, accrued interest, maturity, liquidity, trapped collateral, loss news or the broader market. Bond sets differ across windows. A separate sensitivity excludes windows containing another catalogued landfall, but cannot capture every event or its forecast period. Helene falls in Milton's reference window; Debby enters Beryl's aftermath and Helene its late window; Ian's late window includes Nicole.</div>
<h2>Loss labels need their own evidence audit</h2><p>The source loss table is screened against its own prose. One Ian total-loss label conflicts with mark-to-market wording and is not promoted to terminal-loss evidence. Two single-storm Ian rows remain terminal-loss prose candidates, but neither currently has exact source-class support in the strict eligible sample. Deal-level outcomes are never propagated to all tranches. The event date in the source is not an announcement timestamp. No rows for Idalia or Beryl means absence from this source table, not proof of no losses.</p>{table(losses)}
<h2>Next research priorities</h2><ol><li>Verify offering terms, active risk periods and amendments for genuinely relevant bonds. Keep flood, indemnity wind and industry-index triggers distinct.</li><li>Extend source reviews to the newly matched and unresolved bonds across all four storms.</li><li>Recover publication/version evidence where possible; retain all-basin labeling for GIS probabilities.</li><li>Build local bond-level loss/recovery cases before choosing a pooled model. Current support does not justify a rich pre-landfall probability regression.</li></ol>
<p class="small">Sources: configured read-only TRACE/bridge/N-PORT and issuance outputs; local read-only prediction archive; <a href="https://www.nhc.noaa.gov/archive/">NHC advisory archives</a>; <a href="https://www.nhc.noaa.gov/gis/archive_wsp.php">NHC GIS wind-probability archive</a>. Public artifact uses aggregate exports and official NOAA data only. It embeds no literal trade rows, bond-level price paths, source excerpts, holdings or licensed caches.</p></main></body></html>'''
    path=ROOT/'docs/Hurricane_Options_Story.html'; path.write_text(html,encoding='utf-8'); print(path)


if __name__=='__main__': run()
