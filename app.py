# app.py — Simplified Slack bot for AppGrowth
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

# Check required environment variables
if not SLACK_BOT_TOKEN:
    logger.error("❌ SLACK_BOT_TOKEN not found in environment!")
    exit(1)
if not SLACK_SIGNING_SECRET:
    logger.error("❌ SLACK_SIGNING_SECRET not found in environment!")
    exit(1)

logger.info(f"🔑 Bot token: {SLACK_BOT_TOKEN[:10]}...")
logger.info(f"🔑 Signing secret: {SLACK_SIGNING_SECRET[:10]}...")

# Popular countries with codes
POPULAR_COUNTRIES = [
    {"text": {"type": "plain_text", "text": "🇺🇸 USA - United States"}, "value": "USA"},
    {"text": {"type": "plain_text", "text": "🇹🇭 THA - Thailand"}, "value": "THA"},
    {"text": {"type": "plain_text", "text": "🇳🇱 NLD - Netherlands"}, "value": "NLD"},
    {"text": {"type": "plain_text", "text": "🇩🇪 DEU - Germany"}, "value": "DEU"},
    {"text": {"type": "plain_text", "text": "🇫🇷 FRA - France"}, "value": "FRA"},
    {"text": {"type": "plain_text", "text": "🇬🇧 GBR - United Kingdom"}, "value": "GBR"},
    {"text": {"type": "plain_text", "text": "🇯🇵 JPN - Japan"}, "value": "JPN"},
    {"text": {"type": "plain_text", "text": "🇰🇷 KOR - Korea"}, "value": "KOR"},
    {"text": {"type": "plain_text", "text": "🇧🇷 BRA - Brazil"}, "value": "BRA"},
    {"text": {"type": "plain_text", "text": "🇮🇳 IND - India"}, "value": "IND"},
    {"text": {"type": "plain_text", "text": "🇨🇦 CAN - Canada"}, "value": "CAN"},
    {"text": {"type": "plain_text", "text": "🇦🇺 AUS - Australia"}, "value": "AUS"},
    {"text": {"type": "plain_text", "text": "🇲🇽 MEX - Mexico"}, "value": "MEX"},
    {"text": {"type": "plain_text", "text": "🇪🇸 ESP - Spain"}, "value": "ESP"},
    {"text": {"type": "plain_text", "text": "🇮🇹 ITA - Italy"}, "value": "ITA"}
]

# Segment types for multiple creation
SEGMENT_TYPES = [
    {"text": {"type": "plain_text", "text": "⏱️ Retained 7 days"}, "value": "RetainedAtLeast_7"},
    {"text": {"type": "plain_text", "text": "⏱️ Retained 14 days"}, "value": "RetainedAtLeast_14"},
    {"text": {"type": "plain_text", "text": "⏱️ Retained 30 days"}, "value": "RetainedAtLeast_30"},
    {"text": {"type": "plain_text", "text": "👥 Active Users 60%"}, "value": "ActiveUsers_0.60"},
    {"text": {"type": "plain_text", "text": "👥 Active Users 70%"}, "value": "ActiveUsers_0.70"},
    {"text": {"type": "plain_text", "text": "👥 Active Users 80%"}, "value": "ActiveUsers_0.80"},
    {"text": {"type": "plain_text", "text": "👥 Active Users 90%"}, "value": "ActiveUsers_0.90"},
    {"text": {"type": "plain_text", "text": "👥 Active Users 95%"}, "value": "ActiveUsers_0.95"}
]

# Simple auth status
auth_logged_in = False

def try_login():
    """Simple login function"""
    global auth_logged_in
    try:
        auth_logged_in = appgrowth.login()
        if auth_logged_in:
            logger.info("✅ AppGrowth login successful")
        else:
            logger.error("❌ AppGrowth login failed")
        return auth_logged_in
    except Exception as e:
        logger.error(f"❌ AppGrowth login error: {e}")
        auth_logged_in = False
        return False

def generate_segment_name(app_id, country, seg_type, value):
    """Generate segment name with proper formatting"""
    if seg_type == "RetainedAtLeast":
        code = str(int(value)) + "d"
    else:  # ActiveUsers
        if isinstance(value, str):
            value = float(value)
        code = str(int(value * 100))
    
    country = country.upper()
    return f"bloom_{app_id}_{country}_{code}".lower()

# Initialize Bolt app
logger.info("🚀 Initializing Slack Bolt app...")
bolt_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    logger=logger,
)
logger.info("✅ Bolt app initialized")

