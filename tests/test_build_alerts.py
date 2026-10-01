import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from build_alerts import build, check_sane, parse_date, strip_html  # noqa: E402

TODAY = date(2026, 10, 1)


def food(light, title, day, body="<p>內容&nbsp;說明</p>"):
    return {"燈號": light, "標題名稱": title, "內容": body, "更新日期": day}


class BuildAlertsTest(unittest.TestCase):
    def test_strip_html(self):
        self.assertEqual(strip_html("<ol>\r\n<li><span>香港</span>&amp; 食安</li></ol>"), "香港 & 食安")
        self.assertEqual(strip_html(None), "")

    def test_parse_date(self):
        self.assertEqual(parse_date("2026/09/14"), date(2026, 9, 14))
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date("not a date"))

    def test_keeps_red_and_yellow_only(self):
        rows = [food("紅燈", "A", "2026/09/01"), food("黃燈", "B", "2026/09/02"),
                food("綠燈", "C", "2026/09/03")]
        out = build(rows, [], TODAY)
        self.assertEqual([a["title"] for a in out], ["B", "A"])  # newest first
        self.assertEqual([a["level"] for a in out], ["yellow", "red"])
        self.assertEqual(out[0]["kind"], "food")
        self.assertEqual(out[0]["body"], "內容 說明")

    def test_drops_old_alerts(self):
        out = build([food("紅燈", "old", "2024/09/30"), food("紅燈", "new", "2024/10/02")], [], TODAY)
        self.assertEqual([a["title"] for a in out], ["new"])

    def test_skips_bad_rows(self):
        rows = [food("紅燈", "no date", ""), food("藍燈", "odd light", "2026/09/01"),
                {"燈號": "紅燈"}, food("黃燈", "", "2026/09/01")]
        self.assertEqual(build(rows, [], TODAY), [])

    def test_cosmetic_fields_and_advice(self):
        rows = [{"燈號": "黃燈", "標題名稱": "<b>某產品</b>", "事件過程": "過程", "處置建議": "<p>停止使用</p>",
                 "更新日期": "2026/08/01"}]
        a = build([], rows, TODAY)[0]
        self.assertEqual((a["kind"], a["title"], a["body"], a["advice"]),
                         ("cosmetic", "某產品", "過程", "停止使用"))

    def test_ids_are_stable_and_unique(self):
        rows = [food("紅燈", "A", "2026/09/01"), food("紅燈", "A", "2026/09/01")]
        out = build(rows, [], TODAY)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], build(rows, [], TODAY)[0]["id"])

    def test_body_is_capped(self):
        out = build([food("紅燈", "A", "2026/09/01", body="字" * 5000)], [], TODAY)
        self.assertEqual(len(out[0]["body"]), 1500)


class SanityTest(unittest.TestCase):
    def alerts(self, food, cosmetic):
        return [{"kind": "food"}] * food + [{"kind": "cosmetic"}] * cosmetic

    def test_empty_kind_fails(self):
        with self.assertRaises(SystemExit):
            check_sane(self.alerts(0, 400), previous=None)
        with self.assertRaises(SystemExit):
            check_sane(self.alerts(20, 0), previous=None)

    def test_big_drop_fails(self):
        with self.assertRaises(SystemExit):
            check_sane(self.alerts(5, 100), previous=self.alerts(20, 450))

    def test_normal_change_passes(self):
        check_sane(self.alerts(19, 440), previous=self.alerts(20, 450))
        check_sane(self.alerts(1, 1), previous=None)


if __name__ == "__main__":
    unittest.main()
