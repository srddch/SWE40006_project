from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
target = root / ".env"
if target.exists():
    print(".env already exists; existing settings were kept.")
    raise SystemExit(0)
target.write_text(
    "APP_ENV=development\n"
    f"SECRET_KEY={secrets.token_hex(32)}\n"
    "DATABASE_URL=sqlite:///taskmanager.db\n"
    "DB_NAME=taskmanager\nDB_USER=taskmanager\n"
    f"DB_PASSWORD={secrets.token_hex(16)}\n"
    f"DB_ROOT_PASSWORD={secrets.token_hex(16)}\n"
    "APP_PORT=8000\n",
    encoding="utf-8",
)
print("Created private .env settings. Do not commit this file.")
