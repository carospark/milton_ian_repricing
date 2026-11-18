"""Numerical NHC forecast trajectories with exact valid times and provenance.

Forecast lead is measured from stated advisory issue time, not inferred product
availability. No wind forecast is converted to a bond impairment probability.
"""
import re
import pandas as pd
from .paths import ROOT, output_dir
from .nhc import parse_advisory


def forecast_points(body, issued):
    pattern=r'(?:FORECAST|OUTLOOK) VALID\s+(\d{2})/(\d{2})(\d{2})Z\s+([\d.]+)([NS])\s+([\d.]+)([EW])[^\n]*\nMAX WIND\s+(\d+) KT'
    matches=list(re.finditer(pattern,body))
    terminal=list(re.finditer(r'(?:FORECAST|OUTLOOK) VALID\s+(\d{2})/(\d{2})(\d{2})Z\.\.\.DISSIPATED',body))
    expected=len(re.findall(r'(?:FORECAST|OUTLOOK) VALID',body))
    if len(matches)+len(terminal)!=expected: raise ValueError('Forecast point format changed; refusing incomplete parse')
    points=[]
    for m in sorted(matches+terminal,key=lambda m:m.start()):
        dissipated=len(m.groups())==3
        day,hour,minute=m.groups()[:3]
        if not dissipated: lat,ns,lon,ew,wind=m.groups()[3:]
        candidates=[]
        for shift in (-1,0,1):
            month=issued.normalize().replace(day=1)+pd.DateOffset(months=shift)
            try: valid=month.replace(day=int(day),hour=int(hour),minute=int(minute))
            except ValueError: continue
            lead=(valid-issued).total_seconds()/3600
            if 0<lead<=144: candidates.append((lead,valid))
        if len(candidates)!=1: raise ValueError('Ambiguous forecast month rollover')
        lead,valid=candidates[0]
        points.append({'valid_time_utc':valid.isoformat(),'lead_hours_from_issue':lead,
                       'latitude':None if dissipated else float(lat)*(1 if ns=='N' else -1),
                       'longitude':None if dissipated else float(lon)*(1 if ew=='E' else -1),
                       'max_sustained_wind_knots':None if dissipated else int(wind),
                       'forecast_status':'dissipated' if dissipated else 'forecast_position_and_wind'})
    return points


def run():
    out=output_dir(); manifest=pd.read_csv(out/'nhc_advisories.csv'); rows=[]; intensity=[]
    for r in manifest.to_dict('records'):
        parsed=parse_advisory((ROOT/r['cache_path']).read_text())
        issued=pd.Timestamp(parsed['issue_time_utc']); body=parsed['text']
        points=forecast_points(body,issued)
        rows.extend({**r,**p} for p in points)
        current=re.search(r'MAX SUSTAINED WINDS\s+(\d+) KT',body)
        if not current: raise ValueError('Missing current intensity')
        near=[p for p in points if 18<=p['lead_hours_from_issue']<=30]
        p24=min(near,key=lambda p:abs(p['lead_hours_from_issue']-24)) if near else None
        intensity.append({**r,'current_max_sustained_wind_knots':int(current[1]),
                          'near24h_forecast_wind_knots':p24['max_sustained_wind_knots'] if p24 else None,
                          'near24h_actual_lead_hours':p24['lead_hours_from_issue'] if p24 else None,
                          'forecast_point_count':len(points)})
    pd.DataFrame(rows).to_csv(out/'nhc_forecast_points.csv',index=False)
    pd.DataFrame(intensity).to_csv(out/'nhc_intensity_timeline.csv',index=False)
    print(pd.DataFrame(intensity).groupby('storm').agg(advisories=('advisory_number','size'),forecast_points=('forecast_point_count','sum')).to_string())


if __name__=='__main__': run()
