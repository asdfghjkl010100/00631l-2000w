import unittest
from line_bot.financial import build_snapshot, nav_metrics


class FinancialTests(unittest.TestCase):
    def test_subscription_does_not_change_nav_return(self):
        rows = [{'d': '2026/01/01', 'dk': 20260101, 'n': 10}, {'d': '2026/01/08', 'dk': 20260108, 'n': 10}, {'d': '2026/01/15', 'dk': 20260115, 'n': 10}]
        metrics = nav_metrics(rows)
        self.assertEqual(metrics['annualReturn'], 0)

    def test_snapshot_uses_latest_nav_for_members(self):
        snapshot = build_snapshot({'ta': 200, 'ca': 20, 'sv': 180, 'nav': 10, 'units': 20},
                                  [{'d': '2026/01/01', 'dk': 20260101, 'i': 200, 'n': 10}],
                                  [[{'a': 100, 'u': 10}], [{'a': 100, 'u': 10}]], ['A', 'B'])
        self.assertEqual(snapshot['members'][0]['value'], 100)
        self.assertTrue(all(snapshot['checks'].values()))

    def test_cash_stock_and_members_reconcile(self):
        snapshot = build_snapshot({'ta': 200, 'ca': 20, 'sv': 180, 'nav': 10, 'units': 20},
                                  [{'d': '2026/01/01', 'dk': 20260101, 'i': 200, 'n': 10}],
                                  [[{'a': 100, 'u': 10}], [{'a': 100, 'u': 10}]], ['A', 'B'])
        self.assertTrue(snapshot['checks']['cashPlusStock'])
        self.assertTrue(snapshot['checks']['membersEqualTotal'])


if __name__ == '__main__':
    unittest.main()
