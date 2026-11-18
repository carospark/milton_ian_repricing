"""Scientific figure from official NOAA forecasts and contextual WSP samples."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import yaml


def run():
    out=ROOT/'data/derived'; forecasts=pd.read_csv(out/'public_nhc_intensity.csv')
    wind=pd.read_csv(out/'wsp_location_context.csv')
    definitions=yaml.safe_load((ROOT/'config_comparison.yaml').read_text())['storms']
    selected=yaml.safe_load((ROOT/'config_study.yaml').read_text())['storms']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(4,2,figsize=(13,13),layout='constrained')
    for row,storm in enumerate(selected):
        t0=pd.Timestamp(definitions[storm]['landfall'],tz='UTC')
        f=forecasts[forecasts.storm.eq(storm)].copy()
        f['days']=(pd.to_datetime(f.issue_time_utc,utc=True)-t0).dt.total_seconds()/86400
        ax=axes[row,0]
        ax.plot(f.days,f.current_max_sustained_wind_knots,color='#175d85',label='Current advisory intensity')
        ax.plot(f.days,f.near24h_forecast_wind_knots,'--',color='#a65426',label='Forecast nearest +24h (18–30h)')
        corrected=f[f.corrected]
        ax.scatter(corrected.days,corrected.current_max_sustained_wind_knots,marker='x',color='black',s=45,zorder=4,label='Corrected archive version' if len(corrected) else None)
        ax.set_title(storm.title()+': NHC maximum sustained wind',loc='left',fontweight='bold')
        ax.set_ylabel('Knots'); ax.set_ylim(bottom=0)
        w=wind[wind.storm_context.eq(storm)&wind.threshold_knots.eq(64)].copy()
        ax=axes[row,1]
        expected=pd.date_range(t0-pd.Timedelta(days=7),t0+pd.Timedelta(days=2),freq='6h',inclusive='left')
        for location,g in w.groupby('location'):
            g=g.set_index(pd.to_datetime(g.cycle_utc,utc=True)).reindex(expected)
            days=(g.index-t0).total_seconds()/86400
            ax.plot(days,g.probability_pct,marker='.',markersize=3,label=location.replace('_',' '))
        ax.set_title(storm.title()+': all-basin 64-knot probability context',loc='left',fontweight='bold')
        ax.set_ylabel('0–120h cumulative probability (%)'); ax.set_ylim(0,105)
        for ax in axes[row]:
            ax.axvline(0,color='#777',linestyle=':',linewidth=1)
            ax.set_xlim(-7,2); ax.set_xlabel('Days from landfall date at 00 UTC')
            ax.grid(alpha=.2); ax.legend(loc='upper left',fontsize=8)
    fig.suptitle('Official forecast evolution and local wind context\nIssue / initialization times are not verified publication times; GIS products combine active storms',fontsize=14)
    folder=ROOT/'figures'; folder.mkdir(exist_ok=True)
    fig.savefig(folder/'nhc_information_context.png',dpi=160)
    plt.close(fig)
    print(folder/'nhc_information_context.png')


if __name__=='__main__': run()