# Simple command handler
@bolt_app.command("/appgrowth")
def handle_appgrowth_command(ack, respond, command):
    logger.info("🎯 Received /appgrowth command")
    
    # FIRST: Always acknowledge immediately
    ack()
    logger.info("✅ Command acknowledged")
    
    try:
        text = command.get("text", "").strip()
        logger.info(f"📝 Command text: '{text}'")
        
        if not text:
            logger.info("📋 Showing main menu")
            respond({
                "text": "🎯 AppGrowth Bot Menu",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn", 
                            "text": "*🎯 Welcome to AppGrowth Bot!*\n\nCreate segments in AppGrowth platform:"
                        }
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
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "💡 Use `/appgrowth ping` to check status"
                            }
                        ]
                    }
                ]
            })
            return
        
        if text.lower() == 'ping':
            auth_status = "🟢 Connected" if auth_logged_in else "🔴 Disconnected"
            logger.info(f"📊 Ping - auth status: {auth_status}")
            respond({
                "text": f"🟢 pong! Bot is working.\n📊 AppGrowth Status: {auth_status}"
            })
            return
        
        # Unknown command
        respond({
            "text": f"🤖 Unknown command: `{text}`\n\nUse:\n• `/appgrowth` - main menu\n• `/appgrowth ping` - status check"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in command handler: {e}")
        respond({"text": f"❌ Error: {e}"})

# Button handlers
@bolt_app.action("new_segment_btn")
def handle_new_segment_button(ack, body, client):
    logger.info("🎯 New segment button clicked")
    ack()
    
    try:
        # Get channel ID
        channel_id = body.get("channel", {}).get("id", "unknown")
        trigger_id = body["trigger_id"]
        
        logger.info(f"📍 Channel: {channel_id}, Trigger: {trigger_id}")
        
        # Open modal
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "create_segment_modal",
                "title": {"type": "plain_text", "text": "🎯 New Segment"},
                "submit": {"type": "plain_text", "text": "Create"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "private_metadata": channel_id,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn", 
                            "text": "*Creating a new segment in AppGrowth*"
                        }
                    },
                    {"type": "divider"},
                    {
                        "type": "input",
                        "block_id": "title_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "title_input",
                            "placeholder": {"type": "plain_text", "text": "com.easybrain.number.puzzle.game"}
                        },
                        "label": {"type": "plain_text", "text": "📱 App ID (Bundle ID)"}
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
                        "label": {"type": "plain_text", "text": "🌍 Country"}
                    },
                    {
                        "type": "input",
                        "block_id": "type_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "type_select",
                            "placeholder": {"type": "plain_text", "text": "Select segment type"},
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "⏱️ RetainedAtLeast"}, 
                                    "value": "RetainedAtLeast"
                                },
                                {
                                    "text": {"type": "plain_text", "text": "👥 ActiveUsers"}, 
                                    "value": "ActiveUsers"
                                }
                            ]
                        },
                        "label": {"type": "plain_text", "text": "📊 Segment Type"}
                    },
                    {
                        "type": "input",
                        "block_id": "value_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "value_input",
                            "placeholder": {"type": "plain_text", "text": "Enter value"}
                        },
                        "label": {"type": "plain_text", "text": "🎯 Value"},
                        "hint": {"type": "plain_text", "text": "For RetainedAtLeast: days (30). For ActiveUsers: ratio (0.95)"}
                    }
                ]
            }
        )
        logger.info("✅ Modal opened successfully")
        
    except Exception as e:
        logger.error(f"❌ Error opening modal: {e}")

@bolt_app.action("multiple_segments_btn")
def handle_multiple_segments_button(ack, body, client):
    logger.info("📊 Multiple segments button clicked")
    ack()
    
    try:
        channel_id = body.get("channel", {}).get("id", "unknown")
        trigger_id = body["trigger_id"]
        
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "create_multiple_segments_modal",
                "title": {"type": "plain_text", "text": "📊 Multiple Segments"},
                "submit": {"type": "plain_text", "text": "Create All"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "private_metadata": channel_id,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn", 
                            "text": "*🚀 Bulk Segment Creation*"
                        }
                    },
                    {"type": "divider"},
                    {
                        "type": "input",
                        "block_id": "app_id_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "app_id_input",
                            "placeholder": {"type": "plain_text", "text": "com.easybrain.number.puzzle.game"}
                        },
                        "label": {"type": "plain_text", "text": "📱 App ID (Bundle ID)"}
                    },
                    {
                        "type": "input",
                        "block_id": "countries_block",
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "countries_input",
                            "placeholder": {"type": "plain_text", "text": "Select countries"},
                            "options": POPULAR_COUNTRIES,
                            "max_selected_items": 10
                        },
                        "label": {"type": "plain_text", "text": "🌍 Countries"}
                    },
                    {
                        "type": "input",
                        "block_id": "segment_types_block",
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "segment_types_input",
                            "placeholder": {"type": "plain_text", "text": "Select segment types"},
                            "options": SEGMENT_TYPES,
                            "max_selected_items": 8
                        },
                        "label": {"type": "plain_text", "text": "📊 Segment Types"}
                    }
                ]
            }
        )
        logger.info("✅ Multiple segments modal opened")
        
    except Exception as e:
        logger.error(f"❌ Error opening multiple segments modal: {e}")

