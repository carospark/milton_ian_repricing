import unittest
import pandas as pd
from milton_ian.repricing import paired_changes, aggregate_pairs


class RepricingTests(unittest.TestCase):
    def test_daily_equal_weights_same_side_and_competing_storm(self):
        rows=[]
        for date,day,price in [('2024-06-01',-37,100),('2024-06-02',-36,90),('2024-07-08',0,80),('2024-07-09',1,70)]:
            for _ in range(4 if price==100 else 1):
                rows.append({'storm':'beryl','cusip_id':'test','dealer_side':'S','contra_party':'C','trade_date':date,'days_from_landfall':day,'price':price})
        # Different side never becomes a same-side observation.
        rows.append({**rows[-1],'dealer_side':'B','price':60})
        definitions={'beryl':{'landfall':'2024-07-08'},'other':{'landfall':'2024-06-02'}}
        pairs,daily=paired_changes(pd.DataFrame(rows),definitions)
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs.iloc[0].reference_price,95)
        self.assertEqual(pairs.iloc[0].change_price_points,-20)
        self.assertEqual(pairs.iloc[0].reference_days,2)
        self.assertEqual(pairs.iloc[0].other_catalog_landfalls_in_windows,'other')
        self.assertEqual(len(daily),5)

    def test_public_small_cells_suppress_price_changes(self):
        pairs=pd.DataFrame({'storm':['beryl'],'customer_action':['buy'],'comparison_window':['impact'],
                            'reference_days':[2],'comparison_days':[2],'other_catalog_landfalls_in_windows':[''],
                            'scope_review_status':['explicit_target_state'],'cusip_id':['test'],'change_price_points':[-20]})
        summary=aggregate_pairs(pairs,['beryl'])
        self.assertTrue(summary.median_change_price_points.isna().all())
        self.assertFalse(summary.reported.any())
