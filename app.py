# app.py — Slack bot for AppGrowth (Working version - Multiple segments only)
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
from countries import POPULAR_COUNTRIES

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

# Countries imported from countries.py

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

def parse_bulk_countries(bulk_text):
    """Parse bulk country codes from text input (supports newlines, commas, and spaces)"""
    if not bulk_text or not bulk_text.strip():
        return []

    # Replace commas with spaces, then split by any whitespace
    text = bulk_text.replace(',', ' ')
    codes = text.split()

    parsed_codes = []
    for code in codes:
        code = code.strip().upper()
        if code:
            parsed_codes.append(code)

    return parsed_codes

def generate_segment_name(app_id, country, seg_type, value):
    """Generate segment name with UPPERCASE country code"""
    if seg_type == "RetainedAtLeast":
        code = str(int(value)) + "d"
    else:  # ActiveUsers
        if isinstance(value, str):
            value = float(value)
        code = str(int(value * 100))

    # Make country uppercase, keep app_id as is, code lowercase
    country = country.upper()
    # app_id keeps original case - removed .lower()
    code = code.lower()

    return f"bloom_{app_id}_{country}_{code}"

# Initialize Bolt app
logger.info("🚀 Initializing Slack Bolt app...")
bolt_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    process_before_response=True,  # Critical for avoiding timeouts
    logger=logger
)
logger.info("✅ Bolt app initialized with process_before_response=True")

@bolt_app.command("/appgrowth")
def handle_appgrowth_command(ack, respond, command):
    ack()
    
    logger.info("🎯 Processing /appgrowth command")
    
    text = command.get("text", "").strip()
    
    if not text:
        logger.info("📋 Showing main menu")
        respond(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn", 
                        "text": "*🎯 Welcome to AppGrowth Bot!*\n\nUse the bot to create segments in AppGrowth:\n• Quick creation through convenient forms\n• Automatic segment name generation\n• Parameter validation"
                    }
                },
                {
                    "type": "actions", 
                    "elements": [
                        {
                            "type": "button", 
                            "text": {"type": "plain_text", "text": "📊 Multiple Segments"}, 
                            "action_id": "multiple_segments_btn",
                            "style": "primary"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 *Tip:* Use `/appgrowth ping` to check bot status"
                        }
                    ]
                }
            ]
        )
        return
    
    if text.lower() == 'ping':
        auth_status = "🟢 Connected" if auth_logged_in else "🔴 Disconnected"
        logger.info(f"📊 Ping command - auth status: {auth_status}")
        respond(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🟢 *pong!* Bot is working fine ✨\n\n📊 AppGrowth Status: {auth_status}"
                    }
                }
            ]
        )
        return
    
    # For any other commands
    respond(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🤖 Unknown command: `{text}`\n\nUse:\n• `/appgrowth` - main menu\n• `/appgrowth ping` - status check"
                }
            }
        ]
    )

# Multiple segments creation button handler  
@bolt_app.action("multiple_segments_btn")
def open_multiple_segments_modal(ack, body, client):
    ack()
    
    logger.info("📊 Opening multiple segments creation modal")
    
    try:
        channel_id = None
        
        if "channel_id" in body:
            channel_id = body["channel_id"]
        elif "channel" in body and "id" in body["channel"]:
            channel_id = body["channel"]["id"]
        elif "container" in body and "channel_id" in body["container"]:
            channel_id = body["container"]["channel_id"]
        elif "response_url" in body:
            channel_id = body.get("user", {}).get("id", "unknown")
        
        if not channel_id:
            logger.error("❌ Could not find channel_id for multiple segments")
            return
        
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
                            "text": "*🚀 Bulk Segment Creation*\nCreate multiple segments for one app across different countries and types:"
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
                        "label": {"type": "plain_text", "text": "📱 App ID (Bundle ID)"},
                        "hint": {"type": "plain_text", "text": "Enter the application Bundle ID"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*🌍 Countries*"}
                    },
                    {
                        "type": "input",
                        "block_id": "countries_block",
                        "optional": True,
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "countries_input",
                            "placeholder": {"type": "plain_text", "text": "Select countries"},
                            "options": POPULAR_COUNTRIES,
                            "max_selected_items": 20
                        },
                        "label": {"type": "plain_text", "text": "Dropdown"},
                        "hint": {"type": "plain_text", "text": "Select multiple countries from list"}
                    },
                    {
                        "type": "input",
                        "block_id": "bulk_countries_block",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "bulk_countries_input",
                            "multiline": True,
                            "placeholder": {"type": "plain_text", "text": "ARE ZAF ISR or ARE, ZAF, ISR"}
                        },
                        "label": {"type": "plain_text", "text": "Bulk Text"},
                        "hint": {"type": "plain_text", "text": "Paste country codes: one per line, with spaces, or with commas"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*📊 Segment Types*"}
                    },
                    {
                        "type": "input",
                        "block_id": "all_segments_block",
                        "element": {
                            "type": "checkboxes",
                            "action_id": "all_segments_input",
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "All"},
                                    "value": "all_segments"
                                }
                            ],
                            "initial_options": [
                                {
                                    "text": {"type": "plain_text", "text": "All"},
                                    "value": "all_segments"
                                }
                            ]
                        },
                        "label": {"type": "plain_text", "text": "All Types"},
                        "hint": {"type": "plain_text", "text": "Uncheck to manually select specific types"}
                    },
                    {
                        "type": "input",
                        "block_id": "segment_types_block",
                        "optional": True,
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "segment_types_input",
                            "placeholder": {"type": "plain_text", "text": "Select specific segment types"},
                            "options": SEGMENT_TYPES,
                            "max_selected_items": 5
                        },
                        "label": {"type": "plain_text", "text": "Manual Selection"},
                        "hint": {"type": "plain_text", "text": "Only used when 'All' is unchecked above"}
                    }
                ]
            }
        )
        logger.info("✅ Multiple segments modal opened successfully")
    except Exception as e:
        logger.error(f"❌ Error opening multiple segments modal: {e}")

