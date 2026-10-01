# kenji-alerts

Public safety-alert feed for the Kenji app. A GitHub Action runs daily, downloads the Taiwan FDA "消費紅綠燈" open datasets (food and cosmetics) from [data.fda.gov.tw](https://data.fda.gov.tw), keeps red and yellow alerts from the last two years, and publishes them as [`alerts.json`](alerts.json).

Data source: 衛生福利部食品藥物管理署 (Taiwan FDA) open data, published under the Taiwan Government Open Data License. This repository contains only that public data and the script that filters it.

Run locally: `python3 -m unittest discover -s tests && python3 scripts/build_alerts.py alerts.json`
