# appgrowth.py
# Логин в AppGrowth, чтение кампаний, создание сегментов (Python-3.9 совместим)
# Зависимости:  pip install requests beautifulsoup4 python-dotenv
import os, time, json, re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ───────── конфиг ─────────
load_dotenv()
BASE = os.getenv("APPGROWTH_BASE_URL", "https://app.appgrowth.com")
USER = os.getenv("APPGROWTH_USERNAME")
PW   = os.getenv("APPGROWTH_PASSWORD")

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (AppGrowthBot)",
        "Accept": "text/html,application/json",
    }
)

# ───────── авторизация ─────────
def login(max_attempts: int = 3) -> bool:
    for attempt in range(1, max_attempts + 1):
        try:
            r = SESSION.get(f"{BASE}/auth/", timeout=10)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            token = soup.find("input", attrs={"name": "csrf_token"})
            if not token:
                raise ValueError("CSRF not found on /auth/")
            csrf = token["value"]

            payload = {
                "csrf_token": csrf,
                "username": USER,
                "password": PW,
                "remember": "y",
            }
            res = SESSION.post(
                f"{BASE}/auth/",
                data=payload,
                allow_redirects=False,
                timeout=10,
            )
            if res.status_code == 302:
                print("✅  AppGrowth login OK")
                return True
            print(f"⚠️  Login status {res.status_code}")
        except Exception as e:
            print(f"❌  Attempt {attempt}: {e}")
            time.sleep(3 * attempt)
    return False

# ───────── кампании (пример) ─────────
def get_campaign_page(campaign_id: str) -> str:
    r = SESSION.get(f"{BASE}/campaigns/{campaign_id}", timeout=15)
    r.raise_for_status()
    return r.text

def parse_campaign_info(html: str) -> dict:
    m = re.search(r"window\.__DATA__\s*=\s*({.+?});", html, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
        camp = data.get("campaigns", [])[0]
        return {
            "id": camp.get("id"),
            "title": camp.get("title"),
            "status": camp.get("status") or camp.get("paused_reason"),
            "out_of_budget": camp.get("out_of_budget", False),
        }
    except Exception:
        return {}

# ───────── CSRF утилита (новая regex) ─────────
def _find_csrf(html: str) -> Optional[str]:
    """
    Ищет <input ... name="csrf_token" ... value="..."> в любом порядке атрибутов.
    """
    m = re.search(
        r'<input[^>]*name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    return m.group(1) if m else None

# ───────── создание сегмента ─────────
def create_segment(
    name: str,
    title: str,
    app: str,
    country: str,
    audience: float = 0.95,
    seg_type: str = "ActiveUsers",
) -> bool:
    # 1) GET /segments/new  → CSRF
    r = SESSION.get(f"{BASE}/segments/new", timeout=10)
    r.raise_for_status()
    csrf = _find_csrf(r.text)
    if not csrf:
        raise RuntimeError("CSRF token не найден на /segments/new")

    # 2) payload
    payload = {
        "csrf_token": csrf,
        "name": name,
        "title": title,
        "type": seg_type,
        "options": json.dumps(
            {
                "app": app,
                "flavor": "uid",
                "country": country,
                "audience": f"{audience:.2f}",
            }
        ),
    }

    # 3) POST /segments/
    res = SESSION.post(
        f"{BASE}/segments/",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=False,
        timeout=15,
    )
    return res.status_code == 302
