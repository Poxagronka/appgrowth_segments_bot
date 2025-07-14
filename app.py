# app.py — Slack bot for AppGrowth (Fixed version)
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

# Global auth status
AUTH_STATUS = {"logged_in": False, "in_progress": False}

# Bolt app initialization
bolt_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    logger=logger,
)

def lazy_login():
    """Lazy AppGrowth authorization"""
    if AUTH_STATUS["logged_in"]:
        return True
    
    if AUTH_STATUS["in_progress"]:
        for _ in range(20):
            time.sleep(0.5)
            if AUTH_STATUS["logged_in"]:
                return True
        return False
    
    AUTH_STATUS["in_progress"] = True
    try:
        logger.info("🔐 Performing AppGrowth authorization...")
        success = appgrowth.login()
        AUTH_STATUS["logged_in"] = success
        if success:
            logger.info("✅ AppGrowth authorization successful")
        else:
            logger.error("❌ Failed to authorize with AppGrowth")
        return success
    except Exception as e:
        logger.error(f"❌ AppGrowth authorization error: {e}")
        return False
    finally:
        AUTH_STATUS["in_progress"] = False

def async_login():
    """Async authorization on startup"""
    def login_thread():
        lazy_login()
    
    thread = threading.Thread(target=login_thread, daemon=True)
    thread.start()
    logger.info("🚀 Background AppGrowth authorization started...")

def generate_segment_name(app_id, country, seg_type, value):
    """Generate segment name with proper formatting"""
    if seg_type == "RetainedAtLeast":
        code = str(int(value)) + "d"  # Add 'd' for days: 30d, 7d, 1d
    else:  # ActiveUsers
        if isinstance(value, str):
            value = float(value)
        code = str(int(value * 100))
    
    country = country.upper()
    return f"bloom_{app_id}_{country}_{code}".lower()

# Start background auth
async_login()

# Main command handler
@bolt_app.command("/appgrowth")
def handle_appgrowth(ack, respond, command):
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
                            "text": {"type": "plain_text", "text": "➕ New Segment"}, 
                            "action_id": "new_segment_btn",
                            "style": "primary"
                        },
                        {
                            "type": "button", 
                            "text": {"type": "plain_text", "text": "📊 Multiple Segments"}, 
                            "action_id": "multiple_segments_btn",
                            "style": "secondary"
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
        auth_status = "🟢 Connected" if AUTH_STATUS["logged_in"] else "🔄 Connecting..." if AUTH_STATUS["in_progress"] else "🔴 Disconnected"
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

# Single segment creation button handler
@bolt_app.action("new_segment_btn")
def open_segment_modal(ack, body, client):
    ack()
    
    logger.info("🎯 Opening single segment creation modal")
    
    try:
        # Extract channel_id properly
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
            logger.error("❌ Could not find channel_id")
            return
        
        trigger_id = body["trigger_id"]
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
                            "text": "*Creating a new segment in AppGrowth*\nFill in the parameters to generate a segment:"
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
                        "label": {"type": "plain_text", "text": "📱 App ID (Bundle ID)"},
                        "hint": {"type": "plain_text", "text": "Enter or paste the application Bundle ID"}
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
                        "label": {"type": "plain_text", "text": "🌍 Country"},
                        "hint": {"type": "plain_text", "text": "3-letter country code for targeting"}
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
                                    "text": {"type": "plain_text", "text": "⏱️ RetainedAtLeast - User Retention"}, 
                                    "value": "RetainedAtLeast"
                                },
                                {
                                    "text": {"type": "plain_text", "text": "👥 ActiveUsers - Active Users"}, 
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
                        "hint": {"type": "plain_text", "text": "For RetainedAtLeast: number of days (e.g., 30). For ActiveUsers: ratio from 0 to 1 (e.g., 0.95)"}
                    },
                    {
                        "type": "section",
                        "block_id": "preview_block",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Preview segment name:*\n`bloom_[app-id]_[country]_[value]`"
                        }
                    }
                ]
            }
        )
        logger.info("✅ Single segment modal opened successfully")
    except Exception as e:
        logger.error(f"❌ Error opening single segment modal: {e}")

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
                        "type": "input",
                        "block_id": "countries_block",
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "countries_input",
                            "placeholder": {"type": "plain_text", "text": "Select countries"},
                            "options": POPULAR_COUNTRIES,
                            "max_selected_items": 10
                        },
                        "label": {"type": "plain_text", "text": "🌍 Countries"},
                        "hint": {"type": "plain_text", "text": "Select multiple countries for targeting"}
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
                        "label": {"type": "plain_text", "text": "📊 Segment Types"},
                        "hint": {"type": "plain_text", "text": "Select multiple segment types to create"}
                    },
                    {
                        "type": "section",
                        "block_id": "multiple_preview_block",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*📋 Preview:*\nSelect options above to see segments that will be created..."
                        }
                    }
                ]
            }
        )
        logger.info("✅ Multiple segments modal opened successfully")
    except Exception as e:
        logger.error(f"❌ Error opening multiple segments modal: {e}")

