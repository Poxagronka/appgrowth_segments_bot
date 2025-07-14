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

# ───────── создание сегмента (ИСПРАВЛЕНО) ─────────
def create_segment(
    name: str,
    title: str,
    app: str,
    country: str,
    value: float = 0.95,
    seg_type: str = "ActiveUsers",
) -> bool:
    """
    Создает сегмент в AppGrowth
    
    Args:
        name: Имя сегмента
        title: Заголовок
        app: ID приложения  
        country: Код страны (USA, THA, etc.)
        value: Значение - для ActiveUsers: ratio (0.95), для RetainedAtLeast: дни (30)
        seg_type: Тип сегмента ("ActiveUsers" или "RetainedAtLeast")
    """
    print(f"🎯 Creating segment: {name}, type: {seg_type}, value: {value}")
    
    try:
        # 1) GET /segments/new  → CSRF (fresh token for each request)
        r = SESSION.get(f"{BASE}/segments/new", timeout=10)
        r.raise_for_status()
        csrf = _find_csrf(r.text)
        if not csrf:
            print("❌ CSRF token not found")
            return False

        # 2) Подготовка options в зависимости от типа сегмента
        if seg_type == "RetainedAtLeast":
            # Для RetainedAtLeast используем "age" (количество дней)
            options = {
                "age": str(int(value)),
                "app": app,
                "flavor": "uid",
                "country": country,
            }
        else:  # ActiveUsers
            # Для ActiveUsers используем "audience" (соотношение)
            options = {
                "app": app,
                "flavor": "uid", 
                "country": country,
                "audience": f"{value:.2f}",
            }
        
        print(f"🔧 Options: {options}")

        # 3) payload
        payload = {
            "csrf_token": csrf,
            "name": name,
            "title": title,
            "type": seg_type,
            "options": json.dumps(options),
        }
        
        print(f"📤 Payload: {payload}")

        # 4) POST /segments/
        res = SESSION.post(
            f"{BASE}/segments/",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
            timeout=15,
        )
        
        success = res.status_code == 302
        print(f"📊 Response status: {res.status_code}, success: {success}")
        
        if not success:
            # Check if it's a duplicate/existing segment error
            if res.status_code == 500:
                response_text = res.text[:500]
                if "already exists" in response_text.lower() or "duplicate" in response_text.lower():
                    print(f"⚠️ Segment may already exist")
                else:
                    print(f"❌ Server error: {response_text}")
            else:
                print(f"❌ Response ({res.status_code}): {res.text[:500]}...")
        
        return success
        
    except Exception as e:
        print(f"❌ Exception in create_segment: {e}")
        return False