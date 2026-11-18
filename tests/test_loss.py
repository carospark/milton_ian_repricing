import unittest
from milton_ian.loss import loss_evidence


class LossTests(unittest.TestCase):
    def test_mark_to_market_total_loss_is_not_terminal(self):
        row={'cause_of_loss':'Hurricane Ian','loss_amount':'Mark to market implied ~100% loss of principal.',
             'loss_status':'total_loss','derived_confidence':'high','cat_bond':'Test Class C'}
        result=loss_evidence(row,'ian')
        self.assertTrue(result['total_loss_label_prose_conflict'])
        self.assertFalse(result['terminal_loss_prose_candidate'])
        self.assertEqual(result['source_class'],'Class C')

    def test_multi_event_loss_not_attributed_to_single_storm(self):
        row={'cause_of_loss':'Hurricane Ian, winter storm, earthquake','loss_amount':'Principal reduced to zero.',
             'loss_status':'total_loss','derived_confidence':'high','cat_bond':'Test'}
        result=loss_evidence(row,'ian')
        self.assertEqual(result['attribution_scope'],'multi_event_source_label')
        self.assertFalse(result['terminal_loss_prose_candidate'])
        self.assertEqual(result['source_class'],'')
