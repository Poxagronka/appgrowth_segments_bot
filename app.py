# app.py — Ultra-simple Slack bot for AppGrowth (Fixed duplicates & timeouts)
import os
import re
import logging
import threading
import time
from dotenv import load_dotenv
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

import appgrowth

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

# Check tokens
if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
    logger.error("❌ Missing Slack tokens!")
    exit(1)

logger.info(f"🔑 Token: {SLACK_BOT_TOKEN[:10]}... Secret: {SLACK_SIGNING_SECRET[:10]}...")

# Countries
POPULAR_COUNTRIES = [
    {"text": {"type": "plain_text", "text": "🇺🇸 USA"}, "value": "USA"},
    {"text": {"type": "plain_text", "text": "🇹🇭 THA"}, "value": "THA"},
    {"text": {"type": "plain_text", "text": "🇳🇱 NLD"}, "value": "NLD"},
    {"text": {"type": "plain_text", "text": "🇩🇪 DEU"}, "value": "DEU"},
    {"text": {"type": "plain_text", "text": "🇫🇷 FRA"}, "value": "FRA"},
    {"text": {"type": "plain_text", "text": "🇬🇧 GBR"}, "value": "GBR"},
    {"text": {"type": "plain_text", "text": "🇯🇵 JPN"}, "value": "JPN"},
    {"text": {"type": "plain_text", "text": "🇰🇷 KOR"}, "value": "KOR"},
    {"text": {"type": "plain_text", "text": "🇧🇷 BRA"}, "value": "BRA"},
    {"text": {"type": "plain_text", "text": "🇮🇳 IND"}, "value": "IND"},
    {"text": {"type": "plain_text", "text": "🇨🇦 CAN"}, "value": "CAN"},
    {"text": {"type": "plain_text", "text": "🇦🇺 AUS"}, "value": "AUS"}
]

# Segment types - only 5 options
SEGMENT_TYPES = [
    {"text": {"type": "plain_text", "text": "⏱️ Retained 1 day"}, "value": "RetainedAtLeast_1"},
    {"text": {"type": "plain_text", "text": "⏱️ Retained 7 days"}, "value": "RetainedAtLeast_7"},
    {"text": {"type": "plain_text", "text": "⏱️ Retained 30 days"}, "value": "RetainedAtLeast_30"},
    {"text": {"type": "plain_text", "text": "👥 Active Users 80%"}, "value": "ActiveUsers_0.80"},
    {"text": {"type": "plain_text", "text": "👥 Active Users 95%"}, "value": "ActiveUsers_0.95"}
]

# Value options for single segment creation
ACTIVE_USERS_VALUES = [
    {"text": {"type": "plain_text", "text": "80% (0.80)"}, "value": "0.80"},
    {"text": {"type": "plain_text", "text": "95% (0.95)"}, "value": "0.95"}
]

RETAINED_VALUES = [
    {"text": {"type": "plain_text", "text": "1 day"}, "value": "1"},
    {"text": {"type": "plain_text", "text": "7 days"}, "value": "7"},
    {"text": {"type": "plain_text", "text": "30 days"}, "value": "30"}
]

# Simple auth
auth_logged_in = False
processed_events = set()  # Prevent duplicate processing

def try_login():
    global auth_logged_in
    try:
        auth_logged_in = appgrowth.login()
        logger.info(f"🔐 Login result: {auth_logged_in}")
        return auth_logged_in
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        auth_logged_in = False
        return False

def generate_segment_name(app_id, country, seg_type, value):
    """Generate segment name with UPPERCASE country code"""
    if seg_type == "RetainedAtLeast":
        code = str(int(value)) + "d"
    else:  # ActiveUsers
        if isinstance(value, str):
            value = float(value)
        code = str(int(value * 100))
    
    # Make country uppercase, keep app_id and code lowercase
    country = country.upper()
    app_id = app_id.lower()
    code = code.lower()
    
    return f"bloom_{app_id}_{country}_{code}"

# Initialize Bolt app with minimal config
bolt_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    process_before_response=True,  # Critical for avoiding timeouts
    logger=logger
)

logger.info("✅ Bolt app initialized with process_before_response=True")

