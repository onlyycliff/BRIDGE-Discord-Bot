"""
One-time migration script — import old responses.xlsx data into PostgreSQL.

Usage:
    python scripts/migrate_from_excel.py [--xlsx path/to/responses.xlsx]

Requires DATABASE_URL to be set in the environment (or .env).

What it does:
  1. Reads the "Poll Metadata" sheet — creates Form + Question + Option rows.
  2. Reads the "Poll Responses" sheet — creates Response rows linked to
     the corresponding question/option by matching poll_id + choice text.
  3. Skips records that already exist in the database (idempotent by
     checking Form.id already present).
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
import pandas as pd

from db.session import create_engine_from_url, get_factory, dispose_engine
from db.models import Form, Question, Option, Response
from db.enums import FormStatus, QuestionType


load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / "bridge_bot" / ".env")


def _parse_args():
    parser = argparse.ArgumentParser(description="Import Excel poll data into PostgreSQL")
    parser.add_argument(
        "--xlsx",
        default=str(Path(__file__).resolve().parent.parent / "responses.xlsx"),
        help="Path to the responses.xlsx file (default: project root)",
    )
    return parser.parse_args()


async def migrate(xlsx_path: str) -> None:
    create_engine_from_url()
    factory = get_factory()

    if not Path(xlsx_path).exists():
        print(f"Excel file not found: {xlsx_path} — nothing to migrate.")
        return

    print(f"Reading {xlsx_path} ...")

    try:
        meta_df = pd.read_excel(xlsx_path, sheet_name="Poll Metadata")
    except ValueError:
        print("No 'Poll Metadata' sheet found — skipping form creation.")
        meta_df = pd.DataFrame()

    try:
        votes_df = pd.read_excel(xlsx_path, sheet_name="Poll Responses")
    except ValueError:
        print("No 'Poll Responses' sheet found — nothing to migrate.")
        return

    async with factory() as session:
        # ---- 1. Import Poll Metadata -> Form + Question + Options ----
        meta_count = 0
        for _, row in meta_df.iterrows():
            raw_pid = row.get("Poll_ID")
            if pd.isna(raw_pid):
                continue
            poll_id = int(raw_pid)

            existing = await session.get(Form, poll_id)
            if existing is not None:
                print(f"  Skipping poll {poll_id} — already exists")
                continue

            form = Form(
                id=poll_id,
                guild_id=0,
                channel_id=int(row.get("Channel_ID", 0)) if pd.notna(row.get("Channel_ID")) else 0,
                type="poll",
                title=str(row.get("Description", str(row.get("Question", "")))),
                created_by=0,
                status=FormStatus.active,
                anonymous=False,
            )
            session.add(form)
            await session.flush()

            q = Question(
                form_id=form.id,
                prompt=str(row.get("Question", "")),
                question_type=QuestionType.single_choice,
                order=0,
            )
            session.add(q)
            await session.flush()

            raw_opts = row.get("Options", "[]")
            try:
                options_list = json.loads(raw_opts) if isinstance(raw_opts, str) else []
            except (json.JSONDecodeError, TypeError):
                options_list = []

            for i, opt_text in enumerate(options_list):
                opt = Option(
                    question_id=q.id,
                    text=str(opt_text)[:500],
                    order=i,
                )
                session.add(opt)

            await session.flush()
            meta_count += 1
            print(f"  Created poll {poll_id}: {q.prompt[:50]}...")

        # ---- 2. Import Poll Responses -> Response rows ----
        vote_count = 0
        skip_count = 0
        for _, row in votes_df.iterrows():
            raw_pid = row.get("Poll_ID")
            if pd.isna(raw_pid):
                skip_count += 1
                continue
            poll_id = int(raw_pid)

            form = await session.get(Form, poll_id)
            if form is None:
                print(f"  Skipping vote for unknown poll {poll_id}")
                skip_count += 1
                continue

            # Get the single question for this form
            from sqlalchemy import select
            stmt = select(Question).where(Question.form_id == form.id).limit(1)
            q_result = await session.execute(stmt)
            question = q_result.scalar_one_or_none()
            if question is None:
                skip_count += 1
                continue

            # Find the matching option by text
            choice_text = str(row.get("Choice", "")).strip()
            opt_stmt = select(Option).where(
                Option.question_id == question.id,
                Option.text == choice_text,
            )
            opt_result = await session.execute(opt_stmt)
            option = opt_result.scalar_one_or_none()

            user_id_raw = row.get("User_ID")
            if pd.isna(user_id_raw):
                skip_count += 1
                continue

            resp = Response(
                question_id=question.id,
                user_id=int(user_id_raw),
                username=str(row.get("Username", ""))[:100],
                option_id=option.id if option else None,
                question_type=question.question_type,
            )
            session.add(resp)
            vote_count += 1

            if vote_count % 100 == 0:
                print(f"  Imported {vote_count} votes...")

        await session.commit()
        print("\nMigration complete:")
        print(f"  Polls created: {meta_count}")
        print(f"  Votes imported: {vote_count}")
        print(f"  Skipped: {skip_count}")

    await dispose_engine()


def main():
    args = _parse_args()
    asyncio.run(migrate(args.xlsx))


if __name__ == "__main__":
    main()
