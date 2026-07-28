import unittest
from unittest.mock import patch

from line_bot import sheets_monitor as monitor


class Response:
    headers = {'Content-Type': 'text/csv'}
    encoding = None
    text = ''

    def raise_for_status(self):
        return None


class SheetsMonitorTests(unittest.TestCase):
    def response(self, text, status_error=None):
        response = Response()
        response.text = text
        if status_error:
            response.raise_for_status = status_error
        return response

    @patch('line_bot.sheets_monitor.time.sleep')
    @patch('line_bot.sheets_monitor.requests.get')
    def test_http_error_retries_then_fails(self, get, sleep):
        def fail():
            raise monitor.requests.HTTPError('500')
        get.return_value = self.response('', fail)
        with self.assertRaises(RuntimeError):
            monitor._fetch_csv('https://example.test/data.csv')
        self.assertEqual(get.call_count, 3)

    @patch('line_bot.sheets_monitor.requests.get')
    def test_core_requires_all_fields(self, get):
        get.return_value = self.response('欄位,值\n合資總資產,100\n')
        with self.assertRaises(ValueError):
            monitor.fetch_core_data()

    @patch('line_bot.sheets_monitor.requests.get')
    def test_weekly_uses_previous_sorted_valid_record(self, get):
        get.return_value = self.response(
            '日期,資產,投入,股價\n'
            '2026/01/11,100,90,10\n'
            'bad,NaN,0,0\n'
            '2026/01/25,130,100,13\n'
            '2026/01/18,120,95,12\n'
        )
        self.assertEqual(monitor.fetch_weekly_comparison(), {
            'ta': 120.0, 'sp': 12.0, 'date': '2026/01/18'
        })


if __name__ == '__main__':
    unittest.main()
