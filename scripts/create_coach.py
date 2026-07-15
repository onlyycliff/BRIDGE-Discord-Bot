"""One-shot script to create a coach account."""
import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
os.chdir(_root)

from dotenv import load_dotenv
load_dotenv(_root / ".env")

from werkzeug.security import generate_password_hash
from db.session import create_engine_from_url
from db.repository import create_coach


async def main():
    create_engine_from_url()
    email = "cliffordcoach@bridge.org"
    password = "clifford123"
    name = "Coach"

    pw_hash = generate_password_hash(password)
    coach = await create_coach(email=email, password_hash=pw_hash, name=name)
    print(f"Created coach: id={coach.id}, email={coach.email}, name={coach.name}")


if __name__ == "__main__":
    asyncio.run(main())
