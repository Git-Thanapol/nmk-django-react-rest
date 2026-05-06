     UX Enhancement Plan — nmk ERP (3 Features)

     Context                                                                             
   
     The nmk Django ERP currently has a Help page as the post-login landing, no global   
     search, and no in-app way for users to report bugs or request features. With unit +
     E2E test coverage now in place (138 unit + 43 E2E tests passing), the next priority
     is improving day-to-day UX for non-technical internal users.

     The user picked three features in priority order, with the architectural choices
     already decided:
     1. Dashboard KPI — ApexCharts inside Django templates (no separate Streamlit server)
     2. Global Search (Ctrl+K) — Bootstrap modal triggered globally
     3. Bug/Feature Request system — Conversational form powered by Google Gemini 2.5
     Flash, with image attachments stored locally (NOT sent to LLM). Auto-degrades to a
     plain form (title + description + images saved to DB) if the Gemini quota / token
     budget is exhausted — the user must always be able to submit a request.

     All three reuse existing patterns: Django session auth, Bootstrap 5.3.3 (already in
     base.html), PurchaseAttachment-style file uploads, and the q search-param
     convention.

     ---
     Architecture Decisions (already chosen)

     Decision: Dashboard tech
     Choice: ApexCharts.js via CDN
     Reason: No extra process; uses Django auth; mobile-friendly; matches existing CDN
       pattern
     ────────────────────────────────────────
     Decision: Global search UI
     Choice: Bootstrap modal in base.html
     Reason: Single source of truth; loads on every page; keyboard-driven
     ────────────────────────────────────────
     Decision: LLM provider
     Choice: Google Gemini 2.5 Flash
     Reason: Best Thai language; 1M context; 15 RPM / 1M token-per-day free tier
     ────────────────────────────────────────
     Decision: LLM failure mode
     Choice: Degrade to plain form
     Reason: If Gemini API errors (quota / 429 / network / missing API key), the chat UI
       silently switches to a static title + description + image form — request is still
       saved
     ────────────────────────────────────────
     Decision: Image storage
     Choice: Local MEDIA_ROOT/bug_reports/YYYY/MM/
     Reason: Mirrors PurchaseAttachment.upload_to pattern; no cloud cost
     ────────────────────────────────────────
     Decision: LLM image policy
     Choice: NOT sent to LLM (text only)
     Reason: Per user request; reduces tokens and avoids multimodal complexity

     ---
     Critical Files to Reference (read; modify only where listed)

     - backend/api/templates/base.html:65-183 — sidebar nav (add Dashboard link)
     - backend/api/templates/base.html:187-191 — topbar (insert Ctrl+K button)
     - backend/api/templates/base.html:214-215 — {% block content %}
     - backend/api/models.py:229-240 — PurchaseAttachment (template for BugReportImage)
     - backend/api/views.py:114-117 — current help view (login target — to be repointed)
     - backend/api/views.py:425-477 — purchase form upload loop using
     request.FILES.getlist() (reuse pattern)
     - backend/api/views.py:181,243,297,364,503,657 — existing q-param search per model
     (reuse for global search)
     - backend/api/urls.py:49 — URL registration pattern
     - backend/backend/settings.py:210,213 — MEDIA_ROOT / MEDIA_URL
     - backend/api/tests/factories.py — factories to reuse in new tests
     - backend/api/tests/e2e/conftest.py — logged_in_page, e2e_user, e2e_company fixtures

     ---
     Feature 1 — Dashboard KPI

     Goal

     Replace help as the post-login landing with a real dashboard. Keep the help page
     available, but redirect login → /dashboard/.

     URL & view

     - New URL: path('dashboard/', views.dashboard_view, name='dashboard')
     - New view: dashboard_view (decorated @login_required) — renders shell template with
      no DB queries; charts pull data via JSON endpoints (faster initial paint, easier to
      cache later)
     - Update views.login_view line 126: redirect to 'dashboard' instead of 'help'
     - Add LOGIN_REDIRECT_URL = 'dashboard' to settings.py

     KPI cards (top row, 4 cards)

     1. ยอดขายเดือนนี้ — sum of Invoice.total_amount where invoice_date ∈ this month
     2. ยอดซื้อเดือนนี้ — sum of PurchaseOrder.total_amount for the month
     3. กำไรขั้นต้น — sum(InvoiceItem.line_total - InvoiceItem.cost_price * quantity); show
     % vs prior month
     4. สินค้าใกล้หมด — count of PurchaseItem where remaining_quantity < threshold
     (default 5)

     Charts (ApexCharts)

     ┌────────────────────────────┬───────────────┬─────────────────────────────────────┐
     │           Chart            │     Type      │             Data source             │
     ├────────────────────────────┼───────────────┼─────────────────────────────────────┤
     │ 30-day sales trend         │ line          │ Invoice grouped by date             │
     ├────────────────────────────┼───────────────┼─────────────────────────────────────┤
     │ Top 10 SKUs by quantity    │ horizontal    │ InvoiceItem aggregated              │
     │                            │ bar           │                                     │
     ├────────────────────────────┼───────────────┼─────────────────────────────────────┤
     │ Purchase vs Sales (last 6  │ grouped       │ both totals per month               │
     │ months)                    │ column        │                                     │
     ├────────────────────────────┼───────────────┼─────────────────────────────────────┤
     │ Stock alert (low batches)  │ data table    │ PurchaseItem where                  │
     │                            │               │ remaining_quantity < 5              │
     ├────────────────────────────┼───────────────┼─────────────────────────────────────┤
     │ Profit margin gauge        │ radial bar    │ this-month margin %                 │
     └────────────────────────────┴───────────────┴─────────────────────────────────────┘

     Filters

     - Date range: this month / last month / last 30 days / custom range (HTML date
     inputs)
     - Company selector (dropdown of Company.objects.all()) — applies to all charts via
     query param
     - Filters re-fetch JSON endpoints on change — no full page reload

     JSON endpoints (all @login_required, all return JSON)

     - GET /dashboard/api/kpi-summary/?company=&from=&to=
     - GET /dashboard/api/sales-trend/?company=&days=30
     - GET /dashboard/api/top-skus/?company=&from=&to=&limit=10
     - GET /dashboard/api/purchase-vs-sales/?company=&months=6
     - GET /dashboard/api/stock-alerts/?company=&threshold=5

     All five endpoints implemented in api/views.py as functions (not DRF) to match
     existing template-view style.

     Files to modify / create

     - modify backend/api/templates/base.html — add sidebar nav link "Dashboard" with
     bi-speedometer2 icon, place at top of nav before existing items
     - modify backend/api/views.py — add dashboard_view and 5 JSON endpoints; change
     login redirect target
     - modify backend/api/urls.py — add 6 URLs under dashboard/
     - modify backend/backend/settings.py — add LOGIN_REDIRECT_URL
     - create backend/api/templates/api/dashboard.html — KPI cards + chart containers +
     filter form
     - create backend/static/js/dashboard.js — ApexCharts init, fetch + render, filter
     wiring
     - create backend/api/utils_dashboard.py — pure-function aggregation helpers
     (testable in isolation, no view coupling)

     Tests

     - backend/api/tests/test_dashboard.py (unit): aggregation correctness — fixed-date
     factories → known totals → assert helper output
     - backend/api/tests/e2e/test_dashboard.py: page renders; one chart container
     appears; one JSON endpoint returns 200 with expected keys
     - Update backend/api/tests/e2e/test_auth.py — wait_for_url("**/help/") →
     wait_for_url("**/dashboard/")

     ---
     Feature 2 — Global Search (Ctrl+K)

     Goal

     A floating modal opens on Ctrl+K (or ⌘+K on Mac) showing categorized results across
     Products, Vendors, Customers, Invoices, Purchases, Companies. User types → instant
     results → arrow-key + Enter navigates to detail page.

     UI

     - Bootstrap 5 modal placed at the bottom of base.html (inside body, after sidebar) —
      always available
     - Trigger A: keyboard shortcut bound on document — (e.ctrlKey || e.metaKey) && e.key
      === 'k' → opens modal, focuses input
     - Trigger B: search-icon button in topbar (base.html:187-191) for users who don't
     know the shortcut
     - Search input auto-focused on open; Esc closes; arrow keys move highlight; Enter
     navigates
     - Results grouped by category with bi- icons; max 5 per group; "Show all" link runs
     the existing per-page list filter

     Search endpoint

     GET /api/search/?q=<query> returns JSON:
     {
       "products": [{"id": 1, "label": "SKU-001 — Product Name", "url":
     "/products/edit/1/"}],
       "vendors": [...],
       "customers": [...],
       "invoices": [...],
       "purchases": [...],
       "companies": [...]
     }
     - Each model: limit 5 results, ordered by most-recent
     - Search fields:
       - Product: sku, name, category (icontains)
       - Vendor: name, phone
       - Customer: name, phone
       - Invoice: invoice_number, customer__name
       - Purchase: po_number, vendor__name
       - Company: name

     Files to modify / create

     - modify backend/api/templates/base.html — append Ctrl+K modal markup; add icon
     button in topbar
     - modify backend/api/views.py — add global_search_view returning JsonResponse
     - modify backend/api/urls.py — add path('api/search/', views.global_search_view,
     name='global_search')
     - create backend/static/js/global_search.js — keyboard binding, debounced (200ms)
     fetch, render, navigate

     Tests

     - backend/api/tests/test_search.py (unit): endpoint returns correct grouped results
     for each model
     - backend/api/tests/e2e/test_global_search.py: press Ctrl+K → modal visible; type
     SKU → results appear; press Enter → navigates

     ---
     Feature 3 — Bug / Feature Request System (LLM-driven, with plain-form fallback)

     Goal

     Floating "Report" button (bottom-right) opens a chat-style modal. User types initial
      description; Gemini asks 3-5 clarifying questions in Thai. User can attach multiple
      images at any point (NOT sent to LLM). When LLM judges enough info gathered, it
     produces a Thai summary; user reviews, edits if needed, and submits.

     Critical reliability requirement: if Gemini fails for any reason (quota exhausted,
     429, 5xx, network error, GEMINI_API_KEY missing) the modal automatically falls back
     to a plain form with three fields — Title, Description, Images — and the user can
     still submit. The submitted record is identical in shape; only the conversation JSON
      is empty and a degraded=True flag is recorded.

     Submitted reports appear in /bug-reports/ for the team to triage.

     Models (in api/models.py)

     class BugReport(models.Model):
         TYPE_CHOICES = [('BUG', 'รายงานบั๊ก'), ('FEATURE', 'ขอฟีเจอร์ใหม่')]
         STATUS_CHOICES = [('NEW', 'ใหม่'), ('IN_PROGRESS', 'กำลังดำเนินการ'),
                           ('RESOLVED', 'แก้ไขแล้ว'), ('REJECTED', 'ปฏิเสธ')]

         title = models.CharField(max_length=200)
         report_type = models.CharField(max_length=10, choices=TYPE_CHOICES,
     default='BUG')
         status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
         summary = models.TextField()              # final LLM-generated OR user-typed
     description
         conversation = models.JSONField(default=list)  # [] when degraded
         degraded = models.BooleanField(default=False)  # True if LLM was unavailable
         created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
         created_at = models.DateTimeField(auto_now_add=True)
         resolved_at = models.DateTimeField(null=True, blank=True)
         admin_notes = models.TextField(blank=True)

     class BugReportImage(models.Model):
         bug_report = models.ForeignKey(BugReport, on_delete=models.CASCADE,
                                        related_name='images')
         image = models.ImageField(upload_to='bug_reports/%Y/%m/')
         uploaded_at = models.DateTimeField(auto_now_add=True)

     Migration: standard makemigrations + migrate. No data migration needed.

     LLM integration (api/utils_llm.py — new file)

     import os, json, logging
     import google.generativeai as genai
     from google.api_core import exceptions as gax_exc

     log = logging.getLogger(__name__)

     class LLMUnavailable(Exception):
         """Raised on quota/auth/network failure — caller should fall back to plain
     form."""

     API_KEY = os.environ.get('GEMINI_API_KEY')
     if API_KEY:
         genai.configure(api_key=API_KEY)

     SYSTEM_PROMPT_TH = """คุณเป็นผู้ช่วยรวบรวม bug report / feature request ...
     ถามทีละข้อ ตอบเป็น JSON {"done": bool, "next_question"|"summary": "..."}"""

     def chat(history: list[dict], user_message: str) -> dict:
         if not API_KEY:
             raise LLMUnavailable("GEMINI_API_KEY not set")
         try:
             model = genai.GenerativeModel('gemini-2.5-flash',
                                           system_instruction=SYSTEM_PROMPT_TH)
             chat_session = model.start_chat(history=[
                 {'role': 'user' if m['role'] == 'user' else 'model',
                  'parts': [m['content']]} for m in history
             ])
             response = chat_session.send_message(user_message)
             try:
                 return json.loads(response.text)
             except json.JSONDecodeError:
                 return {'done': False, 'next_question': response.text}
         except (gax_exc.ResourceExhausted,        # quota / token budget
                 gax_exc.PermissionDenied,         # bad key
                 gax_exc.ServiceUnavailable,
                 gax_exc.DeadlineExceeded,
                 gax_exc.GoogleAPICallError) as e:
             log.warning("Gemini unavailable: %s", e)
             raise LLMUnavailable(str(e)) from e

     Add to requirements.txt: google-generativeai>=0.8.3

     Add to .env and .env.prod: GEMINI_API_KEY= (empty value is OK — system degrades
     cleanly)

     Workflow & endpoints

     Endpoint: /bug-reports/chat/
     Method: POST
     Purpose: Send user message + history → LLM responds
     Failure behavior: On LLMUnavailable → return {"degraded": true} (HTTP 200, NOT 5xx —
      JS
       reads flag and switches UI)
     ────────────────────────────────────────
     Endpoint: /bug-reports/upload-image/
     Method: POST
     Purpose: Multipart upload, returns image URL + temp ID
     Failure behavior: Independent of LLM; works in both modes
     ────────────────────────────────────────
     Endpoint: /bug-reports/submit/
     Method: POST
     Purpose: Persist BugReport + linked BugReportImage rows
     Failure behavior: Accepts both shapes: {title, conversation, summary, image_ids}
     (chat)
       and {title, description, image_ids, degraded: true} (plain). Sets degraded=True on
      the
        model when chat unavailable
     ────────────────────────────────────────
     Endpoint: /bug-reports/
     Method: GET
     Purpose: List view (admin sees all, others see own)
     Failure behavior: —
     ────────────────────────────────────────
     Endpoint: /bug-reports/<id>/
     Method: GET
     Purpose: Detail view with conversation transcript + images
     Failure behavior: If degraded=True, transcript section is hidden — show description
     only
     ────────────────────────────────────────
     Endpoint: /bug-reports/<id>/status/
     Method: POST
     Purpose: Update status and admin_notes (staff only)
     Failure behavior: —

     Orphan-image cleanup: image rows created during chat carry a session_key and
     bug_report=null. On /bug-reports/submit/, the chosen image IDs get linked; the rest
     from the same session are deleted. Out-of-band cleanup (cron / management command)
     for abandoned sessions noted in follow-up.

     UI components & fallback flow

     Floating button (in base.html, fixed bottom-right):
     <button id="bug-report-trigger" class="btn btn-warning rounded-circle
     position-fixed"
             style="bottom:20px;right:20px;width:56px;height:56px;z-index:1050;">
         <i class="bi bi-bug-fill"></i>
     </button>

     Modal contains TWO panes (only one visible at a time):

     - Pane A — Chat mode (default): transcript pane + text input + image upload + Submit
      (disabled until LLM marks done)
     - Pane B — Plain mode (fallback): Title input + Description textarea + image upload
     + Submit (always enabled). A small inline notice:
     "ระบบแนะนำคำถามอัตโนมัติไม่พร้อมใช้งานชั่วคราว — ส่งรายละเอียดและรูปประกอบได้เลย"

     JS (backend/static/js/bug_report.js):
     - Maintains in-memory history array of messages
     - On user message → POST to /bug-reports/chat/
       - If response has degraded: true → swap to Pane B; carry over whatever the user
     already typed into the Description textarea
       - If JS detects two consecutive chat failures or the first POST already returns
     degraded → start in Pane B (no flicker)
       - Otherwise append assistant reply; when done, show summary editor + enable Submit
     - Image upload independent: POSTs to /bug-reports/upload-image/ regardless of mode →
      preview thumbnails appear in the same images strip used by both panes
     - On Submit → POSTs payload (chat or plain shape) to /bug-reports/submit/

     Admin list & detail (backend/api/templates/api/bug_reports/list.html, detail.html):
     - List: filter by status, type, user, date; show a small badge on degraded reports
     - Detail: full conversation log if not degraded (collapsed by default); summary;
     attached images grid; status changer (staff only)

     Files to modify / create

     - modify backend/api/models.py — add BugReport, BugReportImage
     - modify backend/api/views.py — add 6 view functions; chat endpoint handles
     LLMUnavailable
     - modify backend/api/urls.py — add 6 URLs under bug-reports/
     - modify backend/api/forms.py — BugReportStatusForm (status + admin_notes)
     - modify backend/api/templates/base.html — floating button + chat modal markup with
     both panes
     - modify backend/api/admin.py — register BugReport (inline BugReportImage)
     - modify backend/requirements.txt — google-generativeai>=0.8.3
     - modify backend/.env and backend/.env.prod — GEMINI_API_KEY=
     - modify backend/backend/settings.py — read GEMINI_API_KEY from env (empty allowed;
     system degrades)
     - create backend/api/utils_llm.py — Gemini wrapper + LLMUnavailable
     - create backend/static/js/bug_report.js — chat + plain-form switching
     - create backend/api/templates/api/bug_reports/list.html
     - create backend/api/templates/api/bug_reports/detail.html
     - create migration 0028_bug_report.py (auto-generated)

     Tests

     - backend/api/tests/test_bug_report.py (unit):
       - BugReport / BugReportImage model behavior
       - View permissions: non-staff can't see others' reports; non-staff can't change
     status
       - /bug-reports/chat/ happy path with mocked utils_llm.chat (no real Gemini calls
     in CI) → verify history threading
       - /bug-reports/chat/ degraded path: mock utils_llm.chat to raise LLMUnavailable →
     assert response is HTTP 200 with {"degraded": true}
       - /bug-reports/submit/ plain-form path: POST {title, description, image_ids} with
     no conversation → assert BugReport saved with degraded=True and conversation == []
       - Missing API key path: unset GEMINI_API_KEY env in test → first chat call returns
      degraded: true immediately
       - Image upload flow stores file under correct path; orphan cleanup on submit drops
      unrelated session images
     - backend/api/tests/e2e/test_bug_report.py:
       - Chat path: monkeypatch utils_llm.chat to canned responses → click floating
     button → modal opens → type → assistant reply visible → submit → entry in
     /bug-reports/
       - Degraded path: monkeypatch to raise LLMUnavailable → modal opens → after first
     send, plain form pane is visible → fill Title + Description → submit → entry visible
      with degraded badge
       - Image upload: thumbnail appears in both modes

     ---
     Implementation Order

     The user explicitly requested this order — implement and ship each before starting
     the next:

     1. Feature 1: Dashboard — biggest UX win, lowest risk, no external deps
     2. Feature 2: Global Search — small surface area, builds on existing search code
     3. Feature 3: Bug/Feature Request — most complex; works without GEMINI_API_KEY
     thanks to plain-form fallback (deploy is non-blocking on key availability)

     Between features: run pytest api/tests/ --no-cov and pytest api/tests/e2e/ --no-cov
     to confirm 181 prior tests still pass.

     ---
     Verification

     After all three features are implemented:

     1. cd backend && pytest api/tests/ --no-cov -v — unit tests for new code pass;
     previous 138 still green
     2. pytest api/tests/e2e/ --no-cov -v — E2E for new flows pass; previous 43 still
     green (plus updated test_auth.py)
     3. Manual smoke (with dev server running):
       - Login → lands on /dashboard/; all 4 KPI cards and 5 charts render with real data
       - Press Ctrl+K → modal opens; type a known SKU → product appears → Enter navigates
       - With GEMINI_API_KEY set: click floating bug button → chat with Gemini (live) →
     attach 2 images → submit → entry visible at /bug-reports/
       - With GEMINI_API_KEY unset: click floating bug button → chat sends one message →
     modal switches to plain form → fill title + description + attach 1 image → submit →
     entry visible with "ส่งแบบฟอร์มธรรมดา" badge
       - As staff: open the report → mark "RESOLVED" → status persists
     4. python manage.py check --deploy — no new security warnings introduced
     5. Verify quota-exhaustion behaviour: temporarily set GEMINI_API_KEY=invalid → chat
     endpoint returns {degraded: true} cleanly (no 500)

     ---
     Risks & Mitigations

     ┌───────────────────────────┬──────────────────────────────────────────────────────┐
     │           Risk            │                      Mitigation                      │
     ├───────────────────────────┼──────────────────────────────────────────────────────┤
     │ Gemini API down or        │ LLMUnavailable exception caught → endpoint returns   │
     │ rate-limited              │ {degraded: true} → JS swaps to plain form. User can  │
     │                           │ still submit.                                        │
     ├───────────────────────────┼──────────────────────────────────────────────────────┤
     │ Gemini token / daily      │ Same path: ResourceExhausted → LLMUnavailable →      │
     │ quota exhausted           │ plain form. Daily-budget overflow does not block the │
     │                           │  team.                                               │
     ├───────────────────────────┼──────────────────────────────────────────────────────┤
     │                           │ Wrapper checks for the key first; raises             │
     │ GEMINI_API_KEY missing in │ LLMUnavailable immediately → users see plain form    │
     │  production               │ from the very first interaction. No setup gate on    │
     │                           │ shipping the feature.                                │
     ├───────────────────────────┼──────────────────────────────────────────────────────┤
     │ Orphan uploaded images    │ Submit-time cleanup of session-bound unattached      │
     │ filling disk              │ uploads; full cron in follow-up                      │
     ├───────────────────────────┼──────────────────────────────────────────────────────┤
     │ Dashboard JSON endpoints  │ All endpoints @login_required only (cheap for v1);   │
     │ expensive on big DB       │ add cache_page(60) decorator if a query exceeds      │
     │                           │ 500ms — measure first                                │
     ├───────────────────────────┼──────────────────────────────────────────────────────┤
     │ Ctrl+K conflicts with     │ Modal still works on most browsers; users on         │
     │ browser shortcut          │ browsers that swallow Ctrl+K (Firefox: focus address │
     │                           │  bar) can use the topbar icon button instead         │
     ├───────────────────────────┼──────────────────────────────────────────────────────┤
     │ LOGIN_REDIRECT_URL change │ Update E2E test_auth.py to wait for **/dashboard/ as │
     │  breaks existing tests    │  part of Feature 1                                   │
     └───────────────────────────┴──────────────────────────────────────────────────────┘

     ---
     Out of Scope (note for follow-up)

     - Real-time dashboard (websockets) — v1 polls JSON on filter change only
     - Bug-report email/Line notifications to admins — add post-MVP
     - Searching inside file contents (e.g., invoice line items) — v1 searches top-level
     fields only
     - Attaching screen recordings to bug reports — images only for v1
     - LLM-suggested duplicate detection on new bug reports — future
     - Cron-based orphan-image cleanup — submit-time cleanup for v1
     - Sending images to Gemini multimodal — explicitly excluded by user