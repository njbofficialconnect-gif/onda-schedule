# -*- coding: utf-8 -*-
"""
온다(ONDA) 일정관리 - DB 모델

User: 로그인 계정 (박현기 / 변시원 / 박현우, 아이디+비밀번호)
Event: 캘린더에 표시되는 일정 하나. 유튜브 업로드, 3인의 개인 일정, 행사, 회의, 계약서 작성일 등
       모든 종류를 category 값으로 구분해서 같은 표에 담는다.
EmailLog: Event에 연결된 담당자에게 보낸 이메일 발송 기록 (누가 언제 무엇을 보냈는지 3명 모두 확인 가능)
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Date, Time, DateTime, Boolean, ForeignKey,
)

from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(50), nullable=False)
    position = Column(String(50), default="")  # 대표 / 전무이사 / 부대표
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # 카카오톡 "나에게 보내기" 알림용 (본인이 직접 연동해야 채워짐)
    kakao_access_token = Column(String(255), nullable=True)
    kakao_refresh_token = Column(String(255), nullable=True)
    kakao_token_expires_at = Column(DateTime, nullable=True)
    kakao_connected_at = Column(DateTime, nullable=True)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    category = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)  # 기간(inclusive). 하루짜리면 start_date와 동일
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)

    location = Column(String(200), default="")
    expense_amount = Column(Integer, nullable=True)  # 원 단위
    expense_note = Column(String(200), default="")
    details = Column(Text, default="")

    # 담당 개인 일정(대표/전무이사/부대표)일 때 어떤 계정 소유인지
    assignee_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 세부내용에 등록하는 상대방(거래처/게스트 등) 개인정보
    contact_company = Column(String(200), default="")
    contact_name = Column(String(50), default="")
    contact_position = Column(String(50), default="")
    contact_email = Column(String(200), default="")

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 카카오톡 하루전/1시간전 알림을 이미 보냈는지 (중복 발송 방지)
    notified_day_before = Column(Boolean, default=False)
    notified_hour_before = Column(Boolean, default=False)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    to_email = Column(String(200), nullable=False)
    subject = Column(String(300), default="")
    body = Column(Text, default="")
    sent_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="sent")  # sent / failed
    error_message = Column(String(500), default="")


class ExportLog(Base):
    """엑셀 내보내기를 이메일로 보낸 기록 (특정 일정에 종속되지 않아 EmailLog와 분리)"""

    __tablename__ = "export_logs"

    id = Column(Integer, primary_key=True)
    to_email = Column(String(200), nullable=False)
    subject = Column(String(300), default="")
    filename = Column(String(200), default="")
    sent_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="sent")
    error_message = Column(String(500), default="")
