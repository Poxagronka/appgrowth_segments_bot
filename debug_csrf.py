import appgrowth, sys, re, textwrap, html

# 1️⃣ Авторизация (как обычно)
if not appgrowth.login():
    sys.exit("login failed")

# 2️⃣ Тянем HTML страницы /segments/
raw = appgrowth.SESSION.get(f"{appgrowth.BASE}/segments/", timeout=10).text
print("⬇️  HTML length:", len(raw))

# 3️⃣ Ищем ВСЕ вхождения 'csrf' (регистр не важен)
hits = list(re.finditer(r"csrf", raw, re.I))
if not hits:
    print("⚠️  Строк 'csrf' не найдено. Сохраняю первую 20k символов в segments.html")
    with open("segments.html", "w", encoding="utf-8") as f:
        f.write(raw[:20000])
    sys.exit()

# 4️⃣ Покажем по 60 символов вокруг каждой находки
print(f"🔍 Найдено {len(hits)} вхождений 'csrf':\n")
for m in hits[:10]:                # первые 10, обычно хватает
    start = max(m.start() - 40, 0)
    fragment = raw[start : m.start() + 60]
    fragment = fragment.replace("\n", " ")
    print("...", html.escape(fragment), "...")
