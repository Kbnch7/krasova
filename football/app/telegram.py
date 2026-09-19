import json
import urllib.error
import urllib.request

from app.config import TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID, сообщение не отправлено", flush=True)
        return False

    request = urllib.request.Request(
        f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return bool(json.load(response).get("ok"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"[telegram] не удалось отправить сообщение: {exc}", flush=True)
        return False
