# -*- coding: utf-8 -*-
"""
온다(ONDA) 일정관리 - 카카오톡 "나에게 보내기" 알림 유틸리티

박현기/변시원/박현우 3명이 각자 자신의 카카오 계정으로 한 번만 연동해두면,
그 사람 담당 일정의 하루전/1시간전 알림이 본인의 카카오톡 "나와의 채팅"으로 옵니다.

준비물 (README 참고):
  1) https://developers.kakao.com 에서 앱 생성
  2) [카카오 로그인] 활성화 + Redirect URI 등록 (KAKAO_REDIRECT_URI와 동일해야 함)
  3) [카카오 로그인 > 동의항목]에서 "카카오톡 메시지 전송" 동의항목 신청
  4) [앱 설정 > 팀원 관리]에 박현기/변시원/박현우 3명의 카카오 계정을 등록
     (앱을 아직 정식 심사에 안 올렸다면, 등록된 팀원만 로그인 연동이 가능합니다)
"""

import json
import os
from datetime import datetime, timedelta

import requests

KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5050")
KAKAO_REDIRECT_URI = os.environ.get("KAKAO_REDIRECT_URI", f"{APP_BASE_URL}/kakao/callback")

AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

# "나에게 보내기"에 필요한 동의항목. 카카오 로그인 동의항목에서 미리 신청해둬야 실제로 붙는다.
SCOPE = "talk_message"


def kakao_configured():
    return bool(KAKAO_REST_API_KEY)


def authorize_url(state=""):
    return (
        f"{AUTHORIZE_URL}?response_type=code&client_id={KAKAO_REST_API_KEY}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}&scope={SCOPE}&state={state}"
    )


def exchange_code(code):
    """인가 코드로 access_token/refresh_token을 받아옵니다."""

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": code,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token_value):
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_API_KEY,
            "refresh_token": refresh_token_value,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def send_memo_to_me(access_token, text):
    """카카오톡 "나에게 보내기"로 텍스트 메시지 하나를 보냅니다. (성공 여부, 응답본문) 반환."""

    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": APP_BASE_URL, "mobile_web_url": APP_BASE_URL},
        "button_title": "캘린더 열기",
    }
    resp = requests.post(
        MEMO_SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=10,
    )
    return resp.ok, resp.text


def get_valid_access_token(db, user):
    """user의 카카오 access_token을 반환합니다. 만료됐으면 자동으로 갱신해서 DB에 저장합니다.
    연동이 안 되어 있으면 None."""

    if not user.kakao_refresh_token:
        return None

    if user.kakao_token_expires_at and user.kakao_token_expires_at > datetime.utcnow() + timedelta(minutes=5):
        return user.kakao_access_token

    try:
        data = refresh_access_token(user.kakao_refresh_token)
    except Exception as e:
        print(f"[경고] {user.display_name}님 카카오 토큰 갱신 실패: {e}")
        return None

    user.kakao_access_token = data.get("access_token")
    if data.get("refresh_token"):
        user.kakao_refresh_token = data["refresh_token"]
    user.kakao_token_expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 21599))
    db.commit()

    return user.kakao_access_token
