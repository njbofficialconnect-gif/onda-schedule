# -*- coding: utf-8 -*-
"""온다(ONDA) 통합 일정관리 앱"""

import os
import secrets
from datetime import datetime, timedelta, date

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file

from db import init_db, get_session
from models import User, Event, EmailLog, ExportLog
from auth import hash_password, verify_password, current_user, login_required
from mailer import send_email, send_email_with_attachment, mail_configured
from constants import CATEGORIES, CATEGORY_ORDER, PERSON_CATEGORY_USERNAME
import kakao
from export import build_events_workbook, filtered_events
from reminders import start_reminder_scheduler

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

init_db()


# ---------- 공통 유틸 ----------

def parse_date(value, default=None):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None


def event_to_dict(ev, users_by_id):
    cat = CATEGORIES.get(ev.category, {"label": ev.category, "color": "#6b7280"})
    assignee = users_by_id.get(ev.assignee_user_id)
    created_by = users_by_id.get(ev.created_by_user_id)
    updated_by = users_by_id.get(ev.updated_by_user_id)

    return {
        "id": ev.id,
        "title": ev.title,
        "start": ev.start_date.isoformat(),
        # FullCalendar의 end는 배타적(exclusive)이라 하루 더해서 보내야 마지막 날까지 표시됨
        "end": (ev.end_date + timedelta(days=1)).isoformat(),
        "allDay": True,
        "color": cat["color"],
        "extendedProps": {
            "category": ev.category,
            "category_label": cat["label"],
            "start_date": ev.start_date.isoformat(),
            "end_date": ev.end_date.isoformat(),
            "start_time": ev.start_time.strftime("%H:%M") if ev.start_time else "",
            "end_time": ev.end_time.strftime("%H:%M") if ev.end_time else "",
            "location": ev.location or "",
            "expense_amount": ev.expense_amount,
            "expense_note": ev.expense_note or "",
            "details": ev.details or "",
            "assignee_user_id": ev.assignee_user_id,
            "assignee_name": assignee.display_name if assignee else "",
            "contact_company": ev.contact_company or "",
            "contact_name": ev.contact_name or "",
            "contact_position": ev.contact_position or "",
            "contact_email": ev.contact_email or "",
            "created_by_name": created_by.display_name if created_by else "",
            "updated_by_name": updated_by.display_name if updated_by else "",
            "updated_at": ev.updated_at.strftime("%Y-%m-%d %H:%M") if ev.updated_at else "",
        },
    }


