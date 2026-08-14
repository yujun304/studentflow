import argparse
import asyncio
from datetime import date

from sqlalchemy import select

from app.core.database import SessionFactory
from app.core.security import hash_password
from app.models.entities import Role, Term, User


async def create_teacher(email: str, name: str, password: str) -> None:
    async with SessionFactory() as db:
        term = await db.scalar(select(Term).where(Term.is_current.is_(True)))
        if not term:
            year = date.today().year
            term = Term(
                name=f"{year}학년도 학생회",
                starts_on=date(year, 1, 1),
                ends_on=date(year, 12, 31),
                is_current=True,
            )
            db.add(term)
            await db.flush()
        existing = await db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            raise SystemExit("이미 존재하는 이메일입니다.")
        db.add(
            User(
                email=email.lower(),
                name=name,
                password_hash=hash_password(password),
                role=Role.TEACHER,
                term_id=term.id,
            )
        )
        await db.commit()
        print(f"Created teacher: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(create_teacher(args.email, args.name, args.password))
