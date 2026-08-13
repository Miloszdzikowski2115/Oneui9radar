import os
import json
import hashlib
import re
import feedparser
import requests
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "seen.json"

FEEDS = {
    "SamMobile": "https://www.sammobile.com/feed/",
    "Android Authority": "https://www.androidauthority.com/feed/",
}

SAMSUNG_S938B_URL = (
    "https://doc.samsungmobile.com/SM-S938B/032404250224/eng.html"
)

KEYWORDS = [
    "one ui 9",
    "oneui 9",
    "android 17",
    "s25 ultra",
    "galaxy s25",
    "s938b",
]

BUILD_PATTERN = r"S938B[A-Z0-9]{8,}"


def load_seen():
    if not os.path.exists(STATE_FILE):
        return set()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-1000:], f)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    response.raise_for_status()


def get_builds(text):
    return sorted(set(re.findall(BUILD_PATTERN, text.upper())))


def classify(title, text):
    content = f"{title} {text}".lower()

    if "one ui 9" in content or "oneui 9" in content:
        if "beta" in content:
            return "🧪 ONE UI 9 BETA"
        return "🚨 ONE UI 9"

    if "android 17" in content:
        return "🤖 ANDROID 17"

    if "s938b" in content:
        return "📦 S25 ULTRA BUILD"

    return None


def scan_rss(seen):
    alerts = []

    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:30]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")

                if not title or not link:
                    continue

                content = f"{title} {summary}".lower()

                if not any(keyword in content for keyword in KEYWORDS):
                    continue

                category = classify(title, summary)

                if not category:
                    continue

                item_id = hashlib.sha256(
                    link.encode("utf-8")
                ).hexdigest()

                if item_id in seen:
                    continue

                seen.add(item_id)

                builds = get_builds(f"{title} {summary}")

                alerts.append({
                    "category": category,
                    "source": source,
                    "title": title,
                    "link": link,
                    "builds": builds,
                })

        except Exception as e:
            print(f"RSS error [{source}]: {e}")

    return alerts


def scan_samsung(seen):
    alerts = []

    try:
        response = requests.get(
            SAMSUNG_S938B_URL,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 OneUI9Radar"
            },
        )

        response.raise_for_status()

        text = response.text

        builds = get_builds(text)

        for build in builds:
            item_id = hashlib.sha256(
                f"samsung:{build}".encode("utf-8")
            ).hexdigest()

            if item_id in seen:
                continue

            seen.add(item_id)

            alerts.append({
                "category": "📦 SAMSUNG S25 ULTRA BUILD",
                "source": "Samsung",
                "title": f"Nowy/wykryty build: {build}",
                "link": SAMSUNG_S938B_URL,
                "builds": [build],
            })

    except Exception as e:
        print(f"Samsung error: {e}")

    return alerts


def format_alert(alert):
    message = (
        f"{alert['category']}\n\n"
        f"📱 {alert['title']}\n"
    )

    if alert["builds"]:
        message += "\n📦 Build:\n"
        for build in alert["builds"]:
            message += f"`{build}`\n"

    message += (
        f"\n🌐 Źródło: {alert['source']}\n"
        f"🔗 {alert['link']}"
    )

    return message


def main():
    seen = load_seen()

    alerts = []

    alerts.extend(scan_rss(seen))
    alerts.extend(scan_samsung(seen))

    print(f"Znaleziono nowych alertów: {len(alerts)}")

    for alert in alerts[:10]:
        try:
            send_telegram(format_alert(alert))
            print(f"Wysłano: {alert['title']}")
        except Exception as e:
            print(f"Telegram error: {e}")

    save_seen(seen)


if __name__ == "__main__":
    main()
