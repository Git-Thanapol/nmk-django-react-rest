"""
Gemini LLM wrapper for the Bug/Feature Request conversational intake
and the Help Q&A assistant.

If GEMINI_API_KEY is not set or Gemini fails for any reason, raises LLMUnavailable.
Callers catch LLMUnavailable and return {degraded: true} so the UI falls back gracefully.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
_client = None

SYSTEM_PROMPT = """คุณเป็นผู้ช่วยรวบรวมข้อมูล bug report / feature request สำหรับระบบ ERP ภาษาไทย
ภารกิจของคุณ: ถามคำถามสั้น ๆ ทีละข้อเพื่อให้ได้ข้อมูลครบ 5 ด้าน:
1. หน้า/ฟังก์ชันที่เกี่ยวข้อง
2. ขั้นตอนทำซ้ำได้ (กรณี bug)
3. ผลลัพธ์ที่คาดหวัง
4. ผลลัพธ์ที่เกิดขึ้นจริง
5. ความเร่งด่วน (เร่งด่วน / ปกติ / ต่ำ)

กฎ:
- ถามทีละข้อเท่านั้น ห้ามถามหลายข้อพร้อมกัน
- เมื่อมีข้อมูลครบ ให้สรุปเป็น JSON และตอบกลับ
- ตอบเป็น JSON เสมอ ไม่มีข้อความอื่นนอก JSON

รูปแบบ JSON ถ้ายังไม่ครบ:
{"done": false, "next_question": "คำถามของคุณ"}

รูปแบบ JSON เมื่อครบแล้ว:
{"done": true, "summary": "สรุปรายละเอียดครบถ้วนเป็นภาษาไทย"}"""


class LLMUnavailable(Exception):
    """Raised when Gemini is unavailable; caller should degrade to plain form."""


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not _API_KEY:
        raise LLMUnavailable("GEMINI_API_KEY not configured")
    try:
        from google import genai
        _client = genai.Client(api_key=_API_KEY)
        return _client
    except ImportError as exc:
        raise LLMUnavailable("google-genai not installed") from exc
    except Exception as exc:
        log.warning("Gemini client init failed: %s", exc)
        raise LLMUnavailable(str(exc)) from exc


def chat(history: list[dict], user_message: str) -> dict:
    """
    Send user_message with history to Gemini.

    history items: {"role": "user"|"assistant", "content": str}
    Returns: {"done": bool, "next_question": str} | {"done": bool, "summary": str}
    Raises: LLMUnavailable on any API error.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise LLMUnavailable("google-genai not installed") from exc

    try:
        client = _get_client()

        gemini_history = [
            types.Content(
                role="user" if m["role"] == "user" else "model",
                parts=[types.Part(text=m["content"])],
            )
            for m in history
        ]

        chat_session = client.chats.create(
            model="gemini-3-flash-preview",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
            history=gemini_history,
        )
        response = chat_session.send_message(user_message)
        text = response.text.strip()

        # Strip markdown code fences if Gemini wraps the JSON
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"done": False, "next_question": text}

    except LLMUnavailable:
        raise
    except Exception as exc:
        log.warning("Gemini API error: %s", exc)
        raise LLMUnavailable(str(exc)) from exc


# ─── Help Q&A ────────────────────────────────────────────────────────────────

