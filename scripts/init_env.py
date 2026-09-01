\
from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"


def main() -> None:
    if TARGET.exists():
        raise SystemExit(".env already exists; refusing to overwrite it.")

    text = EXAMPLE.read_text(encoding="utf-8")
    password = secrets.token_urlsafe(24)
    text = text.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={password}\n", 1)
    TARGET.write_text(text, encoding="utf-8")

    print("Created local .env with a generated database password.")
    print("The .env file is ignored by Git and Docker build context.")


if __name__ == "__main__":
    main()