# Modal submission handlers
@bolt_app.view("create_segment_modal")
def handle_segment_modal(ack, body, client):
    logger.info("🔥 Processing segment modal submission")
    
    try:
        values = body["view"]["state"]["values"]
        
        # Extract values
        title = values.get("title_block", {}).get("title_input", {}).get("value", "").strip()
        country_data = values.get("country_block", {}).get("country_input", {})
        country = country_data.get("selected_option", {}).get("value", "")
        seg_type_data = values.get("type_block", {}).get("type_select", {})
        seg_type = seg_type_data.get("selected_option", {}).get("value", "")
        raw_val = values.get("value_block", {}).get("value_input", {}).get("value", "").strip()
        
        logger.info(f"📱 Values: title='{title}', country='{country}', type='{seg_type}', value='{raw_val}'")
        
        # Basic validation
        errors = {}
        
        if not title:
            errors["title_block"] = "Enter app Bundle ID"
        if not country:
            errors["country_block"] = "Select country"
        if not seg_type:
            errors["type_block"] = "Select segment type"
        if not raw_val:
            errors["value_block"] = "Enter value"
        else:
            if seg_type == "RetainedAtLeast":
                if not raw_val.isdigit():
                    errors["value_block"] = "Enter number of days"
            elif seg_type == "ActiveUsers":
                try:
                    val = float(raw_val)
                    if val <= 0 or val > 1:
                        errors["value_block"] = "Enter ratio 0.01-1.0"
                except ValueError:
                    errors["value_block"] = "Enter valid number"
        
        if errors:
            logger.warning(f"❌ Validation errors: {errors}")
            ack(response_action="errors", errors=errors)
            return
        
        # Validation passed
        ack()
        logger.info("✅ Modal validation passed")
        
        # Get user info
        channel_id = body["view"]["private_metadata"]
        user_id = body["user"]["id"]
        
        # Send progress message
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="🔄 Creating segment... Please wait."
        )
        
        # Create segment in background
        def create_segment_task():
            try:
                logger.info("🎯 Starting segment creation")
                
                # Try login if needed
                if not auth_logged_in:
                    logger.info("🔐 Attempting login...")
                    try_login()
                
                if not auth_logged_in:
                    msg = "❌ AppGrowth authorization failed. Please try again later."
                else:
                    # Prepare values
                    if seg_type == "RetainedAtLeast":
                        val = int(raw_val)
                        audience = 0.95  # Default
                    else:  # ActiveUsers
                        val = float(raw_val)
                        audience = val
                    
                    name = generate_segment_name(title, country, seg_type, val)
                    logger.info(f"🎯 Creating segment: {name}")
                    
                    # Create segment
                    ok = appgrowth.create_segment(
                        name=name,
                        title=title,
                        app=title,
                        country=country,
                        audience=audience,
                        seg_type=seg_type
                    )
                    
                    if ok:
                        msg = f"✅ Segment created: `{name}`"
                        logger.info(f"✅ Success: {name}")
                    else:
                        msg = "❌ Failed to create segment. Please check parameters."
                        logger.error(f"❌ Failed: {name}")
                
                # Send result
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=msg
                )
                
            except Exception as e:
                logger.error(f"❌ Segment creation error: {e}")
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"❌ Error: {e}"
                )
        
        # Start background task
        thread = threading.Thread(target=create_segment_task, daemon=True)
        thread.start()
        logger.info("🚀 Background task started")
        
    except Exception as e:
        logger.error(f"❌ Modal handler error: {e}")
        ack()