# Command handler - ULTRA SIMPLE
@bolt_app.command("/appgrowth")
def handle_appgrowth_command(ack, respond, command, say):
    """Ultra-simple command handler"""
    
    # Step 1: IMMEDIATELY acknowledge
    ack()
    
    # Step 2: Get event ID to prevent duplicates
    event_id = f"{command.get('trigger_id', '')}{command.get('command_id', '')}"
    if event_id in processed_events:
        logger.warning(f"🔄 Duplicate event ignored: {event_id[:20]}...")
        return
    processed_events.add(event_id)
    
    # Keep only last 100 events in memory
    if len(processed_events) > 100:
        processed_events.clear()
    
    logger.info(f"🎯 Processing command: {command.get('text', '').strip()}")
    
    try:
        text = command.get("text", "").strip()
        
        if text.lower() == 'ping':
            auth_status = "🟢 Connected" if auth_logged_in else "🔴 Disconnected"
            respond(f"🟢 pong! AppGrowth: {auth_status}")
            return
        
        if not text:  # Main menu
            respond({
                "response_type": "ephemeral",
                "text": "🎯 AppGrowth Bot",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*🎯 AppGrowth Bot*\n\nCreate segments:"}
                    },
                    {
                        "type": "actions", 
                        "elements": [
                            {
                                "type": "button", 
                                "text": {"type": "plain_text", "text": "➕ New Segment"}, 
                                "action_id": "new_segment_btn",
                                "style": "primary"
                            },
                            {
                                "type": "button", 
                                "text": {"type": "plain_text", "text": "📊 Multiple Segments"}, 
                                "action_id": "multiple_segments_btn"
                            }
                        ]
                    }
                ]
            })
            return
        
        # Unknown command
        respond({
            "response_type": "ephemeral",
            "text": f"Unknown: `{text}`. Use `/appgrowth` or `/appgrowth ping`"
        })
        
    except Exception as e:
        logger.error(f"❌ Command error: {e}")
        respond({"response_type": "ephemeral", "text": f"Error: {e}"})

# Type change handler for single segment modal
@bolt_app.action("type_select")
def handle_type_change(ack, body, client):
    ack()
    
    logger.info("🔄 Type selection changed")
    
    try:
        view_id = body["view"]["id"]
        selected_type = body["actions"][0]["selected_option"]["value"]
        
        logger.info(f"📊 Selected type: {selected_type}")
        
        # Choose options based on selected type
        if selected_type == "RetainedAtLeast":
            value_options = RETAINED_VALUES
            placeholder = "Select retention days"
        else:  # ActiveUsers
            value_options = ACTIVE_USERS_VALUES  
            placeholder = "Select active users %"
        
        # Update the modal
        updated_view = body["view"]
        updated_view["blocks"][3]["element"]["options"] = value_options
        updated_view["blocks"][3]["element"]["placeholder"]["text"] = placeholder
        # Reset selected value
        if "selected_option" in updated_view["blocks"][3]["element"]:
            del updated_view["blocks"][3]["element"]["selected_option"]
        
        client.views_update(
            view_id=view_id,
            view=updated_view
        )
        
        logger.info("✅ Modal updated with new value options")
        
    except Exception as e:
        logger.error(f"❌ Error updating modal: {e}")

# Handle value selection for single segments
@bolt_app.action("value_select")
def handle_value_select(ack, body):
    ack()
    # Just acknowledge, no special handling needed
@bolt_app.action("new_segment_btn")
def handle_new_segment_button(ack, body, client):
    ack()
    
    logger.info("🎯 New segment button")
    
    try:
        channel_id = body.get("channel", {}).get("id", "unknown")
        trigger_id = body["trigger_id"]
        
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "create_segment_modal",
                "title": {"type": "plain_text", "text": "New Segment"},
                "submit": {"type": "plain_text", "text": "Create"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "private_metadata": channel_id,
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "title_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "title_input",
                            "placeholder": {"type": "plain_text", "text": "com.example.app"}
                        },
                        "label": {"type": "plain_text", "text": "App ID"}
                    },
                    {
                        "type": "input",
                        "block_id": "country_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "country_input",
                            "placeholder": {"type": "plain_text", "text": "Select country"},
                            "options": POPULAR_COUNTRIES
                        },
                        "label": {"type": "plain_text", "text": "Country"}
                    },
                    {
                        "type": "input",
                        "block_id": "type_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "type_select",
                            "placeholder": {"type": "plain_text", "text": "Select type"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "Active Users"}, "value": "ActiveUsers"},
                                {"text": {"type": "plain_text", "text": "Retained Users"}, "value": "RetainedAtLeast"}
                            ]
                        },
                        "label": {"type": "plain_text", "text": "Type"}
                    },
                    {
                        "type": "input",
                        "block_id": "value_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "value_select",
                            "placeholder": {"type": "plain_text", "text": "Select value"},
                            "options": ACTIVE_USERS_VALUES  # Default to ActiveUsers
                        },
                        "label": {"type": "plain_text", "text": "Value"}
                    }
                ]
            }
        )
        logger.info("✅ Modal opened")
        
    except Exception as e:
        logger.error(f"❌ Modal error: {e}")

