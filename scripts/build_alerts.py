"""Build a small Taiwan FDA safety-alert feed for the Kenji app.

Downloads TFDA "消費紅綠燈" datasets (food 9641 → export 62, cosmetics 11511 →
export 131), keeps red/yellow alerts from the last two years and writes
alerts.json. Usage: python3 scripts/build_alerts.py [out_path]
"""
import hashlib
import html
import io
import json
import re
import sys
import urllib.request
import zipfile
from datetime import date, datetime, timezone

BASE = "https://data.fda.gov.tw/data/opendata/export/{}/json"
FOOD, COSMETICS = 62, 131
LEVELS = {"紅燈": "red", "黃燈": "yellow"}
BODY_MAX = 1500


def fetch(export_id):
    req = urllib.request.Request(BASE.format(export_id), headers={"User-Agent": "kenji-alerts/1.0"})
    data = urllib.request.urlopen(req, timeout=300).read()
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            data = z.read(z.namelist()[0])
    return json.loads(data.decode("utf-8-sig"))


def strip_html(s):
    if not isinstance(s, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", s)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_date(s):
    try:
        return datetime.strptime((s or "").strip(), "%Y/%m/%d").date()
    except ValueError:
        return None


def build(food_rows, cosmetic_rows, today, days=730):
    out = {}
    for kind, rows in (("food", food_rows), ("cosmetic", cosmetic_rows)):
        for r in rows:
            level = LEVELS.get(r.get("燈號"))
            day = parse_date(r.get("更新日期"))
            title = strip_html(r.get("標題名稱"))
            if not level or not day or not title or (today - day).days > days:
                continue
            ident = hashlib.sha1(f"{kind}|{title}|{day.isoformat()}".encode()).hexdigest()[:16]
            out[ident] = {
                "id": ident,
                "kind": kind,
                "level": level,
                "title": title,
                "body": strip_html(r.get("內容") or r.get("事件過程"))[:BODY_MAX],
                "advice": strip_html(r.get("處置建議")),
                "date": day.isoformat(),
            }
    return sorted(out.values(), key=lambda a: (a["date"], a["id"]), reverse=True)


def check_sane(alerts, previous):
    """Fail loudly (non-zero exit) instead of publishing a broken feed,
    e.g. after TFDA renames a field or an export comes back empty."""
    for kind in ("food", "cosmetic"):
        if not any(a["kind"] == kind for a in alerts):
            sys.exit(f"refusing to publish: no {kind} alerts (TFDA data changed?)")
    if previous and len(alerts) < len(previous) / 2:
        sys.exit(f"refusing to publish: {len(alerts)} alerts vs {len(previous)} before")


def main(out_path="alerts.json"):
    alerts = build(fetch(FOOD), fetch(COSMETICS), date.today())
    try:
        with open(out_path, encoding="utf-8") as f:
            previous = json.load(f).get("alerts")
    except (FileNotFoundError, ValueError):
        previous = None
    check_sane(alerts, previous)
    # Always rewrite so generatedAt says how fresh the data is (one small
    # commit a day also keeps the scheduled workflow from being auto-disabled).
    feed = {"generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "alerts": alerts}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(alerts)} alerts")


if __name__ == "__main__":
    main(*sys.argv[1:])
