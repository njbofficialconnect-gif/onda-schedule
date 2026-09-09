# -*- coding: utf-8 -*-
"""온다(ONDA) 일정관리 - 아이디/비밀번호 로그인 유틸리티"""

from functools import wraps

from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_session
from models import User


def hash_password(raw_password):
    return generate_password_hash(raw_password)


def verify_password(raw_password, password_hash):
    return check_password_hash(password_hash, raw_password)


def current_user():
    """세션에 로그인된 사용자를 User 객체로 반환합니다. 없으면 None."""

    user_id = session.get("user_id")
    if not user_id:
        return None

    db = get_session()
    try:
        return db.query(User).get(user_id)
    finally:
        db.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "login_required"}), 401
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped
