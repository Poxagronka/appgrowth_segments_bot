# app.py — Slack-бот для работы с AppGrowth (улучшенная версия)
import os
import re
import logging
from dotenv import load_dotenv
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

import appgrowth

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

# Популярные App ID для автокомплита
POPULAR_APP_IDS = [
    "com.easybrain.number.puzzle.game",
    "com.pixel.art.coloring.color.number", 
    "com.king.candycrushsaga",
    "com.supercell.clashofclans",
    "com.tencent.ig",
    "com.facebook.katana",
    "com.whatsapp",
    "com.instagram.android",
    "com.spotify.music",
    "com.netflix.mediaclient",
    "com.google.android.apps.maps",
    "com.twitter.android",
    "com.skype.raider",
    "com.viber.voip",
    "com.snapchat.android"
]

# Популярные страны с кодами
POPULAR_COUNTRIES = [
    {"text": {"type": "plain_text", "text": "🇺🇸 USA - Соединенные Штаты"}, "value": "USA"},
    {"text": {"type": "plain_text", "text": "🇹🇭 THA - Таиланд"}, "value": "THA"},
    {"text": {"type": "plain_text", "text": "🇳🇱 NLD - Нидерланды"}, "value": "NLD"},
    {"text": {"type": "plain_text", "text": "🇩🇪 DEU - Германия"}, "value": "DEU"},
    {"text": {"type": "plain_text", "text": "🇫🇷 FRA - Франция"}, "value": "FRA"},
    {"text": {"type": "plain_text", "text": "🇬🇧 GBR - Великобритания"}, "value": "GBR"},
    {"text": {"type": "plain_text", "text": "🇯🇵 JPN - Япония"}, "value": "JPN"},
    {"text": {"type": "plain_text", "text": "🇰🇷 KOR - Корея"}, "value": "KOR"},
    {"text": {"type": "plain_text", "text": "🇧🇷 BRA - Бразилия"}, "value": "BRA"},
    {"text": {"type": "plain_text", "text": "🇮🇳 IND - Индия"}, "value": "IND"},
    {"text": {"type": "plain_text", "text": "🇨🇦 CAN - Канада"}, "value": "CAN"},
    {"text": {"type": "plain_text", "text": "🇦🇺 AUS - Австралия"}, "value": "AUS"},
    {"text": {"type": "plain_text", "text": "🇲🇽 MEX - Мексика"}, "value": "MEX"},
    {"text": {"type": "plain_text", "text": "🇪🇸 ESP - Испания"}, "value": "ESP"},
    {"text": {"type": "plain_text", "text": "🇮🇹 ITA - Италия"}, "value": "ITA"}
]

# Инициализация Bolt-приложения
bolt_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    logger=logger,
)

# Авторизация в AppGrowth при старте
if not appgrowth.login():
    logger.critical("Не удалось авторизоваться в AppGrowth — выходим")
    raise RuntimeError("AppGrowth auth failed :(")

# Обработчик «/appgrowth» — главное меню
@bolt_app.command("/appgrowth")
def handle_appgrowth(ack, respond, command):
    ack()
    text = command.get("text", "").strip()
    
    if not text:
        # Главная help-карточка только с сегментами
        respond(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn", 
                        "text": "*🎯 Добро пожаловать в AppGrowth Bot!*\n\nИспользуйте бота для создания сегментов в AppGrowth:\n• Быстрое создание через удобную форму\n• Автоматическая генерация имени сегмента\n• Валидация параметров"
                    }
                },
                {
                    "type": "actions", 
                    "elements": [
                        {
                            "type": "button", 
                            "text": {"type": "plain_text", "text": "➕ Новый сегмент"}, 
                            "action_id": "new_segment_btn",
                            "style": "primary"
                        },
                        {
                            "type": "button", 
                            "text": {"type": "plain_text", "text": "📖 Документация"}, 
                            "url": "https://docs.appgrowth.com"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 *Совет:* Используйте `/appgrowth ping` для проверки статуса бота"
                        }
                    ]
                }
            ]
        )
        return
    
    if text.lower() == 'ping':
        respond(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🟢 *pong!* Бот работает нормально ✨"
                    }
                }
            ]
        )
        return
    
    # Для любых других команд
    respond(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🤖 Неизвестная команда: `{text}`\n\nИспользуйте:\n• `/appgrowth` - главное меню\n• `/appgrowth ping` - проверка статуса"
                }
            }
        ]
    )

