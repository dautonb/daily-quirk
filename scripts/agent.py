"""
Daily Quirk Agent
- Chọn 1 chủ đề kỳ quặc mới (không lặp lại)
- Dùng Orthogonal API để research 2-3 nguồn + viết bài
- Gửi Markdown lên Telegram
"""

import os, re, sys, json, html as htmllib
from datetime import datetime, timezone
from pathlib import Path
import requests

HERE = Path(__file__).parent
HISTORY_FILE = HERE.parent / "data" / "history.json"

ORTHO_KEY   = os.environ["ORTHOGONAL_API_KEY"]
ORTHO_BASE  = os.environ.get("ORTHOGONAL_BASE",  "https://api.orthogonal.com/v1")
ORTHO_MODEL = os.environ.get("ORTHOGONAL_MODEL", "orthogonal-1")

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT  = os.environ["TELEGRAM_CHAT_ID"]

# ---------------------------------------------------------------------------
PROMPT_PICK = """You are a curious writer hunting for quirky topics for a daily Internet column.

Pick ONE specific, verifiable quirky topic — real, with real sources on the open web. Avoid generic topics.

Style inspiration:
- "Why would someone pay real money for virtual land?"
- "A website that lived 20 years nobody knew about"
- "A technology declared dead that came back"

Recent topics to AVOID (do not repeat or paraphrase):
{history}

Respond in JSON ONLY:
{{"topic":"short title (max 10 words)","search_query":"query to find sources","angle":"one sentence why it's interesting"}}"""

PROMPT_ARTICLE = """You are writing a short Markdown article for a Telegram channel.

Topic: {topic}
Angle: {angle}

Steps:
1. Use web search / your knowledge to trace 2–3 reliable sources.
2. Verify facts. Prefer primary sources, technical blogs, archives, Wikipedia.
3. Write a concise Markdown article in Vietnamese, 250–400 words.

Structure:
**{topic}**

*Chuyện gì xảy ra* — 2–3 câu factual.

*Điều gì thú vị* — 3–5 câu về twist / tại sao đáng quan tâm.

*Đọc tiếp* — bullet list 2–3 nguồn: tiêu đề + URL + 1 dòng lý do.

Rules:
- Không sáo rỗng, không "trong bài viết này".
- URL phải thật, đang tồn tại.
- Nếu nguồn không chắc, bỏ.
- Chỉ trả về Markdown, không gì khác."""

# ---------------------------------------------------------------------------
def call_ortho(messages, temperature=0.7, max_tokens=1500):
    url = f"{ORTHO_BASE.rstrip('/')}/chat/completions"
    r = requests.post(
        url,
        json={
            "model": ORTHO_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        headers={
            "Authorization": f"Bearer {ORTHO_KEY}",
            "Content-Type": "application/json",
        },
        timeout=180,
    )
    if not r.ok:
        print("Orthogonal error:", r.status_code, r.text[:600], file=sys.stderr)
        r.raise_for_status()
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        for k in ("output", "text", "result", "content"):
            if k in data and isinstance(data[k], str):
                return data[k]
        raise RuntimeError(f"Unknown response shape: {json.dumps(data)[:500]}")

def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []

def save_history(h):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2))

def pick_topic(history):
    hist = "\n".join(f"- {t}" for t in history[-30:]) or "(none)"
    raw = call_ortho(
        [{"role": "user", "content": PROMPT_PICK.format(history=hist)}],
        temperature=0.9, max_tokens=400,
    )
    s, e = raw.find("{"), raw.rfind("}")
    if s == -1 or e == -1:
        raise RuntimeError(f"No JSON in topic response: {raw[:300]}")
    return json.loads(raw[s:e + 1])

def write_article(info):
    return call_ortho(
        [{"role": "user", "content":
          PROMPT_ARTICLE.format(topic=info["topic"], angle=info["angle"])}],
        temperature=0.6, max_tokens=1800,
    ).strip()

def md_to_tg_html(md: str) -> str:
    t = htmllib.escape(md)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", t, flags=re.M)
    return t

def tg_send(md: str):
    text = md_to_tg_html(md)
    if len(text) > 4000:
        text = text[:4000] + "\n\n…(còn nữa)"
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={
            "chat_id": TG_CHAT,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=60,
    )
    if not r.ok:
        print("Telegram error:", r.status_code, r.text[:600], file=sys.stderr)
        r.raise_for_status()

def main():
    history = load_history()
    print("Picking topic…")
    info = pick_topic(history)
    print("Topic:", info["topic"])

    print("Writing article…")
    article = write_article(info)
    print("---ARTICLE---\n" + article + "\n---END---")

    header = f"🗓 <b>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</b>\n\n"
    tg_send(header + article)

    history.append(info["topic"])
    save_history(history)
    print("Done.")

if __name__ == "__main__":
    main()