# Handle form inputs to prevent warnings
@bolt_app.action(re.compile("app_id_input|countries_input|bulk_countries_input|all_segments_input|segment_types_input"))
def handle_form_inputs(ack, body):
    ack()
    # Just acknowledge, no preview needed

# Multiple segments submission handler
@bolt_app.view("create_multiple_segments_modal")
def handle_multiple_segments_submission(ack, body, client):
    logger.info("🔥 START: Processing multiple segments submission")
    
    try:
        values = body["view"]["state"]["values"]

        app_id_data = values.get("app_id_block", {}).get("app_id_input", {})
        app_id = app_id_data.get("value", "").strip() if app_id_data.get("value") else ""

        # Get countries from dropdown
        countries_data = values.get("countries_block", {}).get("countries_input", {})
        countries_dropdown = [opt["value"] for opt in countries_data.get("selected_options", [])]

        # Get countries from bulk text
        bulk_data = values.get("bulk_countries_block", {}).get("bulk_countries_input", {})
        bulk_text = bulk_data.get("value", "") if bulk_data.get("value") else ""
        countries_bulk = parse_bulk_countries(bulk_text)

        # Merge and deduplicate countries
        countries = list(set(countries_dropdown + countries_bulk))

        # Check if "ALL segments" checkbox is selected
        all_segments_data = values.get("all_segments_block", {}).get("all_segments_input", {})
        all_segments_checked = len(all_segments_data.get("selected_options", [])) > 0

        # Get manually selected segment types
        segment_types_data = values.get("segment_types_block", {}).get("segment_types_input", {})
        segment_types_manual = [opt["value"] for opt in segment_types_data.get("selected_options", [])]

        # If "ALL" is checked, use all 5 segment types
        if all_segments_checked:
            segment_types = [seg["value"] for seg in SEGMENT_TYPES]
        else:
            segment_types = segment_types_manual

        logger.info(f"📱 App ID: '{app_id}', 🌍 Countries (dropdown): {countries_dropdown}, 🌍 Countries (bulk): {countries_bulk}, 🌍 Total: {countries}, ✅ ALL segments: {all_segments_checked}, 📊 Types: {segment_types}")

        errors = {}

        if not app_id:
            errors["app_id_block"] = "Enter app Bundle ID"
        elif len(app_id) < 5:
            errors["app_id_block"] = "Bundle ID too short"

        if not countries:
            errors["countries_block"] = "Select countries from dropdown or enter bulk text"

        if not segment_types:
            errors["all_segments_block"] = "Check 'ALL segments' or select at least one segment type"
        
        if errors:
            logger.warning(f"❌ Multiple segments validation failed: {errors}")
            ack(response_action="errors", errors=errors)
            return
        
        logger.info("✅ Multiple segments validation passed")
        ack()
        
        channel_id = body["view"]["private_metadata"]
        user_id = body["user"]["id"]
        
        total_segments = len(countries) * len(segment_types)
        
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"🔄 *Creating {total_segments} segments...*\nPlease wait, this may take a minute.",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"🔄 *Creating {total_segments} segments...*\nPlease wait, this may take a minute."}
                }
            ]
        )
        
        def create_multiple_segments_async():
            try:
                logger.info(f"🎯 Starting creation of {total_segments} segments")
                
                if not auth_logged_in:
                    try_login()
                
                if not auth_logged_in:
                    msg = "❌ *AppGrowth authorization error*\n🔧 Please try again later"
                    client.chat_postEphemeral(channel=channel_id, user=user_id, text=msg)
                    return
                
                created_segments = []
                failed_segments = []
                processed = 0
                
                for country in countries:
                    for seg_type_value in segment_types:
                        seg_type, value = seg_type_value.split("_")
                        
                        try:
                            name = generate_segment_name(app_id, country, seg_type, value)
                            logger.info(f"🎯 Creating segment: {name}")
                            
                            if seg_type == "RetainedAtLeast":
                                val = int(value)
                            else:  # ActiveUsers
                                val = float(value)
                            
                            ok = appgrowth.create_segment(
                                name=name,
                                title=app_id,
                                app=app_id,
                                country=country,
                                value=val,
                                seg_type=seg_type
                            )
                            
                            if ok:
                                created_segments.append(name)
                                logger.info(f"✅ Created: {name}")
                            else:
                                failed_segments.append(name)
                                logger.error(f"❌ Failed: {name} (probably already exists or server error)")
                                
                        except Exception as e:
                            failed_segments.append(f"{country}_{seg_type}_{value}")
                            logger.error(f"❌ Exception creating {country}_{seg_type}_{value}: {e}")
                        
                        processed += 1
                        # Send progress update every 5 segments
                        if processed % 5 == 0:
                            try:
                                client.chat_postEphemeral(
                                    channel=channel_id,
                                    user=user_id,
                                    text=f"🔄 Progress: {processed}/{total_segments} processed, {len(created_segments)} created so far..."
                                )
                            except:
                                pass
                        
                        time.sleep(0.5)
                
                success_count = len(created_segments)
                fail_count = len(failed_segments)
                
                if success_count > 0 and fail_count == 0:
                    msg = f"🎉 *All {success_count} segments created successfully!*\n\n📋 Created segments:\n" + "\n".join([f"• `{name}`" for name in created_segments])
                elif success_count > 0 and fail_count > 0:
                    msg = f"⚠️ *Partially completed: {success_count}/{total_segments} segments created*\n\n"
                    if created_segments:
                        msg += f"✅ *Created ({success_count}):*\n" + "\n".join([f"• `{name}`" for name in created_segments[:10]])
                        if len(created_segments) > 10:
                            msg += f"\n... and {len(created_segments) - 10} more"
                    if failed_segments:
                        msg += f"\n\n❌ *Failed ({fail_count}):*\n" + "\n".join([f"• `{name}`" for name in failed_segments[:10]])
                        if len(failed_segments) > 10:
                            msg += f"\n... and {len(failed_segments) - 10} more"
                else:
                    msg = f"❌ *Failed to create any segments ({total_segments} total)*\n\n"
                    if failed_segments:
                        msg += f"📋 *Failed segments:*\n" + "\n".join([f"• `{name}`" for name in failed_segments[:20]])
                        if len(failed_segments) > 20:
                            msg += f"\n... and {len(failed_segments) - 20} more"
                    msg += f"\n\n🔧 *Possible reasons:*\n• Segments already exist\n• Invalid app ID\n• Server errors"
                
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=msg,
                    blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": msg}}]
                )
                
                logger.info(f"✅ Multiple segments process completed: {success_count} success, {fail_count} failed")
                
            except Exception as e:
                logger.error(f"❌ Multiple segments creation error: {e}")
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"❌ *Error creating segments:* {e}"
                )
        
        thread = threading.Thread(target=create_multiple_segments_async, daemon=True)
        thread.start()
        logger.info("🚀 Background multiple segments creation started")
        
    except Exception as e:
        logger.error(f"❌ Error in multiple segments handler: {e}")
        ack()

# Background login
def background_login():
    time.sleep(3)
    try_login()

# Flask wrapper
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

@flask_app.route("/health", methods=["GET"])
def health():
    return {
        "status": "ok",
        "appgrowth_auth": "connected" if auth_logged_in else "disconnected",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    # Start background login
    login_thread = threading.Thread(target=background_login, daemon=True)
    login_thread.start()
    
    # Start Flask app
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting Flask app on port {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False, threaded=True)