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
    
    logger.info(f"📨 Received command: {command}")
    
    # Step 1: IMMEDIATELY acknowledge
    ack()
    logger.info("✅ Command acknowledged")
    
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
            logger.info("✅ Ping response sent")
            return
        
        if not text:  # Main menu
            logger.info("📋 Sending main menu")
            respond({
                "response_type": "ephemeral",
                "text": "🎯 AppGrowth Bot",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*🎯 AppGrowth Bot*\n\nCreate segments for your apps:"}
                    },
                    {
                        "type": "actions", 
                        "elements": [
                            {
                                "type": "button", 
                                "text": {"type": "plain_text", "text": "📊 Create Segments"}, 
                                "action_id": "create_segments_btn",
                                "style": "primary"
                            }
                        ]
                    }
                ]
            })
            logger.info("✅ Main menu sent")
            return
        
        # Unknown command
        respond({
            "response_type": "ephemeral",
            "text": f"Unknown: `{text}`. Use `/appgrowth` or `/appgrowth ping`"
        })
        logger.info("✅ Unknown command response sent")
        
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
        logger.error(f"❌ Create segments modal error: {e}")

# Handle form inputs (to prevent warnings)
@bolt_app.action(re.compile("app_id_input|countries_input|segment_types_input"))
def handle_form_inputs(ack, body):
    ack()
    # Just acknowledge, no special handling needed

# Modal submission handler
@bolt_app.view("create_segments_modal")
def handle_create_segments_modal(ack, body, client):
    logger.info("🔥 Create segments modal submission")
    
    try:
        values = body["view"]["state"]["values"]
        
        app_id = values.get("app_id_block", {}).get("app_id_input", {}).get("value", "").strip()
        countries_data = values.get("countries_block", {}).get("countries_input", {})
        countries = [opt["value"] for opt in countries_data.get("selected_options", [])]
        segment_types_data = values.get("segment_types_block", {}).get("segment_types_input", {})
        segment_types = [opt["value"] for opt in segment_types_data.get("selected_options", [])]
        
        logger.info(f"📱 Create segments: app='{app_id}', countries={len(countries)}, types={len(segment_types)}")
        
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
        
        def create_segments_task():
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
                            
                            logger.info(f"🎯 Creating: {name}")
                            
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
                                logger.info(f"✅ Created: {name}")
                            else:
                                failed += 1
                                logger.error(f"❌ Failed: {name}")
                                
                        except Exception as e:
                            failed += 1
                            logger.error(f"❌ Error: {e}")
                        
                        time.sleep(0.5)
                
                msg = f"✅ Done: {created} created, {failed} failed"
                client.chat_postEphemeral(channel=channel_id, user=user_id, text=msg)
                logger.info(f"✅ Segments creation completed: {msg}")
                
            except Exception as e:
                logger.error(f"❌ Create segments task error: {e}")
        
        thread = threading.Thread(target=create_segments_task, daemon=True)
        thread.start()
        
    except Exception as e:
        logger.error(f"❌ Multiple modal error: {e}")
        ack()

# Flask app setup
logger.info("🌐 Setting up Flask app...")
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@flask_app.route("/", methods=["GET"])
def home():
    return {"status": "AppGrowth Bot is running", "auth": auth_logged_in, "time": time.time()}

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    logger.info("📨 Slack event received")
    try:
        return handler.handle(request)
    except Exception as e:
        logger.error(f"❌ Event handling error: {e}")
        return {"error": str(e)}, 500

# Additional routes for debugging
@flask_app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    logger.info("📨 Slack interactive event received")
    try:
        return handler.handle(request)
    except Exception as e:
        logger.error(f"❌ Interactive handling error: {e}")
        return {"error": str(e)}, 500

@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    logger.info("📨 Slack command received")
    try:
        return handler.handle(request)
    except Exception as e:
        logger.error(f"❌ Command handling error: {e}")
        return {"error": str(e)}, 500

@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "auth": auth_logged_in}

# Catch-all route for debugging
@flask_app.route("/<path:path>", methods=["GET", "POST"])
def catch_all(path):
    logger.warning(f"🔍 Unhandled request to /{path}")
    logger.warning(f"🔍 Method: {request.method}")
    logger.warning(f"🔍 Headers: {dict(request.headers)}")
    return {"error": f"Path /{path} not found", "method": request.method}, 404

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