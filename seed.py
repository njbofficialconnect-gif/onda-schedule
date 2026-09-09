# -*- coding: utf-8 -*-
"""
초기 세팅 스크립트

1) 박현기(대표) / 변시원(전무이사) / 박현우(부대표) 3명의 로그인 계정을 만듭니다.
   이미 있으면 건너뜁니다. 새로 만든 계정의 임시 비밀번호는 이 창에 한 번만 출력되니
   꼭 적어두고, 처음 로그인 후 [비밀번호 변경] 메뉴에서 바꿔주세요.

2) 기존에 정리해두신 "온다_통합일정표.xlsx"(2026.09~11 유튜브 업로드 / 미팅 / 행사 일정)를
   초기 데이터로 캘린더에 넣어줍니다. 이미 들어가 있으면 중복으로 넣지 않습니다.

사용법:
    python seed.py
"""

import secrets
import string
from datetime import date

from db import init_db, get_session
from models import User, Event
from auth import hash_password

PEOPLE = [
    {"username": "hyungi", "display_name": "박현기", "position": "대표"},
    {"username": "siwon", "display_name": "변시원", "position": "전무이사"},
    {"username": "hyunwoo", "display_name": "박현우", "position": "부대표"},
]

# (category, title, start_date, end_date) - 온다_통합일정표.xlsx 2026.09~11 기준
SEED_EVENTS = [
    ("youtube", "라켓원정대 도쿄 1편", date(2026, 9, 5), date(2026, 9, 5)),
    ("meeting", "고흥 테니스협회 회의", date(2026, 9, 9), date(2026, 9, 9)),
    ("youtube", "라켓원정대 도쿄 2편", date(2026, 9, 12), date(2026, 9, 12)),
    ("meeting", "순천시청 문화관광 사업부 미팅", date(2026, 9, 14), date(2026, 9, 14)),
    ("meeting", "크리에이터 미팅", date(2026, 9, 18), date(2026, 9, 18)),
    ("event", "순천만국가정원배 전국대회 주관", date(2026, 9, 19), date(2026, 9, 20)),
    ("event", "필리핀 일정(세부 원정)", date(2026, 9, 22), date(2026, 9, 27)),
    ("youtube", "유명인사 초청 홍보영상", date(2026, 9, 26), date(2026, 9, 26)),
    ("youtube", "라켓원정대 필리핀 1편", date(2026, 10, 3), date(2026, 10, 3)),
    ("event", "타쿠야 내한 일정", date(2026, 10, 9), date(2026, 10, 11)),
    ("youtube", "라켓원정대 필리핀 2편", date(2026, 10, 10), date(2026, 10, 10)),
    ("youtube", "유명인사 초청이벤트 1편", date(2026, 10, 17), date(2026, 10, 17)),
    ("youtube", "유명인사 초청이벤트 2편(On Court)", date(2026, 10, 24), date(2026, 10, 24)),
    ("event", "일본 루이 내한 일정", date(2026, 10, 24), date(2026, 10, 25)),
    ("youtube", "라켓원정대 필리핀 3편", date(2026, 10, 31), date(2026, 10, 31)),
    ("youtube", "라켓원정대 필리핀 4편", date(2026, 11, 7), date(2026, 11, 7)),
]


def random_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def seed_users(db):
    created = []
    for p in PEOPLE:
        existing = db.query(User).filter_by(username=p["username"]).first()
        if existing:
            continue
        pw = random_password()
        user = User(
            username=p["username"],
            password_hash=hash_password(pw),
            display_name=p["display_name"],
            position=p["position"],
        )
        db.add(user)
        created.append((p["username"], pw))
    db.commit()
    return created


def seed_events(db, admin_user_id):
    added = 0
    for category, title, start_d, end_d in SEED_EVENTS:
        exists = (
            db.query(Event)
            .filter_by(title=title, start_date=start_d)
            .first()
        )
        if exists:
            continue
        db.add(
            Event(
                category=category,
                title=title,
                start_date=start_d,
                end_date=end_d,
                created_by_user_id=admin_user_id,
                updated_by_user_id=admin_user_id,
            )
        )
        added += 1
    db.commit()
    return added


def main():
    init_db()
    db = get_session()
    try:
        created_users = seed_users(db)

        # 이벤트를 만든 사람으로 남길 기준 계정 (없으면 첫 번째 계정)
        any_user = db.query(User).first()
        added_events = seed_events(db, any_user.id if any_user else None)

        print("=" * 50)
        if created_users:
            print("새로 생성된 로그인 계정 (꼭 적어두고 로그인 후 비밀번호를 바꾸세요):")
            for username, pw in created_users:
                print(f"  - 아이디: {username}  /  임시 비밀번호: {pw}")
        else:
            print("이미 계정이 모두 존재합니다. 새로 만든 계정은 없습니다.")

        print(f"초기 일정 {added_events}건을 캘린더에 추가했습니다.")
        print("=" * 50)
    finally:
        db.close()


if __name__ == "__main__":
    main()
