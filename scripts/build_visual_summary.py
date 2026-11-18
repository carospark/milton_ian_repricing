"""One-page visual research summary, generated solely from public aggregates."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

INK='#183449'; MUTED='#516779'; TEAL='#087f83'; LIGHT='#dce9ec'; AMBER='#a85d18'


def run():
    out=ROOT/'data/derived'
    coverage=pd.read_csv(out/'public_study_coverage.csv').set_index('storm')
    nhc=pd.read_csv(out/'public_nhc_intensity.csv')
    wsp=pd.read_csv(out/'public_wsp_inventory.csv')
    timing=pd.read_csv(out/'public_timing_summary.csv')
    scope=pd.read_csv(out/'public_beryl_scope_summary.csv').set_index('reviewed_texas_scope')
    loss=pd.read_csv(out/'public_loss_audit_summary.csv').set_index('storm')
    prices=pd.read_csv(out/'public_repricing_summary.csv')
    assert scope.cusips.sum()==coverage.loc['beryl','specific_overlap_cusips']
    fig=plt.figure(figsize=(12,14),facecolor='#f5f8fa')
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'hurricane-repricing-study'})
    canvas=fig.add_axes([0,0,1,1]); canvas.axis('off')
    def text(x,y,s,size=12,color=INK,weight='normal',**kw):
        fig.text(x,y,s,fontsize=size,color=color,fontweight=weight,**kw)
    def card(x,y,w,h):
        canvas.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.012',
                                      facecolor='white',edgecolor='#e0e8ed',linewidth=.8))
    text(.06,.952,'Hurricane repricing study',27,weight='bold')
    text(.06,.924,'Ian · Milton · Idalia · Beryl',15,MUTED)
    text(.94,.928,'RESEARCH SNAPSHOT\n18 NOVEMBER 2026',9,MUTED,ha='right',linespacing=1.5)
    text(.06,.887,'WHAT HAS BEEN DONE',11,TEAL,weight='bold')
    metrics=[(len(nhc),'NHC advisories'),(int(nhc.forecast_point_count.sum()),'forecast-time records'),
             (int(wsp.loc[wsp.status.eq('cached_and_parsed'),'cycles'].sum()),'wind-probability grids')]
    for i,(value,label) in enumerate(metrics):
        x=.06+i*.303
        card(x,.779,.276,.086)
        text(x+.018,.824,f'{value:,}',27,weight='bold')
        text(x+.018,.794,label,11,MUTED)
    text(.06,.752,'Collected & frozen  →  Bond identities linked  →  Timing, geography & losses audited',12,weight='bold')
    text(.06,.728,'Observed-price comparisons built · Offline rebuild verified · Public aggregate exports',11,MUTED)
    card(.06,.445,.88,.251)
    text(.08,.670,'A broad inventory; few bonds trade repeatedly near landfall',15,weight='bold')
    text(.08,.649,'Counts are distinct bond identifiers, not verified tranche / exposure assignments.',10,MUTED)
    ax=fig.add_axes([.17,.489,.68,.135]); ax.set_facecolor('white')
    storms=['ian','milton','idalia','beryl']; vals=coverage.loc[storms,'eligible_cusips']
    repeat=coverage.loc[storms,'event8_repeated_customer_cusips']
    ax.barh(range(4),vals,color=LIGHT,height=.48)
    ax.barh(range(4),repeat,color=TEAL,height=.48)
    for i,(n,r) in enumerate(zip(vals,repeat)):
        ax.text(n+3,i,f'{r} / {n}',va='center',fontsize=11,color=INK)
    ax.set_yticks(range(4),[s.title() for s in storms],color=INK,fontsize=12)
    ax.invert_yaxis(); ax.set_xlim(0,max(vals)+35); ax.set_xticks([])
    ax.tick_params(left=False); ax.spines[['top','right','bottom','left']].set_visible(False)
    text(.08,.462,'Teal = traded on ≥2 dates in the −4/+3-day interval. Pale = all strict eligible bonds.',10,MUTED)
    price=prices[prices.storm.eq('beryl')&prices.customer_action.eq('buy')&prices.comparison_window.eq('impact')&prices.minimum_observed_days_each_window.eq(2)&prices.restriction.eq('all_strict')&prices['sample'].eq('all_identity_eligible')].iloc[0]
    if price.paired_cusips>=5:
        text(.06,.426,f'Beryl price screen: {price.median_change_price_points:+.2f} points ({int(price.paired_cusips)} paired bonds, days 0/+7 vs −45/−8); mixed exposure, descriptive only.',9.8,MUTED)
    card(.06,.213,.423,.197); card(.517,.213,.423,.197)
    text(.08,.384,'Beryl: overlap ≠ Texas exposure',15,weight='bold')
    total=int(scope.cusips.sum()); texas=int(scope.loc['explicit_texas','cusips'])
    broad=int(scope.loc['broad_us_scope_weights_unverified','cusips']); restricted=total-texas-broad
    text(.08,.352,f'{texas} of {total}',27,TEAL,weight='bold')
    text(.08,.331,'original market-overlap bonds have explicit Texas scope',9.5,MUTED)
    text(.08,.301,f'{broad} broader US scope · {restricted} restricted / other peril',11,weight='bold')
    text(.08,.269,'Secondary-source geography only;\noffering terms and active coverage need verification.',10,MUTED,linespacing=1.5)
    text(.537,.384,'Pre-landfall market matches are thin',14,weight='bold')
    pre=timing[timing.max_age_hours.eq(24)&timing.period.eq('prelandfall_event8')].set_index('storm')
    for y,storm in [(.346,'beryl'),(.314,'idalia')]:
        r=pre.loc[storm]
        text(.537,y,storm.title(),12,weight='bold')
        text(.695,y,f'{int(r.cusips)} bond'+('s' if r.cusips!=1 else '')+f' · {int(r.customer_trades)} trades',12,TEAL,weight='bold')
    text(.537,.269,'Strictly earlier market samples, at most 24 hours old.\nCalendar days −4/−1; landfall day excluded.',10,MUTED,linespacing=1.5)
    card(.06,.092,.88,.087)
    text(.08,.153,'Ian: a loss label is not yet a verified bond outcome',14,weight='bold')
    r=loss.loc['ian']
    text(.08,.128,f'{int(r.total_loss_label_prose_conflicts)} label / prose conflict  ·  {int(r.terminal_loss_prose_candidates)} terminal-loss prose candidates  ·  {int(r.terminal_candidates_with_exact_class_support)} exact class links',12,AMBER,weight='bold')
    text(.08,.107,'Mark-to-market estimates remain provisional; deal losses are not assigned to every tranche.',10,MUTED)
    text(.06,.060,'Current evidence supports descriptive timelines and targeted bond case studies.',12,weight='bold')
    text(.06,.040,'Causal repricing effects remain unestablished. GIS grids combine active storms; issue times ≠ publication times.',9.5,MUTED)
    text(.06,.021,'Source: public aggregate study exports + official NHC data. No raw trades, holdings or source excerpts shown.',8.5,MUTED)
    folder=ROOT/'figures'; folder.mkdir(exist_ok=True)
    for suffix in ('png','svg'):
        target=folder/f'hurricane_repricing_summary.{suffix}'
        fig.savefig(target,dpi=180,facecolor=fig.get_facecolor(),metadata={'Date':None} if suffix=='svg' else {})
        if suffix=='svg': target.write_text('\n'.join(line.rstrip() for line in target.read_text().splitlines())+'\n')
    plt.close(fig)
    print(folder/'hurricane_repricing_summary.png')


if __name__=='__main__': run()