# ---------- 로그인 ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("calendar_page"))
        return render_template("login.html", error=None)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    db = get_session()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user or not verify_password(password, user.password_hash):
            return render_template("login.html", error="아이디 또는 비밀번호가 올바르지 않습니다.")

        user.last_login_at = datetime.utcnow()
        db.commit()

        session["user_id"] = user.id
        session["display_name"] = user.display_name
    finally:
        db.close()

    return redirect(request.args.get("next") or url_for("calendar_page"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _account_page(error=None, done=False):
    user = current_user()
    return render_template(
        "change_password.html",
        error=error,
        done=done,
        kakao_configured=kakao.kakao_configured(),
        kakao_connected=bool(user.kakao_refresh_token),
    )


@app.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    user = current_user()
    if request.method == "GET":
        return _account_page()

    current_pw = request.form.get("current_password") or ""
    new_pw = request.form.get("new_password") or ""
    new_pw2 = request.form.get("new_password2") or ""

    if not verify_password(current_pw, user.password_hash):
        return _account_page(error="현재 비밀번호가 올바르지 않습니다.")
    if len(new_pw) < 4:
        return _account_page(error="새 비밀번호는 4자 이상이어야 합니다.")
    if new_pw != new_pw2:
        return _account_page(error="새 비밀번호가 서로 일치하지 않습니다.")

    db = get_session()
    try:
        db_user = db.query(User).get(user.id)
        db_user.password_hash = hash_password(new_pw)
        db.commit()
    finally:
        db.close()

    return _account_page(done=True)


# ---------- 카카오톡 알림 연동 ----------

@app.route("/kakao/connect")
@login_required
def kakao_connect():
    if not kakao.kakao_configured():
        return _account_page(error="카카오 연동이 아직 설정되지 않았습니다 (.env의 KAKAO_REST_API_KEY 확인).")

    state = secrets.token_urlsafe(16)
    session["kakao_oauth_state"] = state
    return redirect(kakao.authorize_url(state=state))


@app.route("/kakao/callback")
@login_required
def kakao_callback():
    error = request.args.get("error")
    if error:
        return _account_page(error=f"카카오 연동이 취소되었습니다 ({error}).")

    state = request.args.get("state", "")
    if not state or state != session.pop("kakao_oauth_state", None):
        return _account_page(error="연동 요청이 유효하지 않습니다. 다시 시도해주세요.")

    code = request.args.get("code")
    if not code:
        return _account_page(error="카카오 인가 코드가 없습니다.")

    try:
        token_data = kakao.exchange_code(code)
    except Exception as e:
        return _account_page(error=f"카카오 토큰 발급에 실패했습니다: {e}")

    user = current_user()
    db = get_session()
    try:
        db_user = db.query(User).get(user.id)
        db_user.kakao_access_token = token_data.get("access_token")
        db_user.kakao_refresh_token = token_data.get("refresh_token")
        db_user.kakao_token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get("expires_in", 21599)
        )
        db_user.kakao_connected_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

    return _account_page(done=True)


@app.route("/kakao/disconnect", methods=["POST"])
@login_required
def kakao_disconnect():
    user = current_user()
    db = get_session()
    try:
        db_user = db.query(User).get(user.id)
        db_user.kakao_access_token = None
        db_user.kakao_refresh_token = None
        db_user.kakao_token_expires_at = None
        db_user.kakao_connected_at = None
        db.commit()
    finally:
        db.close()
    return redirect(url_for("change_password"))


# ---------- 캘린더 페이지 ----------

@app.route("/")
@login_required
def calendar_page():
    user = current_user()
    db = get_session()
    try:
        all_users = db.query(User).all()
        people = [{"id": u.id, "name": u.display_name, "username": u.username} for u in all_users]
    finally:
        db.close()

    categories = [{"key": k, **CATEGORIES[k]} for k in CATEGORY_ORDER]

    return render_template(
        "calendar.html",
        user=user,
        categories=categories,
        people=people,
        mail_configured=mail_configured(),
    )


# ---------- 이벤트 API ----------

@app.route("/api/events", methods=["GET"])
@login_required
def api_events_list():
    db = get_session()
    try:
        events = db.query(Event).all()
        users_by_id = {u.id: u for u in db.query(User).all()}
        return jsonify([event_to_dict(e, users_by_id) for e in events])
    finally:
        db.close()


@app.route("/api/events", methods=["POST"])
@login_required
def api_events_create():
    data = request.get_json(force=True) or {}
    user = current_user()

    category = data.get("category")
    if category not in CATEGORIES:
        return jsonify({"error": "invalid_category"}), 400

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title_required"}), 400

    start_date = parse_date(data.get("start_date"))
    end_date = parse_date(data.get("end_date"), default=start_date)
    if not start_date:
        return jsonify({"error": "start_date_required"}), 400
    if end_date < start_date:
        end_date = start_date

    assignee_user_id = data.get("assignee_user_id")
    db = get_session()
    try:
        if not assignee_user_id and category in PERSON_CATEGORY_USERNAME:
            person = db.query(User).filter_by(username=PERSON_CATEGORY_USERNAME[category]).first()
            assignee_user_id = person.id if person else None

        ev = Event(
            category=category,
            title=title,
            start_date=start_date,
            end_date=end_date,
            start_time=parse_time(data.get("start_time")),
            end_time=parse_time(data.get("end_time")),
            location=(data.get("location") or "").strip(),
            expense_amount=data.get("expense_amount") or None,
            expense_note=(data.get("expense_note") or "").strip(),
            details=(data.get("details") or "").strip(),
            assignee_user_id=assignee_user_id,
            contact_company=(data.get("contact_company") or "").strip(),
            contact_name=(data.get("contact_name") or "").strip(),
            contact_position=(data.get("contact_position") or "").strip(),
            contact_email=(data.get("contact_email") or "").strip(),
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        db.add(ev)
        db.commit()

        users_by_id = {u.id: u for u in db.query(User).all()}
        return jsonify(event_to_dict(ev, users_by_id)), 201
    finally:
        db.close()


@app.route("/api/events/<int:event_id>", methods=["PUT"])
@login_required
def api_events_update(event_id):
    data = request.get_json(force=True) or {}
    user = current_user()

    db = get_session()
    try:
        ev = db.query(Event).get(event_id)
        if not ev:
            return jsonify({"error": "not_found"}), 404

        if "category" in data:
            if data["category"] not in CATEGORIES:
                return jsonify({"error": "invalid_category"}), 400
            ev.category = data["category"]

        if "title" in data:
            title = (data.get("title") or "").strip()
            if not title:
                return jsonify({"error": "title_required"}), 400
            ev.title = title

        if "start_date" in data:
            start_date = parse_date(data.get("start_date"))
            if start_date:
                ev.start_date = start_date

        if "end_date" in data:
            end_date = parse_date(data.get("end_date"), default=ev.start_date)
            ev.end_date = end_date if end_date >= ev.start_date else ev.start_date

        if "start_time" in data:
            ev.start_time = parse_time(data.get("start_time"))
        if "end_time" in data:
            ev.end_time = parse_time(data.get("end_time"))
        if "location" in data:
            ev.location = (data.get("location") or "").strip()
        if "expense_amount" in data:
            ev.expense_amount = data.get("expense_amount") or None
        if "expense_note" in data:
            ev.expense_note = (data.get("expense_note") or "").strip()
        if "details" in data:
            ev.details = (data.get("details") or "").strip()
        if "assignee_user_id" in data:
            ev.assignee_user_id = data.get("assignee_user_id") or None
        if "contact_company" in data:
            ev.contact_company = (data.get("contact_company") or "").strip()
        if "contact_name" in data:
            ev.contact_name = (data.get("contact_name") or "").strip()
        if "contact_position" in data:
            ev.contact_position = (data.get("contact_position") or "").strip()
        if "contact_email" in data:
            ev.contact_email = (data.get("contact_email") or "").strip()

        ev.updated_by_user_id = user.id
        ev.updated_at = datetime.utcnow()

        db.commit()

        users_by_id = {u.id: u for u in db.query(User).all()}
        return jsonify(event_to_dict(ev, users_by_id))
    finally:
        db.close()


@app.route("/api/events/<int:event_id>", methods=["DELETE"])
@login_required
def api_events_delete(event_id):
    db = get_session()
    try:
        ev = db.query(Event).get(event_id)
        if not ev:
            return jsonify({"error": "not_found"}), 404
        db.query(EmailLog).filter_by(event_id=event_id).delete()
        db.delete(ev)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ---------- 이메일 발송 ----------

@app.route("/api/events/<int:event_id>/send-email", methods=["POST"])
@login_required
def api_send_email(event_id):
    data = request.get_json(force=True) or {}
    user = current_user()

    to_email = (data.get("to_email") or "").strip()
    subject = (data.get("subject") or "").strip()
    body = data.get("body") or ""

    if not to_email:
        return jsonify({"error": "to_email_required"}), 400
    if not subject:
        return jsonify({"error": "subject_required"}), 400

    db = get_session()
    try:
        ev = db.query(Event).get(event_id)
        if not ev:
            return jsonify({"error": "not_found"}), 404

        ok, err = send_email(to_email, subject, body, sender_display_name=user.display_name)

        log = EmailLog(
            event_id=event_id,
            to_email=to_email,
            subject=subject,
            body=body,
            sent_by_user_id=user.id,
            status="sent" if ok else "failed",
            error_message=err or "",
        )
        db.add(log)
        db.commit()

        if not ok:
            return jsonify({"error": "send_failed", "message": err}), 502

        return jsonify({"ok": True})
    finally:
        db.close()


@app.route("/api/events/<int:event_id>/email-logs", methods=["GET"])
@login_required
def api_email_logs(event_id):
    db = get_session()
    try:
        logs = (
            db.query(EmailLog)
            .filter_by(event_id=event_id)
            .order_by(EmailLog.sent_at.desc())
            .all()
        )
        users_by_id = {u.id: u for u in db.query(User).all()}
        return jsonify([
            {
                "id": lg.id,
                "to_email": lg.to_email,
                "subject": lg.subject,
                "body": lg.body,
                "status": lg.status,
                "error_message": lg.error_message,
                "sent_at": lg.sent_at.strftime("%Y-%m-%d %H:%M"),
                "sent_by_name": users_by_id[lg.sent_by_user_id].display_name
                if lg.sent_by_user_id in users_by_id else "",
            }
            for lg in logs
        ])
    finally:
        db.close()


# ---------- 엑셀 내보내기 ----------

@app.route("/api/export/excel", methods=["GET"])
@login_required
def api_export_excel():
    start = parse_date(request.args.get("start"))
    end = parse_date(request.args.get("end"))
    categories = request.args.getlist("category") or None

    db = get_session()
    try:
        events = filtered_events(db, Event, start, end, categories)
        users_by_id = {u.id: u for u in db.query(User).all()}
        buf = build_events_workbook(events, users_by_id)
    finally:
        db.close()

    filename = f"ONDA_일정_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/export/excel/email", methods=["POST"])
@login_required
def api_export_excel_email():
    data = request.get_json(force=True) or {}
    user = current_user()

    to_email = (data.get("to_email") or "").strip()
    if not to_email:
        return jsonify({"error": "to_email_required"}), 400

    start = parse_date(data.get("start"))
    end = parse_date(data.get("end"))
    categories = data.get("categories") or None

    db = get_session()
    try:
        events = filtered_events(db, Event, start, end, categories)
        users_by_id = {u.id: u for u in db.query(User).all()}
        buf = build_events_workbook(events, users_by_id)

        filename = f"ONDA_일정_{datetime.now().strftime('%Y%m%d')}.xlsx"
        subject = f"[ONDA] 일정 엑셀 ({datetime.now().strftime('%Y-%m-%d')})"
        body = (
            f"{user.display_name}님이 ONDA 통합 일정관리에서 보낸 엑셀입니다.\n\n"
            f"첨부된 파일을 확인해주세요."
        )

        ok, err = send_email_with_attachment(
            to_email, subject, body, filename, buf.getvalue(),
            sender_display_name=user.display_name,
        )

        log = ExportLog(
            to_email=to_email,
            subject=subject,
            filename=filename,
            sent_by_user_id=user.id,
            status="sent" if ok else "failed",
            error_message=err or "",
        )
        db.add(log)
        db.commit()

        if not ok:
            return jsonify({"error": "send_failed", "message": err}), 502

        return jsonify({"ok": True})
    finally:
        db.close()


# "python app.py"로 켜면 디버그 모드가 코드 변경 감시용 부모 프로세스를 하나 더 띄우는데,
# 감시용 부모 프로세스에는 WERKZEUG_RUN_MAIN이 없고 실제 요청을 처리하는 자식 프로세스에는
# "true"로 설정되어 있으므로 그걸로 구분해서, 알림 스케줄러가 두 번 뜨지 않게 한다.
_is_reloader_watcher = __name__ == "__main__" and os.environ.get("WERKZEUG_RUN_MAIN") != "true"

if not _is_reloader_watcher:
    start_reminder_scheduler()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