# Type change handler
@bolt_app.action("type_select")
def handle_type_change(ack, body, client):
    ack()
    
    try:
        view_id = body["view"]["id"]
        selected_type = body["actions"][0]["selected_option"]["value"]
        
        value_hint = {
            "RetainedAtLeast": "Number of retention days (e.g., 7, 14, 30)",
            "ActiveUsers": "Active users ratio from 0 to 1 (e.g., 0.80, 0.95)"
        }
        
        value_placeholder = {
            "RetainedAtLeast": "30",
            "ActiveUsers": "0.95"
        }
        
        updated_view = body["view"]
        updated_view["blocks"][4]["element"]["placeholder"]["text"] = value_placeholder.get(selected_type, "Enter value")
        updated_view["blocks"][4]["hint"]["text"] = value_hint.get(selected_type, "Enter segment value")
        
        client.views_update(
            view_id=view_id,
            view=updated_view
        )
    except Exception as e:
        logger.error(f"❌ Error updating type: {e}")

# Field changes for preview
@bolt_app.action(re.compile("title_input|country_input|value_input|app_id_input|countries_input|segment_types_input"))
def handle_field_changes(ack, body, client):
    ack()
    
    try:
        view_id = body["view"]["id"]
        values = body["view"]["state"]["values"]
        
        # Check if this is single or multiple segment modal
        if "title_block" in values:  # Single segment
            title = ""
            country = ""
            value = ""
            seg_type = "ActiveUsers"
            
            if "title_block" in values and values["title_block"]["title_input"]["value"]:
                title = values["title_block"]["title_input"]["value"]
            
            if "country_block" in values and values["country_block"]["country_input"]["selected_option"]:
                country = values["country_block"]["country_input"]["selected_option"]["value"]
                
            if "type_block" in values and values["type_block"]["type_select"]["selected_option"]:
                seg_type = values["type_block"]["type_select"]["selected_option"]["value"]
                
            if "value_block" in values and values["value_block"]["value_input"]["value"]:
                value = values["value_block"]["value_input"]["value"]
            
            if title and country and value:
                try:
                    preview_name = generate_segment_name(title, country, seg_type, value)
                    preview_text = f"*Preview segment name:*\n`{preview_name}`"
                except:
                    preview_text = "*Preview segment name:*\n`Fill all fields for preview`"
            else:
                preview_text = "*Preview segment name:*\n`Fill all fields for preview`"
            
            updated_view = body["view"]
            updated_view["blocks"][5]["text"]["text"] = preview_text
        
        else:  # Multiple segments
            app_id = ""
            countries = []
            segment_types = []
            
            if "app_id_block" in values and values["app_id_block"]["app_id_input"]["value"]:
                app_id = values["app_id_block"]["app_id_input"]["value"]
            
            if "countries_block" in values and values["countries_block"]["countries_input"]["selected_options"]:
                countries = [opt["value"] for opt in values["countries_block"]["countries_input"]["selected_options"]]
                
            if "segment_types_block" in values and values["segment_types_block"]["segment_types_input"]["selected_options"]:
                segment_types = [opt["value"] for opt in values["segment_types_block"]["segment_types_input"]["selected_options"]]
            
            if app_id and countries and segment_types:
                preview_lines = ["*📋 Segments to be created:*"]
                count = 0
                
                for country in countries[:3]:
                    for seg_type_value in segment_types[:3]:
                        seg_type, value = seg_type_value.split("_")
                        preview_name = generate_segment_name(app_id, country, seg_type, value)
                        preview_lines.append(f"• `{preview_name}`")
                        count += 1
                        if count >= 6:
                            break
                    if count >= 6:
                        break
                
                total_segments = len(countries) * len(segment_types)
                if total_segments > 6:
                    preview_lines.append(f"... *and {total_segments - 6} more segments*")
                
                preview_lines.append(f"\n*Total: {total_segments} segments*")
                preview_text = "\n".join(preview_lines)
            else:
                preview_text = "*📋 Preview:*\nSelect options above to see segments that will be created..."
            
            updated_view = body["view"]
            updated_view["blocks"][4]["text"]["text"] = preview_text
        
        client.views_update(
            view_id=view_id,
            view=updated_view
        )
    except Exception as e:
        logger.warning(f"Error updating preview: {e}")

