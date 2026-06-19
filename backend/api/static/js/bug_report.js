/**
 * Bug / Feature Request — Chat modal with Gemini + plain-form fallback.
 *
 * Two panes inside #bug-report-modal:
 *   #br-chat-pane   — chat with LLM, submit disabled until done:true
 *   #br-plain-pane  — plain form (title + description), always submittable
 *
 * Images: shared between both panes, uploaded independently to /bug-reports/upload-image/
 */

(function () {
  "use strict";

  // ── State ────────────────────────────────────────────────────────────────
  let history = [];       // [{role, content}]
  let imageIds = [];      // temp BugReportImage PKs
  let degraded = false;
  let llmDone = false;
  let modal = null;

  // ── DOM shortcuts ────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  function showPane(pane) {
    $("br-chat-pane").style.display = pane === "chat" ? "" : "none";
    $("br-plain-pane").style.display = pane === "plain" ? "" : "none";
  }

  function appendMessage(role, text) {
    const wrap = $("br-chat-messages");
    const el = document.createElement("div");
    el.className = `br-msg br-msg--${role} mb-2`;
    el.innerHTML = `<div class="br-bubble">${escHtml(text)}</div>`;
    wrap.appendChild(el);
    wrap.scrollTop = wrap.scrollHeight;
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setLoading(loading) {
    const btn = $("br-send-btn");
    if (btn) btn.disabled = loading;
  }

  // ── Degrade to plain form ─────────────────────────────────────────────────
  function degradeToPlain(carriedText) {
    degraded = true;
    showPane("plain");
    if (carriedText && $("br-plain-description")) {
      $("br-plain-description").value = carriedText;
    }
    const notice = $("br-degraded-notice");
    if (notice) notice.classList.remove("d-none");
  }

  // ── Send message to LLM ──────────────────────────────────────────────────
  async function sendMessage() {
    const input = $("br-user-input");
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    appendMessage("user", text);
    history.push({ role: "user", content: text });
    setLoading(true);

    try {
      const res = await fetch("/bug-reports/chat/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrf(),
        },
        body: JSON.stringify({ history: history.slice(0, -1), message: text }),
      });

      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();

      if (data.degraded) {
        degradeToPlain(text);
        return;
      }

      const assistantText = data.next_question || data.summary || "";
      history.push({ role: "assistant", content: assistantText });
      appendMessage("assistant", assistantText);

      if (data.done) {
        llmDone = true;
        $("br-summary-section").classList.remove("d-none");
        if ($("br-summary-text")) {
          $("br-summary-text").value = data.summary || "";
        }
        $("br-chat-submit").disabled = false;
      }
    } catch (e) {
      console.error("Bug report chat error:", e);
      degradeToPlain(text);
    } finally {
      setLoading(false);
    }
  }

  // ── Image upload ─────────────────────────────────────────────────────────
  async function uploadImages(files) {
    for (const file of files) {
      const fd = new FormData();
      fd.append("image", file);
      fd.append("csrfmiddlewaretoken", getCsrf());
      try {
        const res = await fetch("/bug-reports/upload-image/", {
          method: "POST",
          credentials: "same-origin",
          body: fd,
        });
        if (!res.ok) continue;
        const data = await res.json();
        imageIds.push(data.id);
        addThumbnail(data.url);
      } catch (e) {
        console.error("Image upload error:", e);
      }
    }
  }

  function addThumbnail(url) {
    ["br-image-strip", "br-image-strip-plain"].forEach((id) => {
      const strip = $(id);
      if (!strip) return;
      const img = document.createElement("img");
      img.src = url;
      img.className = "br-thumb rounded";
      img.style.cssText = "width:56px;height:56px;object-fit:cover;cursor:pointer";
      img.title = "คลิกเพื่อดูรูปเต็ม";
      img.addEventListener("click", () => window.open(url, "_blank"));
      strip.appendChild(img);
    });
  }

  // ── Submit (chat path) ───────────────────────────────────────────────────
  async function submitChat() {
    const title = ($("br-chat-title")?.value || "").trim();
    const summary = ($("br-summary-text")?.value || "").trim();
    const type = $("br-type-select")?.value || "BUG";
    if (!title || !summary) {
      alert("กรุณากรอกหัวเรื่อง และตรวจสอบสรุปรายละเอียด");
      return;
    }
    await submitReport({ title, summary, type, conversation: history, degraded: false });
  }

  // ── Submit (plain path) ──────────────────────────────────────────────────
  async function submitPlain() {
    const title = ($("br-plain-title")?.value || "").trim();
    const description = ($("br-plain-description")?.value || "").trim();
    const type = $("br-plain-type-select")?.value || "BUG";
    if (!title || !description) {
      alert("กรุณากรอกหัวเรื่องและรายละเอียด");
      return;
    }
    await submitReport({ title, summary: description, type, conversation: [], degraded: true });
  }

  async function submitReport(payload) {
    payload.image_ids = imageIds;
    try {
      const res = await fetch("/bug-reports/submit/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrf(),
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      modal.hide();
      if (data.url) {
        window.location.href = data.url;
      } else {
        showToast("ส่งรายงานเรียบร้อยแล้ว ขอบคุณ!");
        resetState();
      }
    } catch (e) {
      alert("เกิดข้อผิดพลาดในการส่ง กรุณาลองใหม่");
      console.error(e);
    }
  }

  // ── CSRF ──────────────────────────────────────────────────────────────────
  function getCsrf() {
    return document.cookie.split(";").reduce((val, c) => {
      const [k, v] = c.trim().split("=");
      return k === "csrftoken" ? decodeURIComponent(v) : val;
    }, "");
  }

  // ── Toast ─────────────────────────────────────────────────────────────────
  function showToast(msg) {
    const el = document.createElement("div");
    el.className = "toast align-items-center text-bg-success border-0 position-fixed bottom-0 end-0 m-3 show";
    el.setAttribute("role", "alert");
    el.style.zIndex = 1100;
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${escHtml(msg)}</div>
      <button class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  // ── Clipboard paste ──────────────────────────────────────────────────────
  let modalOpen = false;

  function handlePaste(e) {
    if (!modalOpen) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    const imageFiles = [];
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) imageFiles.push(file);
      }
    }
    if (imageFiles.length) {
      e.preventDefault();
      uploadImages(imageFiles);
      showToast(`วางรูปจากคลิปบอร์ด ${imageFiles.length} ไฟล์`);
    }
  }

  // ── Reset ─────────────────────────────────────────────────────────────────
  function resetState() {
    history = [];
    imageIds = [];
    degraded = false;
    llmDone = false;
    if ($("br-chat-messages")) $("br-chat-messages").innerHTML = "";
    if ($("br-user-input")) $("br-user-input").value = "";
    if ($("br-image-strip")) $("br-image-strip").innerHTML = "";
    if ($("br-image-strip-plain")) $("br-image-strip-plain").innerHTML = "";
    if ($("br-summary-section")) $("br-summary-section").classList.add("d-none");
    if ($("br-chat-submit")) $("br-chat-submit").disabled = true;
    if ($("br-plain-title")) $("br-plain-title").value = "";
    if ($("br-plain-description")) $("br-plain-description").value = "";
    if ($("br-degraded-notice")) $("br-degraded-notice").classList.add("d-none");
    showPane("chat");
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("bug-report-modal");
    if (!modalEl) return;

    modal = new bootstrap.Modal(modalEl, { backdrop: true, keyboard: true });
    showPane("chat");

    // Track modal open/close for paste handler
    modalEl.addEventListener("shown.bs.modal", () => { modalOpen = true; });
    modalEl.addEventListener("hidden.bs.modal", () => { modalOpen = false; });

    // Global paste listener — active only while modal is open
    document.addEventListener("paste", handlePaste);

    // Trigger button (topbar)
    document.getElementById("bug-report-trigger")?.addEventListener("click", function () {
      resetState();
      modal.show();
    });

    // Chat: send on button click or Enter
    $("br-send-btn")?.addEventListener("click", sendMessage);
    $("br-user-input")?.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Image upload — shared strip
    $("br-image-input")?.addEventListener("change", function () {
      if (this.files?.length) uploadImages(Array.from(this.files));
      this.value = "";
    });

    // Submit buttons
    $("br-chat-submit")?.addEventListener("click", submitChat);
    $("br-plain-submit")?.addEventListener("click", submitPlain);

    // Reset when modal hides
    modalEl.addEventListener("hidden.bs.modal", resetState);
  });
})();