@bolt_app.action("multiple_segments_btn")
def handle_multiple_segments_button(ack, body, client):
    ack()
    
    logger.info("📊 Multiple segments button")
    
    try:
        channel_id = body.get("channel", {}).get("id", "unknown")
        trigger_id = body["trigger_id"]
        
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "create_multiple_segments_modal",
                "title": {"type": "plain_text", "text": "Multiple Segments"},
                "submit": {"type": "plain_text", "text": "Create All"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "private_metadata": channel_id,
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "app_id_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "app_id_input",
                            "placeholder": {"type": "plain_text", "text": "com.example.app"}
                        },
                        "label": {"type": "plain_text", "text": "App ID"}
                    },
                    {
                        "type": "input",
                        "block_id": "countries_block",
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "countries_input",
                            "placeholder": {"type": "plain_text", "text": "Select countries"},
                            "options": POPULAR_COUNTRIES,
                            "max_selected_items": 5
                        },
                        "label": {"type": "plain_text", "text": "Countries"}
                    },
                    {
                        "type": "input",
                        "block_id": "segment_types_block",
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "segment_types_input",
                            "placeholder": {"type": "plain_text", "text": "Select types"},
                            "options": SEGMENT_TYPES,
                            "max_selected_items": 5
                        },
                        "label": {"type": "plain_text", "text": "Types"}
                    }
                ]
            }
        )
        logger.info("✅ Multiple modal opened")
        
    except Exception as e:
        logger.error(f"❌ Multiple modal error: {e}")

# Modal submission handlers
@bolt_app.view("create_segment_modal")
def handle_segment_modal(ack, body, client):
    logger.info("🔥 Segment modal submission")
    
    try:
        values = body["view"]["state"]["values"]
        
        # Extract values safely
        title = values.get("title_block", {}).get("title_input", {}).get("value", "").strip()
        country_data = values.get("country_block", {}).get("country_input", {})
        country = country_data.get("selected_option", {}).get("value", "")
        seg_type_data = values.get("type_block", {}).get("type_select", {})
        seg_type = seg_type_data.get("selected_option", {}).get("value", "")
        value_data = values.get("value_block", {}).get("value_select", {})
        raw_val = value_data.get("selected_option", {}).get("value", "")
        
        logger.info(f"📱 Modal data: title='{title}', country='{country}', type='{seg_type}', value='{raw_val}'")
        
        # Validation - simplified since values come from select
        errors = {}
        if not title:
            errors["title_block"] = "Required"
        if not country:
            errors["country_block"] = "Required"
        if not seg_type:
            errors["type_block"] = "Required"
        if not raw_val:
            errors["value_block"] = "Required"
        
        if errors:
            logger.warning(f"❌ Validation errors: {errors}")
            ack(response_action="errors", errors=errors)
            return
        
        # Success
        ack()
        logger.info("✅ Modal validated")
        
        # Get metadata
        channel_id = body["view"]["private_metadata"]
        user_id = body["user"]["id"]
        
        # Send immediate response
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="🔄 Creating segment..."
            )
        except Exception as e:
            logger.error(f"❌ Response error: {e}")
        
        # Background task
        def create_task():
            try:
                logger.info("🎯 Background creation started")
                
                # Ensure auth
                if not auth_logged_in:
                    try_login()
                
                if not auth_logged_in:
                    msg = "❌ Authorization failed"
                else:
                    # Prepare
                    if seg_type == "RetainedAtLeast":
                        val = int(raw_val)  # Days for retention
                    else:
                        val = float(raw_val)  # Ratio for active users
                    
                    name = generate_segment_name(title, country, seg_type, val)
                    logger.info(f"🎯 Creating: {name}, type: {seg_type}, value: {val}")
                    
                    # Create segment with detailed logging
                    try:
                        ok = appgrowth.create_segment(
                            name=name,
                            title=title,
                            app=title,
                            country=country,
                            value=val,
                            seg_type=seg_type
                        )
                        logger.info(f"🎯 AppGrowth result: {ok}")
                        
                        if ok:
                            msg = f"✅ Created: `{name}`"
                        else:
                            msg = f"❌ Failed to create `{name}`"
                            
                    except Exception as e:
                        logger.error(f"❌ AppGrowth exception: {e}")
                        msg = f"❌ Error: {e}"
                
                # Send result
                try:
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=msg
                    )
                    logger.info(f"✅ Result sent: {msg[:50]}...")
                except Exception as e:
                    logger.error(f"❌ Failed to send result: {e}")
                
            except Exception as e:
                logger.error(f"❌ Task error: {e}")
        
        # Start background
        thread = threading.Thread(target=create_task, daemon=True)
        thread.start()
        logger.info("🚀 Background thread started")
        
    except Exception as e:
        logger.error(f"❌ Modal handler error: {e}")
        ack()

