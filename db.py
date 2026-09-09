# -*- coding: utf-8 -*-
"""
온다(ONDA) 일정관리 - DB 연결 설정

로컬 개발은 SQLite 파일(data/onda.db)을 그대로 쓰고, 나중에 실제 배포할 때는
DATABASE_URL 환경변수를 PostgreSQL 등으로 바꾸면 코드 수정 없이 그쪽으로 전환됩니다.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/onda.db")

# Render/Heroku류 호스팅은 DATABASE_URL을 "postgres://"로 주는 경우가 많은데,
# 최신 SQLAlchemy는 "postgresql://"만 인식하므로 여기서 보정해준다.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()

# 기존 DB에 나중에 추가된 컬럼들. (테이블, 컬럼명, "ALTER TABLE ... ADD COLUMN" 뒤에 붙일 타입/기본값)
# 새로 만드는 DB는 create_all이 이미 다 채워서 만들기 때문에 여기서는 아무 일도 안 하고,
# 기존에 쓰던 DB 파일에만 실제로 컬럼을 추가한다.
_ADDED_COLUMNS = [
    ("users", "kakao_access_token", "VARCHAR(255)"),
    ("users", "kakao_refresh_token", "VARCHAR(255)"),
    ("users", "kakao_token_expires_at", "DATETIME"),
    ("users", "kakao_connected_at", "DATETIME"),
    # 기존에 있던 일정들은 "이미 알림을 보낸 것"으로 처리해서, 기능을 새로 켰을 때
    # 지나간 일정들에 대해 한꺼번에 알림이 몰려 나가지 않도록 한다.
    ("events", "notified_day_before", "BOOLEAN DEFAULT 1"),
    ("events", "notified_hour_before", "BOOLEAN DEFAULT 1"),
]


def _run_migrations():
    if not DATABASE_URL.startswith("sqlite"):
        return  # 다른 DB(PostgreSQL 등)는 별도 마이그레이션 도구를 쓰는 게 안전하므로 건드리지 않음

    with engine.begin() as conn:
        for table, column, ddl_type in _ADDED_COLUMNS:
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def init_db():
    """테이블이 없으면 만들고, 기존 DB라면 새로 추가된 컬럼을 채워 넣습니다."""

    os.makedirs("data", exist_ok=True)

    import models  # noqa: F401  (모델을 Base에 등록시키기 위해 임포트)

    Base.metadata.create_all(engine)
    _run_migrations()


def get_session():
    return SessionLocal()
