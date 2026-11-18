import unittest
from milton_ian.nhc import parse_advisory
from milton_ian.forecast import forecast_points
import pandas as pd


class AdvisoryTests(unittest.TestCase):
    def test_forecast_month_rollover_and_signs(self):
        body='FORECAST VALID 01/0600Z 24.5N  84.5W\nMAX WIND  80 KT...GUSTS 95 KT.'
        points=forecast_points(body,pd.Timestamp('2022-09-30T21:00:00Z'))
        self.assertEqual(points[0]['valid_time_utc'],'2022-10-01T06:00:00+00:00')
        self.assertEqual(points[0]['lead_hours_from_issue'],9)
        self.assertEqual(points[0]['longitude'],-84.5)

    def test_unparsed_forecast_fails_closed(self):
        with self.assertRaises(ValueError):
            forecast_points('FORECAST VALID unexpected',pd.Timestamp('2024-07-01T00:00:00Z'))

    def test_explicit_dissipation_is_not_zero_wind(self):
        points=forecast_points('OUTLOOK VALID 02/0000Z...DISSIPATED',pd.Timestamp('2024-07-01T00:00:00Z'))
        self.assertEqual(points[0]['forecast_status'],'dissipated')
        self.assertIsNone(points[0]['max_sustained_wind_knots'])

    def test_corrected_issue_time_is_not_publication_time(self):
        row = parse_advisory('<pre>HURRICANE BERYL FORECAST/ADVISORY NUMBER 1...CORRECTED\n2100 UTC FRI JUN 28 2024\n</pre>')
        self.assertEqual(row['issue_time_utc'], '2024-06-28T21:00:00+00:00')
        self.assertTrue(row['corrected'])
        self.assertIn('publication time unverified', row['timing_status'])

    def test_fail_closed_on_missing_time(self):
        with self.assertRaises(ValueError):
            parse_advisory('<pre>FORECAST/ADVISORY NUMBER 2</pre>')
