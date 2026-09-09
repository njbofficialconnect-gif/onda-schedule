(function () {
  "use strict";

  const catByKey = {};
  ONDA.categories.forEach((c) => (catByKey[c.key] = c));

  const els = {
    calendar: document.getElementById("calendar"),
    modal: document.getElementById("event-modal"),
    modalTitle: document.getElementById("modal-title-text"),
    form: document.getElementById("event-form"),
    id: document.getElementById("f-id"),
    category: document.getElementById("f-category"),
    assignee: document.getElementById("f-assignee"),
    title: document.getElementById("f-title"),
    startDate: document.getElementById("f-start-date"),
    endDate: document.getElementById("f-end-date"),
    startTime: document.getElementById("f-start-time"),
    endTime: document.getElementById("f-end-time"),
    location: document.getElementById("f-location"),
    expenseAmount: document.getElementById("f-expense-amount"),
    expenseNote: document.getElementById("f-expense-note"),
    details: document.getElementById("f-details"),
    contactCompany: document.getElementById("f-contact-company"),
    contactPosition: document.getElementById("f-contact-position"),
    contactName: document.getElementById("f-contact-name"),
    contactEmail: document.getElementById("f-contact-email"),
    btnOpenMail: document.getElementById("btn-open-mail"),
    btnDelete: document.getElementById("btn-delete-event"),
    btnSave: document.getElementById("btn-save-event"),
    metaLine: document.getElementById("meta-line"),
    emailLogSection: document.getElementById("email-log-section"),
    emailLogList: document.getElementById("email-log-list"),

    mailModal: document.getElementById("mail-modal"),
    mTo: document.getElementById("m-to"),
    mSubject: document.getElementById("m-subject"),
    mBody: document.getElementById("m-body"),
    mailStatus: document.getElementById("mail-status"),
    btnSendMail: document.getElementById("btn-send-mail"),

    exportModal: document.getElementById("export-modal"),
    exStart: document.getElementById("ex-start"),
    exEnd: document.getElementById("ex-end"),
    exEmail: document.getElementById("ex-email"),
    exportStatus: document.getElementById("export-status"),
    btnExportDownload: document.getElementById("btn-export-download"),
    btnExportEmail: document.getElementById("btn-export-email"),
  };

  let currentEventId = null;
  let activeCategories = new Set(ONDA.categories.map((c) => c.key));

  // ---------- 공통 fetch 헬퍼 ----------
  async function api(url, options) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (res.status === 401) {
      window.location.href = "/login";
      throw new Error("login_required");
    }
    return res;
  }

  // ---------- FullCalendar 초기화 ----------
  const calendar = new FullCalendar.Calendar(els.calendar, {
    locale: "ko",
    height: "auto",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,listMonth",
    },
    buttonText: { today: "오늘", month: "월간", list: "목록" },
    events: async (info, success, failure) => {
      try {
        const res = await api("/api/events");
        const all = await res.json();
        success(all.filter((e) => activeCategories.has(e.extendedProps.category)));
      } catch (e) {
        failure(e);
      }
    },
    dateClick: (info) => openCreateModal(info.dateStr),
    eventClick: (info) => openEditModal(info.event),
  });
  calendar.render();

  // ---------- 카테고리 필터 ----------
  document.querySelectorAll(".cat-checkbox").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) activeCategories.add(cb.value);
      else activeCategories.delete(cb.value);
      calendar.refetchEvents();
    });
  });

  // ---------- 모달 열기/닫기 ----------
  function resetForm() {
    els.form.reset();
    els.id.value = "";
    els.btnDelete.classList.add("hidden");
    els.metaLine.textContent = "";
    els.emailLogSection.classList.add("hidden");
    els.emailLogList.innerHTML = "";
    els.btnOpenMail.disabled = true;
  }

  function openCreateModal(dateStr) {
    resetForm();
    els.modalTitle.textContent = "새 일정";
    els.startDate.value = dateStr || todayStr();
    els.endDate.value = els.startDate.value;
    currentEventId = null;
    els.modal.classList.remove("hidden");
  }

  function openEditModal(fcEvent) {
    resetForm();
    const p = fcEvent.extendedProps;
    currentEventId = fcEvent.id;

    els.modalTitle.textContent = "일정 상세";
    els.id.value = fcEvent.id;
    els.category.value = p.category;
    els.assignee.value = p.assignee_user_id || "";
    els.title.value = fcEvent.title;
    els.startDate.value = p.start_date;
    els.endDate.value = p.end_date;
    els.startTime.value = p.start_time || "";
    els.endTime.value = p.end_time || "";
    els.location.value = p.location || "";
    els.expenseAmount.value = p.expense_amount != null ? p.expense_amount : "";
    els.expenseNote.value = p.expense_note || "";
    els.details.value = p.details || "";
    els.contactCompany.value = p.contact_company || "";
    els.contactPosition.value = p.contact_position || "";
    els.contactName.value = p.contact_name || "";
    els.contactEmail.value = p.contact_email || "";

    els.btnOpenMail.disabled = !(ONDA.mailConfigured && p.contact_email);

    const metaBits = [];
    if (p.created_by_name) metaBits.push(`등록: ${p.created_by_name}`);
    if (p.updated_by_name) metaBits.push(`최근 수정: ${p.updated_by_name} (${p.updated_at})`);
    els.metaLine.textContent = metaBits.join(" · ");

    els.btnDelete.classList.remove("hidden");
    els.modal.classList.remove("hidden");

    loadEmailLogs(fcEvent.id);
  }

  function closeModal() {
    els.modal.classList.add("hidden");
    currentEventId = null;
  }

  document.getElementById("btn-new-event").addEventListener("click", () => openCreateModal());
  els.modal.querySelectorAll("[data-close]").forEach((btn) => btn.addEventListener("click", closeModal));

  els.contactEmail.addEventListener("input", () => {
    els.btnOpenMail.disabled = !(ONDA.mailConfigured && els.contactEmail.value.trim());
  });

  function todayStr() {
    const d = new Date();
    return d.toISOString().slice(0, 10);
  }

  // ---------- 저장 ----------
  function collectPayload() {
    return {
      category: els.category.value,
      title: els.title.value.trim(),
      start_date: els.startDate.value,
      end_date: els.endDate.value || els.startDate.value,
      start_time: els.startTime.value || null,
      end_time: els.endTime.value || null,
      location: els.location.value.trim(),
      expense_amount: els.expenseAmount.value ? parseInt(els.expenseAmount.value, 10) : null,
      expense_note: els.expenseNote.value.trim(),
      details: els.details.value.trim(),
      assignee_user_id: els.assignee.value ? parseInt(els.assignee.value, 10) : null,
      contact_company: els.contactCompany.value.trim(),
      contact_position: els.contactPosition.value.trim(),
      contact_name: els.contactName.value.trim(),
      contact_email: els.contactEmail.value.trim(),
    };
  }

  els.btnSave.addEventListener("click", async () => {
    if (!els.form.reportValidity()) return;
    const payload = collectPayload();

    els.btnSave.disabled = true;
    try {
      let res;
      if (currentEventId) {
        res = await api(`/api/events/${currentEventId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        res = await api("/api/events", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert("저장에 실패했습니다: " + (err.error || res.status));
        return;
      }
      closeModal();
      calendar.refetchEvents();
    } finally {
      els.btnSave.disabled = false;
    }
  });

  els.btnDelete.addEventListener("click", async () => {
    if (!currentEventId) return;
    if (!confirm("이 일정을 삭제할까요?")) return;
    const res = await api(`/api/events/${currentEventId}`, { method: "DELETE" });
    if (res.ok) {
      closeModal();
      calendar.refetchEvents();
    } else {
      alert("삭제에 실패했습니다.");
    }
  });

  // ---------- 이메일 발송 ----------
  function buildMailTemplate() {
    const title = els.title.value.trim();
    const start = els.startDate.value;
    const end = els.endDate.value || start;
    const period = start === end ? start : `${start} ~ ${end}`;
    const loc = els.location.value.trim();
    const name = els.contactName.value.trim();

    const subject = `[ONDA] ${title} 관련 안내`;
    const bodyLines = [
      name ? `${name}님, 안녕하세요.` : "안녕하세요.",
      "",
      `ONDA(온다) 관련하여 아래 일정 안내드립니다.`,
      "",
      `- 일정: ${title}`,
      `- 기간: ${period}`,
    ];
    if (loc) bodyLines.push(`- 장소: ${loc}`);
    bodyLines.push("", "감사합니다.", `ONDA · ${ONDA.currentUser.name}`);

    return { subject, body: bodyLines.join("\n") };
  }

  els.btnOpenMail.addEventListener("click", () => {
    const tpl = buildMailTemplate();
    els.mTo.value = els.contactEmail.value.trim();
    els.mSubject.value = tpl.subject;
    els.mBody.value = tpl.body;
    els.mailStatus.textContent = "";
    els.mailStatus.className = "mail-status";
    els.mailModal.classList.remove("hidden");
  });

  els.mailModal.querySelectorAll("[data-close-mail]").forEach((btn) =>
    btn.addEventListener("click", () => els.mailModal.classList.add("hidden"))
  );

  els.btnSendMail.addEventListener("click", async () => {
    if (!currentEventId) {
      // 새 일정은 먼저 저장해야 이메일 발송 기록을 남길 수 있음
      alert("먼저 일정을 저장한 뒤에 이메일을 보내주세요.");
      return;
    }
    els.btnSendMail.disabled = true;
    els.mailStatus.textContent = "발송 중...";
    els.mailStatus.className = "mail-status";
    try {
      const res = await api(`/api/events/${currentEventId}/send-email`, {
        method: "POST",
        body: JSON.stringify({
          to_email: els.mTo.value.trim(),
          subject: els.mSubject.value.trim(),
          body: els.mBody.value,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        els.mailStatus.textContent = "발송되었습니다.";
        els.mailStatus.className = "mail-status ok";
        loadEmailLogs(currentEventId);
        setTimeout(() => els.mailModal.classList.add("hidden"), 900);
      } else {
        els.mailStatus.textContent = "발송 실패: " + (data.message || data.error || "알 수 없는 오류");
        els.mailStatus.className = "mail-status err";
      }
    } finally {
      els.btnSendMail.disabled = false;
    }
  });

  async function loadEmailLogs(eventId) {
    const res = await api(`/api/events/${eventId}/email-logs`);
    if (!res.ok) return;
    const logs = await res.json();
    if (logs.length === 0) {
      els.emailLogSection.classList.add("hidden");
      return;
    }
    els.emailLogSection.classList.remove("hidden");
    els.emailLogList.innerHTML = logs
      .map((lg) => {
        const failCls = lg.status === "failed" ? "log-fail" : "";
        const statusLabel = lg.status === "failed" ? "실패" : "발송됨";
        return `<li class="${failCls}"><strong>${escapeHtml(lg.subject)}</strong> → ${escapeHtml(lg.to_email)}<br>
          ${lg.sent_at} · ${escapeHtml(lg.sent_by_name)} · ${statusLabel}</li>`;
      })
      .join("");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  // ---------- 엑셀 내보내기 ----------
  function exportQueryParams() {
    const params = new URLSearchParams();
    if (els.exStart.value) params.set("start", els.exStart.value);
    if (els.exEnd.value) params.set("end", els.exEnd.value);
    activeCategories.forEach((c) => params.append("category", c));
    return params;
  }

  document.getElementById("btn-open-export").addEventListener("click", () => {
    els.exStart.value = "";
    els.exEnd.value = "";
    els.exEmail.value = "";
    els.exportStatus.textContent = "";
    els.exportStatus.className = "mail-status";
    els.exportModal.classList.remove("hidden");
  });

  els.exportModal.querySelectorAll("[data-close-export]").forEach((btn) =>
    btn.addEventListener("click", () => els.exportModal.classList.add("hidden"))
  );

  els.btnExportDownload.addEventListener("click", () => {
    const params = exportQueryParams();
    window.open(`/api/export/excel?${params.toString()}`, "_blank");
  });

  els.btnExportEmail.addEventListener("click", async () => {
    const toEmail = els.exEmail.value.trim();
    if (!toEmail) {
      els.exportStatus.textContent = "받는사람 이메일을 입력해주세요.";
      els.exportStatus.className = "mail-status err";
      return;
    }
    els.btnExportEmail.disabled = true;
    els.exportStatus.textContent = "발송 중...";
    els.exportStatus.className = "mail-status";
    try {
      const res = await api("/api/export/excel/email", {
        method: "POST",
        body: JSON.stringify({
          to_email: toEmail,
          start: els.exStart.value || null,
          end: els.exEnd.value || null,
          categories: Array.from(activeCategories),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        els.exportStatus.textContent = "이메일로 발송되었습니다.";
        els.exportStatus.className = "mail-status ok";
      } else {
        els.exportStatus.textContent = "발송 실패: " + (data.message || data.error || "알 수 없는 오류");
        els.exportStatus.className = "mail-status err";
      }
    } finally {
      els.btnExportEmail.disabled = false;
    }
  });
})();
