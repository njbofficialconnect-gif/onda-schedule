# -*- coding: utf-8 -*-
"""온다(ONDA) 일정관리 - 엑셀 내보내기"""

import io

from openpyxl import Workbook
from openpyxl.styles import Font

from constants import CATEGORIES

HEADERS = [
    "종류", "제목", "시작일", "종료일", "시작시간", "종료시간", "장소",
    "지출(원)", "지출메모", "세부사항", "담당자",
    "연락처 회사명", "연락처 이름", "연락처 직책", "연락처 이메일",
]

COLUMN_WIDTHS = [12, 28, 12, 12, 10, 10, 20, 12, 18, 32, 10, 18, 12, 12, 24]


def build_events_workbook(events, users_by_id):
    wb = Workbook()
    ws = wb.active
    ws.title = "ONDA 일정"

    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for ev in events:
        assignee = users_by_id.get(ev.assignee_user_id)
        ws.append([
            CATEGORIES.get(ev.category, {}).get("label", ev.category),
            ev.title,
            ev.start_date.isoformat(),
            ev.end_date.isoformat(),
            ev.start_time.strftime("%H:%M") if ev.start_time else "",
            ev.end_time.strftime("%H:%M") if ev.end_time else "",
            ev.location or "",
            ev.expense_amount if ev.expense_amount is not None else "",
            ev.expense_note or "",
            ev.details or "",
            assignee.display_name if assignee else "",
            ev.contact_company or "",
            ev.contact_name or "",
            ev.contact_position or "",
            ev.contact_email or "",
        ])

    for idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[chr(64 + idx)].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def filtered_events(db, Event, start_date=None, end_date=None, categories=None):
    q = db.query(Event)
    if start_date:
        q = q.filter(Event.end_date >= start_date)
    if end_date:
        q = q.filter(Event.start_date <= end_date)
    if categories:
        q = q.filter(Event.category.in_(categories))
    return q.order_by(Event.start_date, Event.start_time).all()