# Single segment submission handler
@bolt_app.view("create_segment_modal")
def handle_segment_submission(ack, body, client):
    logger.info("🔥 START: Processing single segment submission")
    
    try:
        values = body["view"]["state"]["values"]
        
        title_data = values.get("title_block", {}).get("title_input", {})
        title = title_data.get("value", "").strip() if title_data.get("value") else ""
        
        country_data = values.get("country_block", {}).get("country_input", {})
        if country_data.get("selected_option"):
            country = country_data["selected_option"]["value"].strip()
        else:
            country = ""
        
        seg_type_data = values.get("type_block", {}).get("type_select", {})
        if seg_type_data.get("selected_option"):
            seg_type = seg_type_data["selected_option"]["value"]
        else:
            seg_type = ""
        
        raw_val_data = values.get("value_block", {}).get("value_input", {})
        raw_val = raw_val_data.get("value", "").strip() if raw_val_data.get("value") else ""
        
        logger.info(f"📱 Title: '{title}', 🌍 Country: '{country}', 📊 Type: '{seg_type}', 🎯 Value: '{raw_val}'")
        
        # Validation
        errors = {}
        
        if not title:
            errors["title_block"] = "Enter app Bundle ID"
        elif len(title) < 5:
            errors["title_block"] = "Bundle ID too short"
        
        if not country:
            errors["country_block"] = "Select country"
            
        if not seg_type:
            errors["type_block"] = "Select segment type"
        
        if not raw_val:
            errors["value_block"] = "Enter value"
        else:
            if seg_type == "RetainedAtLeast":
                if not raw_val.isdigit():
                    errors["value_block"] = "Enter number of days (e.g., 7, 14, 30)"
                else:
                    val = int(raw_val)
                    if val <= 0 or val > 365:
                        errors["value_block"] = "Days must be from 1 to 365"
            elif seg_type == "ActiveUsers":
                try:
                    val = float(raw_val)
                    if val <= 0 or val > 1:
                        errors["value_block"] = "Ratio must be from 0.01 to 1.0"
                except ValueError:
                    errors["value_block"] = "Enter ratio (e.g., 0.80, 0.95)"
        
        if errors:
            logger.warning(f"❌ Validation failed: {errors}")
            ack(response_action="errors", errors=errors)
            return
        
        logger.info("✅ Validation passed")
        ack()
        logger.info("✅ ACK sent, modal should close")
        
        channel_id = body["view"]["private_metadata"]
        user_id = body["user"]["id"]
        
        logger.info(f"📍 Channel ID: {channel_id}, User ID: {user_id}")
        
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="🔄 *Creating segment...*\nPlease wait, this may take a few seconds.",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "🔄 *Creating segment...*\nPlease wait, this may take a few seconds."}
                }
            ]
        )
        
        def create_segment_async():
            try:
                logger.info("🎯 Starting segment creation")
                
                if not lazy_login():
                    msg = "❌ *AppGrowth authorization error*\n🔧 Please try again later or contact administrator"
                else:
                    if seg_type == "RetainedAtLeast":
                        val = int(raw_val)
                    else:
                        val = float(raw_val)
                        
                    name = generate_segment_name(title, country, seg_type, val)
                    logger.info(f"🎯 Creating segment: {name}")
                    
                    # FIXED: Use proper audience parameter
                    if seg_type == "RetainedAtLeast":
                        ok = appgrowth.create_segment(
                            name=name,
                            title=title,
                            app=title,
                            country=country,
                            audience=0.95,  # Default value instead of None
                            seg_type=seg_type
                        )
                    else:  # ActiveUsers
                        ok = appgrowth.create_segment(
                            name=name,
                            title=title,
                            app=title,
                            country=country,
                            audience=val,
                            seg_type=seg_type
                        )
                    
                    if ok:
                        msg = f"✅ *Segment created successfully!*\n🎯 Name: `{name}`\n📱 App: `{title}`\n🌍 Country: `{country}`\n📊 Type: `{seg_type}`\n🎯 Value: `{raw_val}`"
                        logger.info(f"✅ Segment created: {name}")
                    else:
                        msg = f"❌ *Failed to create segment*\n🔧 Please check parameters and try again"
                        logger.error(f"❌ Failed to create segment: {name}")
                        
            except Exception as e:
                logger.error(f"❌ Segment creation error: {e}")
                msg = f"❌ *Creation error:* {e}"
            
            try:
                client.chat_postEphemeral(
                    channel=channel_id, 
                    user=user_id, 
                    text=msg,
                    blocks=[
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": msg}
                        }
                    ]
                )
                logger.info("✅ Result sent to user")
            except Exception as e:
                logger.error(f"❌ Error sending result: {e}")
        
        thread = threading.Thread(target=create_segment_async, daemon=True)
        thread.start()
        logger.info("🚀 Background segment creation started")
        
    except Exception as e:
        logger.error(f"❌ Error in submission handler: {e}")
        ack()

