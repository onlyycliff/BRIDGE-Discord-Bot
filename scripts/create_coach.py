"""One-shot script to create a coach account.

Usage:
    python scripts/create_coach.py --email coach@bridge.org --password s3cret --name "Coach Name"

Both --email and --password are required. The script will fail loudly
if either is missing — no hardcoded fallbacks.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
os.chdir(_root)

from dotenv import load_dotenv
load_dotenv(_root / ".env")

from werkzeug.security import generate_password_hash
from db.session import create_engine_from_url
from db.repository import create_coach


async def main():
    parser = argparse.ArgumentParser(description="Create a coach account")
    parser.add_argument("--email", required=True, help="Coach email address")
    parser.add_argument("--password", required=True, help="Coach password (plain text, will be hashed)")
    parser.add_argument("--name", default="Coach", help="Coach display name")
    args = parser.parse_args()

    create_engine_from_url()

    pw_hash = generate_password_hash(args.password)
    coach = await create_coach(email=args.email, password_hash=pw_hash, name=args.name)
    print(f"Created coach: id={coach.id}, email={coach.email}, name={coach.name}")


if __name__ == "__main__":
    asyncio.run(main())
