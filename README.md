# 🛡️ LayID CSV Preflight

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Website](https://img.shields.io/badge/Website-layid.online-indigo)](https://layid.online)
[![RFC-4180](https://img.shields.io/badge/Spec-RFC--4180-success)](https://www.rfc-editor.org/rfc/rfc4180)

> **Catch dirty byte-order marks (BOM), unescaped quotes, ragged rows, and delimiter drift before database ingestion.**

Stop 2 AM ETL pipeline crashes in Snowflake, BigQuery, Postgres, and Pandas caused by customer CSV exports.

---

## 🚀 Live Online Validator & Auto-Fix

Don't want to install anything locally? Try the free in-browser validator:
👉 **[https://layid.online](https://layid.online)**

- Instant RFC-4180 hygiene scoring (0 - 100%)
- Line-by-line anomaly inspector
- **1-Click Auto-Fix (VIP Pro)**: Automatically strip UTF-8 BOM (`\xef\xbb\xbf`), unify European semicolons to standard commas, pad ragged rows, and download a warehouse-ready dataset directly from the browser.

---

## 📦 Zero-Dependency Local CLI

For air-gapped security, CI/CD pipelines, and local developer workflows:

### Quickstart

```bash
# Clone the repository
git clone https://github.com/tuanthanh2005/csv-preflight.git
cd csv-preflight

# Run preflight validation against schema rules
python csv_preflight.py sample_data.csv --rules sample_rules.json
```

### Example Output

```json
{
  "status": "findings",
  "records_checked": 4,
  "findings": [
    {"record": 3, "column": "email", "rule": "REQUIRED"},
    {"record": 4, "column": "customer_id", "rule": "UNIQUE", "duplicates_record": 2}
  ]
}
```

---

## ⚡ What CSV Preflight Catches

1. **UTF-8 Byte-Order Mark (BOM):** Detects `\xEF\xBB\xBF` prepended by Microsoft Excel that causes column header corruption (e.g. `\ufeffcustomer_id`).
2. **Delimiter Drift:** Heuristic scoring for comma (`,`), semicolon (`;`), tab (`\t`), and pipe (`|`).
3. **Ragged Rows:** Identifies lines with column counts inconsistent with the header schema.
4. **Encoding Anomalies:** Flags Latin-1, Windows-1252, and broken UTF-8 byte sequences.

---

## 💎 VIP Pro Commercial Package

For automated batch repair, custom validation rule generation, and high-volume warehouse automation:
- **Price:** $20.00 USDC one-time
- **Payment Network:** Base (EVM)
- **Get VIP Pro:** [https://layid.online/#pricing](https://layid.online/#pricing)

---

## 📄 License

MIT License. Free for open-source and individual pipeline verification.
