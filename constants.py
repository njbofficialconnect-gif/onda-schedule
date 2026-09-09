# -*- coding: utf-8 -*-
"""일정 카테고리(종류) 정의. label은 화면에 보이는 이름, color는 캘린더에 쓰이는 색상."""

CATEGORIES = {
    "youtube": {"label": "유튜브 업로드", "color": "#e11d48"},
    "ceo": {"label": "박현기 대표", "color": "#2563eb"},
    "director": {"label": "변시원 전무이사", "color": "#7c3aed"},
    "vp": {"label": "박현우 부대표", "color": "#059669"},
    "event": {"label": "ONDA 행사", "color": "#d97706"},
    "meeting": {"label": "회의/미팅", "color": "#0891b2"},
    "contract": {"label": "계약서 작성", "color": "#dc2626"},
}

# 개인 일정 카테고리 -> 담당자로 지정될 계정의 username
PERSON_CATEGORY_USERNAME = {
    "ceo": "onda1",       # 박현기 대표
    "director": "onda3",  # 변시원 전무이사
    "vp": "onda2",        # 박현우 부대표
}

CATEGORY_ORDER = ["youtube", "ceo", "director", "vp", "event", "meeting", "contract"]
