import os
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
def database_url() -> str:
    url=os.getenv("DATABASE_URL")
    if not url: raise RuntimeError("DATABASE_URL environment variable is required")
    return url
engine=create_engine(database_url(),pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
def get_db() -> Generator[Session,None,None]:
    with SessionLocal() as session: yield session