# Обработчик кнопки «Новый сегмент»
@bolt_app.action("new_segment_btn")
def open_segment_modal(ack, body, client):
    ack()
    trigger_id = body["trigger_id"]
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "create_segment_modal",
            "title": {"type": "plain_text", "text": "🎯 Новый сегмент"},
            "submit": {"type": "plain_text", "text": "Создать"},
            "close": {"type": "plain_text", "text": "Отмена"},
            "private_metadata": body["channel_id"],
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn", 
                        "text": "*Создание нового сегмента в AppGrowth*\nЗаполните параметры для генерации сегмента:"
                    }
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "title_block",
                    "element": {
                        "type": "external_select",
                        "action_id": "title_input",
                        "placeholder": {"type": "plain_text", "text": "Выберите или введите App ID"},
                        "min_query_length": 3
                    },
                    "label": {"type": "plain_text", "text": "📱 App ID"},
                    "hint": {"type": "plain_text", "text": "Bundle ID приложения, например com.easybrain.number.puzzle.game"}
                },
                {
                    "type": "input",
                    "block_id": "country_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "country_input",
                        "placeholder": {"type": "plain_text", "text": "Выберите страну"},
                        "options": POPULAR_COUNTRIES
                    },
                    "label": {"type": "plain_text", "text": "🌍 Страна"},
                    "hint": {"type": "plain_text", "text": "Код страны из 3 букв для таргетинга"}
                },
                {
                    "type": "input",
                    "block_id": "type_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "type_select",
                        "placeholder": {"type": "plain_text", "text": "Выберите тип сегмента"},
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "⏱️ RetainedAtLeast - Удержание пользователей"}, 
                                "value": "RetainedAtLeast"
                            },
                            {
                                "text": {"type": "plain_text", "text": "👥 ActiveUsers - Активные пользователи"}, 
                                "value": "ActiveUsers"
                            }
                        ]
                    },
                    "label": {"type": "plain_text", "text": "📊 Тип сегмента"}
                },
                {
                    "type": "input",
                    "block_id": "value_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "value_input",
                        "placeholder": {"type": "plain_text", "text": "Введите значение"}
                    },
                    "label": {"type": "plain_text", "text": "🎯 Значение"},
                    "hint": {"type": "plain_text", "text": "Для RetainedAtLeast: число дней (например, 30). Для ActiveUsers: доля от 0 до 1 (например, 0.95)"}
                },
                {
                    "type": "section",
                    "block_id": "preview_block",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Предварительное имя сегмента:*\n`bloom_[app-id]_[country]_[value]`"
                    }
                }
            ]
        }
    )

# Обработчик автокомплита для App ID
@bolt_app.options("title_input")
def handle_app_id_options(ack, body):
    query = body.get("value", "").lower()
    
    # Фильтруем популярные App ID по запросу
    filtered_options = []
    for app_id in POPULAR_APP_IDS:
        if query in app_id.lower():
            filtered_options.append({
                "text": {"type": "plain_text", "text": app_id},
                "value": app_id
            })
    
    # Добавляем возможность создать новый App ID если его нет в списке
    if query and len(query) > 5 and not any(query in app.lower() for app in POPULAR_APP_IDS):
        filtered_options.insert(0, {
            "text": {"type": "plain_text", "text": f"📝 Использовать: {query}"},
            "value": query
        })
    
    ack(options=filtered_options[:10])  # Максимум 10 опций

# Обработчик изменений в модалке для динамического preview
@bolt_app.action("type_select")
def handle_type_change(ack, body, client):
    ack()
    
    # Получаем текущие значения
    view_id = body["view"]["id"]
    selected_type = body["actions"][0]["selected_option"]["value"]
    
    # Обновляем hint для поля значения в зависимости от типа
    value_hint = {
        "RetainedAtLeast": "Число дней удержания (например, 7, 14, 30)",
        "ActiveUsers": "Доля активных пользователей от 0 до 1 (например, 0.80, 0.95)"
    }
    
    value_placeholder = {
        "RetainedAtLeast": "30",
        "ActiveUsers": "0.95"
    }
    
    # Обновляем модалку
    updated_view = body["view"]
    updated_view["blocks"][4]["element"]["placeholder"]["text"] = value_placeholder.get(selected_type, "Введите значение")
    updated_view["blocks"][4]["hint"]["text"] = value_hint.get(selected_type, "Введите значение для сегмента")
    
    client.views_update(
        view_id=view_id,
        view=updated_view
    )

