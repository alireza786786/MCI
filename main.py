import os
import re
import base64
import time
import urllib.parse
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_TAG = os.getenv("CHANNEL_TAG", "👉🆔@@Goodbaye_filtering📡⚡️")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def decode_base64_safely(data: str) -> str:
    clean_data = data.strip().replace("\r", "").replace("\n", "")
    missing_padding = len(clean_data) % 4
    if missing_padding:
        clean_data += "=" * (4 - missing_padding)
    try:
        decoded_bytes = base64.b64decode(clean_data)
        return decoded_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def fetch_source_configs(url: str) -> list:
    configs = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[SKIP] Status code {response.status_code} for URL: {url}")
            return configs

        content = response.text.strip()
        if not content:
            return configs

        if not content.startswith("vless://"):
            decoded = decode_base64_safely(content)
            if "vless://" in decoded:
                content = decoded

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("vless://"):
                configs.append(line)

    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] Skipping slow source: {url}")
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Error connecting to {url}: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error parsing {url}: {e}")

    return configs

def filter_and_deduplicate(raw_configs: list) -> list:
    unique_fingerprints = set()
    filtered_list = []

    for cfg in raw_configs:
        try:
            clean_url = cfg.split("#")[0].strip()
            parsed = urllib.parse.urlparse(clean_url)
            queries = urllib.parse.parse_qs(parsed.query)

            security = queries.get("security", [""])[0].lower()
            transport_type = queries.get("type", [""])[0].lower()

            if security == "reality" and transport_type == "grpc":
                server_host = parsed.hostname or ""
                server_port = parsed.port or ""
                sni = queries.get("sni", [""])[0].lower()
                pbk = queries.get("pbk", [""])[0]
                service_name = queries.get("serviceName", [""])[0]

                unique_key = f"{server_host}:{server_port}-{sni}-{pbk}-{service_name}"

                if unique_key not in unique_fingerprints:
                    unique_fingerprints.add(unique_key)
                    encoded_tag = urllib.parse.quote(CHANNEL_TAG)
                    final_config = f"{clean_url}#{encoded_tag}"
                    filtered_list.append(final_config)
        except Exception:
            continue

    return filtered_list

def send_file_to_telegram(configs: list):
    """ذخیره کانفیگ‌ها در یک فایل و ارسال فایل با کپشن جذاب به تلگرام"""
    file_name = "Reality_VIP_Configs.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(configs))

    caption = (
        f"📁 <b>فایل اختصاصی تمام کانفیگ‌های Reality + gRPC</b>\n\n"
        f"⚡️ <b>تعداد کل کانفیگ‌ها:</b> {len(configs)} عدد\n"
        f"🛡 <b>پروتکل:</b> VLESS Reality gRPC (ضد فیلتر)\n"
        f"🕒 <b>زمان بروزرسانی:</b> خودکار هر ۴ ساعت\n\n"
        f"📥 <i>این فایل را در برنامه‌های V2rayNG یا NekoBox ایمپورت کنید.</i>\n\n"
        f"📢 {CHANNEL_TAG}\n"
        f"➖➖➖➖➖➖➖➖➖➖"
    )

    doc_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_name, "rb") as doc:
        requests.post(
            doc_url,
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"document": (file_name, doc, "text/plain")},
            timeout=20
        )

def send_configs_to_telegram(configs: list):
    if not BOT_TOKEN or not CHAT_ID:
        print("[WARN] Telegram BOT_TOKEN or CHAT_ID is missing.")
        return

    if not configs:
        print("[INFO] No Reality+gRPC configs found.")
        return

    # ۱. اول فایل کامل کانفیگ‌ها ارسال می‌شود
    try:
        send_file_to_telegram(configs)
        print("[OK] Configs file sent successfully.")
    except Exception as e:
        print(f"[FAIL] Sending document failed: {e}")

    # ۲. ارسال چند کانفیگ به صورت مستقیم در کانال برای کپی سریع
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    top_samples = configs[:6]  # ارسال ۶ تای اول در متن
    chunk_size = 2

    for i in range(0, len(top_samples), chunk_size):
        chunk = top_samples[i:i + chunk_size]
        message_body = "\n\n".join([f"<code>{c}</code>" for c in chunk])
        payload = {
            "chat_id": CHAT_ID,
            "text": message_body,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            requests.post(api_url, json=payload, timeout=10)
            time.sleep(2)
        except Exception as e:
            print(f"[TELEGRAM FAIL] {e}")

def main():
    if not os.path.exists("sources.txt"):
        print("sources.txt not found!")
        return

    with open("sources.txt", "r", encoding="utf-8") as f:
        sources = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    all_raw_configs = []
    for idx, url in enumerate(sources, 1):
        print(f"[{idx}/{len(sources)}] Fetching from: {url}")
        configs = fetch_source_configs(url)
        all_raw_configs.extend(configs)

    final_configs = filter_and_deduplicate(all_raw_configs)
    print(f"Total Unique VLESS Reality gRPC configs: {len(final_configs)}")
    send_configs_to_telegram(final_configs)

if __name__ == "__main__":
    main()
