"""Small independent edge cases for economically consequential audit rules."""
import unittest
import pandas as pd
from milton_ian.sample import select_mapping, metrics, exposure, class_mapping
from milton_ian.contracts import outcome_map, stamps, category, observation_dates

class AuditTests(unittest.TestCase):
    def test_identity_eligibility_and_ambiguous_pairs(self):
        p=pd.DataFrame(columns=['cusip_id','deal_url'])
        for confidence,title,eligible in [('high','none',True),('medium','none',False),('high','propagated',False)]:
            b=pd.DataFrame([dict(cusip_id='X',deal_url='a',match_confidence=confidence,title_evidence=title,bridge_level='title-propagated' if title=='propagated' else 'strict')])
            self.assertEqual(select_mapping('X',b,p)[1],eligible)
        b=pd.concat([b,b.assign(deal_url='b')])
        mapping,eligible,status,_,_=select_mapping('X',b,p)
        self.assertIsNone(mapping);self.assertFalse(eligible);self.assertIn('ambiguous',status)

    def frame(self):
        return pd.DataFrame({'trade_date':pd.to_datetime(['2024-10-08','2024-10-09','2024-10-10','2024-10-10','2024-10-10']), 'contra_party':['C','C','C','D','A'],'dealer_side':['S','B','?','B','S'],'volume':[30.,10.,4.,50.,100.],'price':[95.,90.,94.,96.,None],'volume_capped':[False]*5})

    def test_day_zero_direction_and_counterparties(self):
        g=self.frame();d=metrics(g,pd.Timestamp('2024-10-09'),pd.Timestamp('2024-10-05'),pd.Timestamp('2024-10-12'))
        self.assertEqual((d['customer_trades_pre'],d['customer_trades_landfall'],d['customer_trades_post']),(1,1,1))
        self.assertEqual(d['net_customer_imbalance_buy_minus_sell'],20.)
        self.assertEqual(d['customer_volume'],44.)
        self.assertEqual(d['event8_all_trading_density'],3/8)
        self.assertEqual(d['other_unknown_counterparty_trades'],1)

    def test_missing_directional_volume_not_zero(self):
        g=self.frame();g.loc[0,'volume']=float('nan')
        d=metrics(g,pd.Timestamp('2024-10-09'),pd.Timestamp('2024-10-05'),pd.Timestamp('2024-10-12'))
        self.assertTrue(pd.isna(d['net_customer_imbalance_buy_minus_sell']))

    def test_missing_exposure_is_unknown_and_exclusion_is_ambiguous(self):
        h=pd.DataFrame([dict(hazard_class='hurricane_or_named_storm',region='us')])
        self.assertEqual(exposure(h.iloc[:0],'', ['us']),'unknown')
        self.assertEqual(exposure(h,'US hurricane excluding Florida',['us']),'ambiguous')
        self.assertEqual(exposure(h,'US hurricane',['us']),'florida_hurricane_exposed')

    def test_conflicting_class_never_gets_risk_metrics(self):
        h=pd.DataFrame({'cusip':['X','X'],'title':['Re 2024-1 Class A','Re 2024-1 Class B']})
        t=pd.DataFrame({'deal_slug':['re-2024-1'],'tranche_id':['Class A'],'expected_loss':['2%']})
        r=class_mapping('X',{'deal_slug':'re-2024-1'},t,h)
        self.assertEqual(r['class_match_status'],'conflicting_nport_classes');self.assertEqual(r['expected_loss'],'')

    def test_probability_outcome_not_lexicographic_token(self):
        import json
        r={'platform':'polymarket','metadata_json':json.dumps({'market':{'clobTokenIds':'["999", "111"]','outcomes':'["Yes", "No"]'}}),'outcome_ids_json':'[]'}
        self.assertEqual(outcome_map(r),{'999':'Yes','111':'No'})

    def test_timestamp_and_seasonal_classification(self):
        d=stamps(pd.Series(['1728514802','2024-10-09T23:00:02Z']))
        self.assertEqual(d.iloc[0],d.iloc[1])
        self.assertEqual(category({'platform':'kalshi','contract_id':'TROPSTORM-24DEC01-T15','title':'Number of tropical storms','metadata_json':'2024'}),'broad_seasonal_count')

    def test_archive_observations_align_to_eastern_trade_days(self):
        frame=pd.DataFrame({'ts':pd.to_datetime(['2024-10-10T04:00:00Z','2024-10-10T03:30:00Z'],utc=True)})
        self.assertEqual(observation_dates(frame,'kalshi').tolist(),['2024-10-09','2024-10-08'])
        self.assertEqual(observation_dates(frame,'polymarket').tolist(),['2024-10-10','2024-10-09'])

if __name__=='__main__':unittest.main()