@bolt_app.view("create_multiple_segments_modal")
def handle_multiple_segments_modal(ack, body, client):
    logger.info("🔥 Multiple segments modal")
    
    try:
        values = body["view"]["state"]["values"]
        
        app_id = values.get("app_id_block", {}).get("app_id_input", {}).get("value", "").strip()
        countries_data = values.get("countries_block", {}).get("countries_input", {})
        countries = [opt["value"] for opt in countries_data.get("selected_options", [])]
        segment_types_data = values.get("segment_types_block", {}).get("segment_types_input", {})
        segment_types = [opt["value"] for opt in segment_types_data.get("selected_options", [])]
        
        logger.info(f"📱 Multiple: app='{app_id}', countries={len(countries)}, types={len(segment_types)}")
        
        # Validation
        errors = {}
        if not app_id:
            errors["app_id_block"] = "Required"
        if not countries:
            errors["countries_block"] = "Select countries"
        if not segment_types:
            errors["segment_types_block"] = "Select types"
        
        if errors:
            ack(response_action="errors", errors=errors)
            return
        
        ack()
        
        channel_id = body["view"]["private_metadata"]
        user_id = body["user"]["id"]
        total = len(countries) * len(segment_types)
        
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"🔄 Creating {total} segments..."
        )
        
        def multiple_task():
            try:
                if not auth_logged_in:
                    try_login()
                
                if not auth_logged_in:
                    client.chat_postEphemeral(channel=channel_id, user=user_id, text="❌ Auth failed")
                    return
                
                created = 0
                failed = 0
                
                for country in countries:
                    for seg_type_value in segment_types:
                        try:
                            seg_type, value = seg_type_value.split("_")
                            name = generate_segment_name(app_id, country, seg_type, value)
                            
                            if seg_type == "RetainedAtLeast":
                                val = int(value)  # Days
                            else:
                                val = float(value)  # Ratio
                            
                            logger.info(f"🎯 Multiple creating: {name}")
                            
                            ok = appgrowth.create_segment(
                                name=name,
                                title=app_id,
                                app=app_id,
                                country=country,
                                value=val,
                                seg_type=seg_type
                            )
                            
                            if ok:
                                created += 1
                                logger.info(f"✅ Multiple success: {name}")
                            else:
                                failed += 1
                                logger.error(f"❌ Multiple failed: {name}")
                                
                        except Exception as e:
                            failed += 1
                            logger.error(f"❌ Multiple error: {e}")
                        
                        time.sleep(0.5)
                
                msg = f"✅ Done: {created} created, {failed} failed"
                client.chat_postEphemeral(channel=channel_id, user=user_id, text=msg)
                logger.info(f"✅ Multiple completed: {msg}")
                
            except Exception as e:
                logger.error(f"❌ Multiple task error: {e}")
        
        thread = threading.Thread(target=multiple_task, daemon=True)
        thread.start()
        
    except Exception as e:
        logger.error(f"❌ Multiple modal error: {e}")
        ack()

# Flask setup
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@flask_app.route("/", methods=["GET"])
def home():
    return {"status": "running", "auth": auth_logged_in, "time": time.time()}

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    logger.info("📨 Slack event received")
    return handler.handle(request)

@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "auth": auth_logged_in}

# Background login
def background_login():
    time.sleep(3)
    try_login()

if __name__ == "__main__":
    # Start login
    login_thread = threading.Thread(target=background_login, daemon=True)
    login_thread.start()
    
    # Start app
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting on port {port}")
    
    flask_app.run(
        host="0.0.0.0", 
        port=port, 
        debug=False,
        threaded=True  # Important for concurrent requests
    )