# Map topic keywords → help page anchor id
HELP_ANCHORS: dict[str, tuple[str, str]] = {
    "dashboard": ("sec-dashboard", "Dashboard"),
    "purchase": ("sec-purchase", "ใบสั่งซื้อ (PO)"),
    "po": ("sec-purchase", "ใบสั่งซื้อ (PO)"),
    "ซื้อ": ("sec-purchase", "ใบสั่งซื้อ (PO)"),
    "invoice": ("sec-invoice", "ใบกำกับ / ใบขาย"),
    "ใบกำกับ": ("sec-invoice", "ใบกำกับ / ใบขาย"),
    "ขาย": ("sec-invoice", "ใบกำกับ / ใบขาย"),
    "product": ("sec-product", "สินค้า"),
    "สินค้า": ("sec-product", "สินค้า"),
    "stock": ("sec-product", "สินค้า"),
    "sku": ("sec-product", "สินค้า"),
    "vendor": ("sec-vendor", "ผู้จำหน่าย"),
    "ผู้จำหน่าย": ("sec-vendor", "ผู้จำหน่าย"),
    "transaction": ("sec-transaction", "รายรับ/รายจ่าย"),
    "รายรับ": ("sec-transaction", "รายรับ/รายจ่าย"),
    "รายจ่าย": ("sec-transaction", "รายรับ/รายจ่าย"),
    "import": ("sec-import", "นำเข้าข้อมูล Platform"),
    "shopee": ("sec-import", "นำเข้าข้อมูล Platform"),
    "lazada": ("sec-import", "นำเข้าข้อมูล Platform"),
    "tiktok": ("sec-import", "นำเข้าข้อมูล Platform"),
    "นำเข้า": ("sec-import", "นำเข้าข้อมูล Platform"),
    "mapping": ("sec-mapping", "จับคู่สินค้า"),
    "map": ("sec-mapping", "จับคู่สินค้า"),
    "จับคู่": ("sec-mapping", "จับคู่สินค้า"),
    "report": ("sec-reports", "รายงาน"),
    "รายงาน": ("sec-reports", "รายงาน"),
    "ภาษี": ("sec-reports", "รายงาน"),
    "vat": ("sec-vat", "VAT Tracking"),
    "50 ทวิ": ("sec-wht", "ใบรับรอง 50 ทวิ"),
    "wht": ("sec-wht", "ใบรับรอง 50 ทวิ"),
    "หักภาษี": ("sec-wht", "ใบรับรอง 50 ทวิ"),
    "company": ("sec-company", "บริษัท"),
    "บริษัท": ("sec-company", "บริษัท"),
    "search": ("sec-search", "ค้นหาทั่วไป"),
    "ค้นหา": ("sec-search", "ค้นหาทั่วไป"),
    "bug": ("sec-bugreport", "แจ้งปัญหา"),
    "แจ้งปัญหา": ("sec-bugreport", "แจ้งปัญหา"),
    "fifo": ("sec-invoice", "ใบกำกับ / ใบขาย"),
    "faq": ("sec-faq", "FAQ"),
    "สถานะ": ("sec-status", "สถานะต่างๆ"),
    "status": ("sec-status", "สถานะต่างๆ"),
    "draft": ("sec-status", "สถานะต่างๆ"),
    "paid": ("sec-status", "สถานะต่างๆ"),
    "billed": ("sec-status", "สถานะต่างๆ"),
}


@lru_cache(maxsize=1)
def _load_help_docs() -> str:
    docs_path = Path(__file__).parent.parent / "docs" / "help.md"
    if docs_path.exists():
        return docs_path.read_text(encoding="utf-8")
    return ""


_HELP_SYSTEM_PROMPT_TEMPLATE = """\
คุณเป็น AI ผู้ช่วยสำหรับระบบ Namkang Phone ERP ภารกิจ: ตอบคำถามของ user เกี่ยวกับการใช้งานระบบ

ข้อมูลระบบ (คู่มือฉบับเต็ม):
---
{docs}
---

กฎการตอบ:
- ตอบเป็นภาษาไทยแบบสบายๆ ไม่เป็นทางการ (internal use)
- ตอบตรงประเด็น กระชับ ไม่ยาวเกินไป
- ถ้าคำถามตรงกับหัวข้อในคู่มือ ให้ระบุ help_anchor ของหัวข้อนั้น
- help_anchor คือค่าใน anchor comment ของแต่ละหัวข้อ เช่น "sec-purchase", "sec-invoice"
- ถ้าไม่รู้จริงๆ หรือคำถามนอกขอบเขตระบบ ให้บอกตรงๆ ว่าไม่ทราบ
- ตอบเป็น JSON เสมอ ไม่มีข้อความอื่นนอก JSON

รูปแบบ JSON:
{{"answer": "คำตอบของคุณ", "help_anchor": "sec-xxx หรือ null", "help_title": "ชื่อหัวข้อ หรือ null"}}
"""