@bolt_app.view("create_multiple_segments_modal")
def handle_multiple_segments_modal(ack, body, client):
    logger.info("🔥 Processing multiple segments modal")
    
    try:
        values = body["view"]["state"]["values"]
        
        # Extract values
        app_id = values.get("app_id_block", {}).get("app_id_input", {}).get("value", "").strip()
        countries_data = values.get("countries_block", {}).get("countries_input", {})
        countries = [opt["value"] for opt in countries_data.get("selected_options", [])]
        segment_types_data = values.get("segment_types_block", {}).get("segment_types_input", {})
        segment_types = [opt["value"] for opt in segment_types_data.get("selected_options", [])]
        
        logger.info(f"📱 Multiple: app='{app_id}', countries={countries}, types={segment_types}")
        
        # Validation
        errors = {}
        if not app_id:
            errors["app_id_block"] = "Enter app Bundle ID"
        if not countries:
            errors["countries_block"] = "Select countries"
        if not segment_types:
            errors["segment_types_block"] = "Select segment types"
        
        if errors:
            logger.warning(f"❌ Multiple validation errors: {errors}")
            ack(response_action="errors", errors=errors)
            return
        
        ack()
        logger.info("✅ Multiple segments validation passed")
        
        channel_id = body["view"]["private_metadata"]
        user_id = body["user"]["id"]
        
        total_segments = len(countries) * len(segment_types)
        
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"🔄 Creating {total_segments} segments... Please wait."
        )
        
        def create_multiple_task():
            try:
                logger.info(f"🎯 Creating {total_segments} segments")
                
                if not auth_logged_in:
                    try_login()
                
                if not auth_logged_in:
                    msg = "❌ AppGrowth authorization failed"
                    client.chat_postEphemeral(channel=channel_id, user=user_id, text=msg)
                    return
                
                created = []
                failed = []
                
                for country in countries:
                    for seg_type_value in segment_types:
                        seg_type, value = seg_type_value.split("_")
                        
                        try:
                            name = generate_segment_name(app_id, country, seg_type, value)
                            logger.info(f"🎯 Creating: {name}")
                            
                            if seg_type == "RetainedAtLeast":
                                audience = 0.95
                            else:
                                audience = float(value)
                            
                            ok = appgrowth.create_segment(
                                name=name,
                                title=app_id,
                                app=app_id,
                                country=country,
                                audience=audience,
                                seg_type=seg_type
                            )
                            
                            if ok:
                                created.append(name)
                                logger.info(f"✅ Created: {name}")
                            else:
                                failed.append(name)
                                logger.error(f"❌ Failed: {name}")
                                
                        except Exception as e:
                            failed.append(f"{country}_{seg_type}_{value}")
                            logger.error(f"❌ Error: {e}")
                        
                        time.sleep(0.5)  # Rate limiting
                
                success_count = len(created)
                fail_count = len(failed)
                
                if success_count > 0 and fail_count == 0:
                    msg = f"🎉 All {success_count} segments created successfully!"
                elif success_count > 0:
                    msg = f"⚠️ {success_count}/{total_segments} segments created. {fail_count} failed."
                else:
                    msg = "❌ Failed to create any segments."
                
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=msg
                )
                
                logger.info(f"✅ Multiple task completed: {success_count} success, {fail_count} failed")
                
            except Exception as e:
                logger.error(f"❌ Multiple creation error: {e}")
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"❌ Error: {e}"
                )
        
        thread = threading.Thread(target=create_multiple_task, daemon=True)
        thread.start()
        logger.info("🚀 Multiple segments task started")
        
    except Exception as e:
        logger.error(f"❌ Multiple modal error: {e}")
        ack()

# Flask app setup
logger.info("🌐 Setting up Flask app...")
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@flask_app.route("/", methods=["GET"])
def home():
    return {"status": "AppGrowth Bot is running", "timestamp": time.time()}

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    logger.info("📨 Received Slack event")
    try:
        return handler.handle(request)
    except Exception as e:
        logger.error(f"❌ Event handling error: {e}")
        return {"error": str(e)}, 500

@flask_app.route("/health", methods=["GET"])
def health():
    return {
        "status": "ok",
        "appgrowth_auth": "connected" if auth_logged_in else "disconnected",
        "timestamp": time.time()
    }

# Background login on startup
def startup_login():
    logger.info("🚀 Starting background login...")
    time.sleep(2)  # Give app time to start
    try_login()

if __name__ == "__main__":
    # Start background login
    login_thread = threading.Thread(target=startup_login, daemon=True)
    login_thread.start()
    
    # Start Flask app
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting Flask app on port {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False)