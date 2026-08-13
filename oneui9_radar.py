import os
import json
import hashlib
import feedparser
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

FEEDS = [
    "https://www.sammobile.com/feed/",
    "https://www.androidauthority.com/feed/",
]

STATE_FILE = "seen.json"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=20,
    )


def main():
    seen = set()

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            seen = set(json.load(f))

    new_items = []

    for feed_url in FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")

            text = f"{title} {summary}".lower()

            if "one ui 9" not in text:
                continue

            if "s25" not in text and "samsung" not in text:
                continue

            item_id = hashlib.sha256(link.encode()).hexdigest()

            if item_id in seen:
                continue

            seen.add(item_id)
            new_items.append((title, link))

    for title, link in new_items[:5]:
        send_telegram(
            "🚨 ONE UI 9 RADAR\n\n"
            f"📱 {title}\n\n"
            f"🔗 {link}"
        )

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)


if __name__ == "__main__":
    main()
