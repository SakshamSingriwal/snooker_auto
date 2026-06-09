from datetime import datetime
from backend.database import init_db, archive_month

init_db()
year = datetime.now().year
month = datetime.now().month
path = archive_month(year, month)
print(f"✅ Archived {year}-{month:02d} → {path}")