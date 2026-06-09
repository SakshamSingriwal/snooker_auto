# 🎱 Snooker Cafe Management System

## Features
- Multi-table support: Snooker (×5), Pool, Ludo, Carrom, Chess, Seating
- Per-table: configurable rate/min + minimum minutes billing
- Food/drinks menu with category support (food, drink, hookah)
- Customer ordering via QR code (mobile browser, no app install)
- Automatic billing: table time + food/drink orders combined
- Admin dashboard: live sessions, orders queue, sales reports
- Monthly data archiving to separate DB file

## Quick Start
```bash
pip install -r requirements.txt
python run.py
```
- Admin dashboard: http://localhost:8501 (password: admin123)
- API docs: http://localhost:8000/docs

## Generate QR Codes
```bash
python generate_qr.py
```
Prints and saves QR PNGs to `qr_codes/`. Print and stick on tables.

## Monthly Archive
```bash
python archive_monthly.py
```
Copies current DB to `data/archive_YYYY_MM.db` and removes closed records.