# Multiple segments submission handler
@bolt_app.view("create_multiple_segments_modal")
def handle_multiple_segments_submission(ack, body, client):
    logger.info("🔥 START: Processing multiple segments submission")
    
    try:
        values = body["view"]["state"]["values"]
        
        app_id_data = values.get("app_id_block", {}).get("app_id_input", {})
        app_id = app_id_data.get("value", "").strip() if app_id_data.get("value") else ""
        
        countries_data = values.get("countries_block", {}).get("countries_input", {})
        countries = [opt["value"] for opt in countries_data.get("selected_options", [])]
        
        segment_types_data = values.get("segment_types_block", {}).get("segment_types_input", {})
        segment_types = [opt["value"] for opt in segment_types_data.get("selected_options", [])]
        
        logger.info(f"📱 App ID: '{app_id}', 🌍 Countries: {countries}, 📊 Types: {segment_types}")
        
        errors = {}
        
        if not app_id:
            errors["app_id_block"] = "Enter app Bundle ID"
        elif len(app_id) < 5:
            errors["app_id_block"] = "Bundle ID too short"
        
        if not countries:
            errors["countries_block"] = "Select at least one country"
            
        if not segment_types:
            errors["segment_types_block"] = "Select at least one segment type"
        
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
                
                if not lazy_login():
                    msg = "❌ *AppGrowth authorization error*\n🔧 Please try again later"
                    client.chat_postEphemeral(channel=channel_id, user=user_id, text=msg)
                    return
                
                created_segments = []
                failed_segments = []
                
                for country in countries:
                    for seg_type_value in segment_types:
                        seg_type, value = seg_type_value.split("_")
                        
                        try:
                            name = generate_segment_name(app_id, country, seg_type, value)
                            logger.info(f"🎯 Creating segment: {name}")
                            
                            # FIXED: Use proper audience parameter
                            if seg_type == "RetainedAtLeast":
                                ok = appgrowth.create_segment(
                                    name=name,
                                    title=app_id,
                                    app=app_id,
                                    country=country,
                                    audience=0.95,  # Default value instead of None
                                    seg_type=seg_type
                                )
                            else:  # ActiveUsers
                                val = float(value)
                                ok = appgrowth.create_segment(
                                    name=name,
                                    title=app_id,
                                    app=app_id,
                                    country=country,
                                    audience=val,
                                    seg_type=seg_type
                                )
                            
                            if ok:
                                created_segments.append(name)
                                logger.info(f"✅ Created: {name}")
                            else:
                                failed_segments.append(name)
                                logger.error(f"❌ Failed: {name}")
                                
                        except Exception as e:
                            failed_segments.append(f"{country}_{seg_type}_{value}")
                            logger.error(f"❌ Error creating segment {country}_{seg_type}_{value}: {e}")
                        
                        time.sleep(0.5)
                
                success_count = len(created_segments)
                fail_count = len(failed_segments)
                
                if success_count > 0 and fail_count == 0:
                    msg = f"🎉 *All {success_count} segments created successfully!*\n\n📋 Created segments:\n" + "\n".join([f"• `{name}`" for name in created_segments[:10]])
                    if success_count > 10:
                        msg += f"\n... and {success_count - 10} more"
                elif success_count > 0 and fail_count > 0:
                    msg = f"⚠️ *Partially completed: {success_count}/{total_segments} segments created*\n\n✅ Success: {success_count}\n❌ Failed: {fail_count}"
                else:
                    msg = f"❌ *Failed to create any segments*\n🔧 Please check parameters and try again"
                
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

# Flask wrapper
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/health", methods=["GET"])
def health_check():
    auth_status = "connected" if AUTH_STATUS["logged_in"] else "connecting" if AUTH_STATUS["in_progress"] else "disconnected"
    return {
        "status": "ok",
        "appgrowth_auth": auth_status,
        "timestamp": time.time()
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting bot on port {port}")
    flask_app.run(host="0.0.0.0", port=port)