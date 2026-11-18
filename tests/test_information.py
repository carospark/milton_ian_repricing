import io
import unittest
import zipfile

import pandas as pd
import shapefile

from milton_ian.match import prior_day_prices, execution_times, intraday_prices
from milton_ian.wsp import grid_values


class InformationTests(unittest.TestCase):
    def test_execution_clock_localizes_eastern_with_dst(self):
        rows = pd.DataFrame({'trade_date':['2024-07-05','2024-01-05','2024-11-03'],
                             'trade_time':['12:00:00','12:00:00','01:30:00']})
        stamps = execution_times(rows)
        self.assertEqual(stamps.iloc[0].hour,16)
        self.assertEqual(stamps.iloc[1].hour,17)
        self.assertTrue(pd.isna(stamps.iloc[2]))

    def test_intraday_excludes_future_ties_and_stale_samples(self):
        trades = pd.DataFrame({'storm':['beryl']*3,'trade_date':['2024-07-05']*3,
                               'trade_time':['12:00:00','13:00:00','18:00:00'],'price':[99]*3})
        prices = pd.DataFrame({'storm':['beryl']*3,'source_id':['test']*3,
                               'timestamp_utc':['2024-07-05T15:00:00Z','2024-07-05T16:00:00Z','2024-07-06T00:00:00Z'],
                               'price':[.4,.5,.9]})
        result = intraday_prices(trades,prices,1)
        self.assertEqual(result.price_market.tolist(),[.4,.5])
        self.assertTrue(result.market_sample_age_hours.eq(1).all())

    def test_prior_day_excludes_same_day_and_does_not_carry_across_gap(self):
        trades = pd.DataFrame({'storm':['beryl']*3,'trade_date':['2024-07-06','2024-07-07','2024-07-09'], 'price':[99]*3})
        prices = pd.DataFrame({'storm':['beryl']*3,'source_id':['test']*3,
                               'timestamp_utc':['2024-07-06T02:00:00Z','2024-07-06T03:00:00Z','2024-07-06T16:00:00Z'],
                               'price':[.4,.5,.9]})
        matched = prior_day_prices(trades, prices)
        self.assertEqual(matched.trade_date.dt.strftime('%Y-%m-%d').tolist(), ['2024-07-06','2024-07-07'])
        self.assertEqual(matched.price_market.tolist(), [.5,.9])

    def test_missing_grid_or_threshold_is_not_zero(self):
        cycle = '2024070700'; stem = cycle+'_wsp34knt120hr_halfDeg'
        shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
        writer = shapefile.Writer(shp=shp,shx=shx,dbf=dbf,shapeType=shapefile.POINT)
        writer.field('PWIND120','N', decimal=1)
        writer.point(-95.5,29.5); writer.record(71.5); writer.close()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            for suffix, stream in [('shp',shp),('shx',shx),('dbf',dbf)]: z.writestr(stem+'.'+suffix,stream.getvalue())
            z.writestr(stem+'.shp.xml','PWIND120 0-120')
        points = [('present',29.5,-95.5),('absent',30.,-95.5)]
        values = grid_values(buffer.getvalue(),cycle,34,points)
        self.assertEqual(values[0]['probability_pct'],71.5)
        self.assertIsNone(values[1]['probability_pct'])
        values = grid_values(buffer.getvalue(),cycle,64,points)
        self.assertTrue(all(v['probability_pct'] is None for v in values))
        self.assertTrue(all(v['point_status']=='threshold_layer_absent_not_imputed' for v in values))
