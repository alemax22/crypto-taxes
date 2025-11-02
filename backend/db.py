#!/usr/bin/env python3
"""
Database setup (SQLAlchemy 2.0)
Creates engine, session factory, and declarative base bound to DATABASE_URL.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = os.getenv(
	"DATABASE_URL",
	"postgresql+psycopg2://cryptotaxes:cryptotaxes@localhost:5432/cryptotaxes",
)

SCHEMA_NAME = "cryptofinance"


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db() -> None:
	"""Create all database tables for models already imported in the process."""
	Base.metadata.create_all(bind=engine)