# Обработчик изменений в других полях для preview
@bolt_app.action(re.compile("title_input|country_input|value_input"))
def handle_field_changes(ack, body, client):
    ack()
    
    try:
        view_id = body["view"]["id"]
        values = body["view"]["state"]["values"]
        
        # Извлекаем текущие значения
        title = ""
        country = ""
        value = ""
        seg_type = "ActiveUsers"  # default
        
        if "title_block" in values and values["title_block"]["title_input"]["selected_option"]:
            title = values["title_block"]["title_input"]["selected_option"]["value"]
        
        if "country_block" in values and values["country_block"]["country_input"]["selected_option"]:
            country = values["country_block"]["country_input"]["selected_option"]["value"]
            
        if "type_block" in values and values["type_block"]["type_select"]["selected_option"]:
            seg_type = values["type_block"]["type_select"]["selected_option"]["value"]
            
        if "value_block" in values and values["value_block"]["value_input"]["value"]:
            value = values["value_block"]["value_input"]["value"]
        
        # Генерируем preview имени
        if title and country and value:
            try:
                if seg_type == "RetainedAtLeast" and value.isdigit():
                    code = value
                elif seg_type == "ActiveUsers":
                    code = value.split('.')[-1] if '.' in value else value
                else:
                    code = value
                    
                preview_name = f"bloom_{title}_{country}_{code}".lower()
                preview_text = f"*Предварительное имя сегмента:*\n`{preview_name}`"
            except:
                preview_text = "*Предварительное имя сегмента:*\n`Заполните все поля для preview`"
        else:
            preview_text = "*Предварительное имя сегмента:*\n`Заполните все поля для preview`"
        
        # Обновляем preview блок
        updated_view = body["view"]
        updated_view["blocks"][5]["text"]["text"] = preview_text
        
        client.views_update(
            view_id=view_id,
            view=updated_view
        )
    except Exception as e:
        logger.warning(f"Error updating preview: {e}")

# Обработчик сабмита модалки
@bolt_app.view("create_segment_modal")
def handle_segment_submission(ack, body, client):
    values = body["view"]["state"]["values"]
    
    # Извлекаем значения
    title_data = values["title_block"]["title_input"]
    title = title_data.get("selected_option", {}).get("value", "").strip() if title_data.get("selected_option") else ""
    
    country_data = values["country_block"]["country_input"]
    country = country_data.get("selected_option", {}).get("value", "").strip() if country_data.get("selected_option") else ""
    
    seg_type_data = values["type_block"]["type_select"]
    seg_type = seg_type_data.get("selected_option", {}).get("value", "") if seg_type_data.get("selected_option") else ""
    
    raw_val = values["value_block"]["value_input"]["value"].strip() if values["value_block"]["value_input"]["value"] else ""
    
    # Валидация
    errors = {}
    
    if not title:
        errors["title_block"] = "Выберите App ID"
    
    if not country:
        errors["country_block"] = "Выберите страну"
        
    if not seg_type:
        errors["type_block"] = "Выберите тип сегмента"
    
    if not raw_val:
        errors["value_block"] = "Введите значение"
    else:
        if seg_type == "RetainedAtLeast":
            if not raw_val.isdigit():
                errors["value_block"] = "Введите число дней (например, 7, 14, 30)"
            else:
                val = int(raw_val)
                if val <= 0 or val > 365:
                    errors["value_block"] = "Число дней должно быть от 1 до 365"
        elif seg_type == "ActiveUsers":
            try:
                val = float(raw_val)
                if val <= 0 or val > 1:
                    errors["value_block"] = "Доля должна быть от 0.01 до 1.0"
            except ValueError:
                errors["value_block"] = "Введите долю (например, 0.80, 0.95)"
    
    if errors:
        ack(response_action="errors", errors=errors)
        return
    
    ack()
    
    # Генерируем имя сегмента
    try:
        if seg_type == "RetainedAtLeast":
            val = int(raw_val)
            code = str(val)
        else:
            val = float(raw_val)
            code = raw_val.split('.')[-1] if '.' in raw_val else raw_val
            
        name = f"bloom_{title}_{country}_{code}".lower()
        
        # Создаем сегмент
        ok = appgrowth.create_segment(
            name=name,
            title=title,
            app=title,
            country=country,
            audience=val if seg_type == "ActiveUsers" else None,
            seg_type=seg_type
        )
        
        if ok:
            msg = f"✅ *Сегмент успешно создан!*\n🎯 Имя: `{name}`\n📱 App: `{title}`\n🌍 Страна: `{country}`\n📊 Тип: `{seg_type}`\n🎯 Значение: `{raw_val}`"
        else:
            msg = f"❌ *Не удалось создать сегмент*\n🔧 Проверьте параметры и попробуйте снова"
            
    except Exception as e:
        logger.error(f"Error creating segment: {e}")
        msg = f"❌ *Ошибка при создании:* {e}"
    
    user = body["user"]["id"]
    client.chat_postEphemeral(
        channel=body["view"]["private_metadata"], 
        user=user, 
        text=msg,
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": msg}
            }
        ]
    )

# Flask обёртка
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)