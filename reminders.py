# -*- coding: utf-8 -*-
"""온다(ONDA) 일정관리 - 하루전/1시간전 카카오톡 알림 스케줄러"""

import threading
from datetime import datetime, timedelta, time as dtime

from apscheduler.schedulers.background import BackgroundScheduler

from db import get_session
from models import Event, User
from constants import CATEGORIES
import kakao

DEFAULT_START_TIME = dtime(9, 0)  # 시작 시간을 안 정한 일정은 오전 9시 기준으로 알림 계산

_lock = threading.Lock()


def _build_message(ev, offset_label):
    cat = CATEGORIES.get(ev.category, {"label": ev.category})
    t = ev.start_time or DEFAULT_START_TIME
    lines = [
        f"[ONDA 일정 알림] {offset_label}",
        f"{cat['label']} · {ev.title}",
        f"{ev.start_date.strftime('%m/%d')} {t.strftime('%H:%M')}",
    ]
    if ev.location:
        lines.append(f"장소: {ev.location}")
    return "\n".join(lines)


def _targets_for_event(ev, users_by_id, all_users):
    if ev.assignee_user_id and ev.assignee_user_id in users_by_id:
        return [users_by_id[ev.assignee_user_id]]
    return all_users


def _notify_users(db, ev, users, offset_label):
    text = _build_message(ev, offset_label)
    for user in users:
        token = kakao.get_valid_access_token(db, user)
        if not token:
            continue  # 이 사람은 아직 카카오 연동을 안 했으면 조용히 건너뜀
        ok, resp = kakao.send_memo_to_me(token, text)
        if not ok:
            print(f"[경고] {user.display_name}님 카카오 알림 발송 실패: {resp}")


def check_and_send_reminders():
    if not _lock.acquire(blocking=False):
        return  # 이전 작업이 아직 실행 중이면 건너뜀
    try:
        if not kakao.kakao_configured():
            return

        db = get_session()
        try:
            now = datetime.now()
            all_users = db.query(User).all()
            users_by_id = {u.id: u for u in all_users}

            events = (
                db.query(Event)
                .filter(
                    (Event.notified_day_before == False) | (Event.notified_hour_before == False)  # noqa: E712
                )
                .all()
            )

            for ev in events:
                start_dt = datetime.combine(ev.start_date, ev.start_time or DEFAULT_START_TIME)

                if now >= start_dt:
                    # 이미 시작된(지나간) 일정은 더 이상 알림 대상이 아님 -> 조용히 완료 처리
                    ev.notified_day_before = True
                    ev.notified_hour_before = True
                    db.commit()
                    continue

                due_day_before = start_dt - timedelta(hours=24)
                due_hour_before = start_dt - timedelta(hours=1)
                targets = _targets_for_event(ev, users_by_id, all_users)

                if not ev.notified_day_before and now >= due_day_before:
                    _notify_users(db, ev, targets, "하루 전")
                    ev.notified_day_before = True
                    db.commit()

                if not ev.notified_hour_before and now >= due_hour_before:
                    _notify_users(db, ev, targets, "1시간 전")
                    ev.notified_hour_before = True
                    db.commit()
        finally:
            db.close()
    finally:
        _lock.release()


def start_reminder_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(check_and_send_reminders, "interval", minutes=5, id="kakao_reminders")
    scheduler.start()
    print("[안내] 5분마다 카카오톡 알림 대상 일정을 확인합니다.")
    return scheduler