def help_ask(question: str) -> dict:
    """
    Single-turn Q&A using the help docs as context.

    Returns: {"answer": str, "help_anchor": str|None, "help_title": str|None}
    Raises: LLMUnavailable
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise LLMUnavailable("google-genai not installed") from exc

    try:
        client = _get_client()
        docs = _load_help_docs()
        system_prompt = _HELP_SYSTEM_PROMPT_TEMPLATE.format(docs=docs)

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=question,
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {"answer": text, "help_anchor": None, "help_title": None}

        # Fallback: scan question for known topic keywords if LLM didn't suggest anchor
        if not result.get("help_anchor"):
            q_lower = question.lower()
            for keyword, (anchor, title) in HELP_ANCHORS.items():
                if keyword in q_lower:
                    result["help_anchor"] = anchor
                    result["help_title"] = title
                    break

        return result

    except LLMUnavailable:
        raise
    except Exception as exc:
        log.warning("Gemini help_ask error: %s", exc)
        raise LLMUnavailable(str(exc)) from exc


# ─── Product Mapping AI Pre-Match ────────────────────────────────────────────

_SUGGEST_SYSTEM_PROMPT = """\
คุณเป็น AI ช่วยจับคู่ชื่อสินค้าจากแพลตฟอร์ม e-commerce (Shopee/Lazada/TikTok) กับสินค้าในระบบ ERP

โจทย์: ชื่อสินค้าบนแพลตฟอร์มถูกพิมพ์แบบ free-text ไม่เป็นมาตรฐาน เช่น "AP4 ANC สีขาว มือ1 ของแท้"
คุณต้องวิเคราะห์ว่าน่าจะตรงกับสินค้าตัวไหนในรายการ candidates

กฎ:
- ตอบเป็น JSON เสมอ ไม่มีข้อความอื่นนอก JSON
- เลือก top 3 candidates ต่อ item (confidence ≥ 0.5 เท่านั้น)
- confidence เป็น float 0.0-1.0
- reason อธิบายสั้นๆ ว่าทำไมถึงเลือกตัวนี้
- ถ้าไม่มี candidate ที่มั่นใจเลย ให้ส่ง array ว่าง []

รูปแบบ JSON:
{"suggestions": {"<external_key>": [{"product_id": 12, "sku": "AP4-ANC", "name": "AirPods 4 ANC", "confidence": 0.93, "reason": "AP4 ANC ตรงกับรหัส SKU"}]}}
"""


def suggest_product_matches(items: list[dict], candidate_products: list[dict]) -> dict:
    """
    Ask Gemini to pre-match unmapped platform items to internal products.

    items: [{"external_key": str, "item_name": str}, ...]
    candidate_products: [{"id": int, "sku": str, "name": str}, ...]
    Returns: {"suggestions": {external_key: [{"product_id", "sku", "name", "confidence", "reason"}]}, "degraded": False}
    Raises: LLMUnavailable
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise LLMUnavailable("google-genai not installed") from exc

    try:
        client = _get_client()

        candidates_text = "\n".join(
            f'- id={p["id"]} | SKU: {p["sku"]} | ชื่อ: {p["name"]}'
            for p in candidate_products
        )
        items_text = "\n".join(
            f'- external_key="{it["external_key"]}" | ชื่อจากแพลตฟอร์ม: "{it["item_name"]}"'
            for it in items
        )

        user_message = f"รายการสินค้าในระบบ (candidates):\n{candidates_text}\n\nรายการที่ต้องจับคู่:\n{items_text}"

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            config=types.GenerateContentConfig(system_instruction=_SUGGEST_SYSTEM_PROMPT),
            contents=user_message,
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {"suggestions": {}}

        result["degraded"] = False
        return result

    except LLMUnavailable:
        raise
    except Exception as exc:
        log.warning("Gemini suggest_product_matches error: %s", exc)
        raise LLMUnavailable(str(exc)) from exc
