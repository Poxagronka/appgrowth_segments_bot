# AppGrowth Segments Bot - Project Structure

## Overview
This is a Slack bot for AppGrowth segment generation, deployed on Fly.io.

## Project Structure
```
/Users/poxagronka/appgrowth-bot/
├── app.py              # Main Flask application and Slack bot handler
├── appgrowth.py        # Core AppGrowth API integration logic
├── countries.py        # Country list configuration (Tier 1-3 markets)
├── segments.html       # HTML template for segment generation form
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container configuration for deployment
├── fly.toml           # Fly.io deployment configuration
├── test_segment.py     # Test file for segment generation
└── debug_csrf.py       # CSRF debugging utility
```

## Key Components

### app.py
- Flask web server
- Slack event handlers (slash commands, interactions)
- OAuth flow for Slack
- Webhook endpoint for segment generation

### appgrowth.py
- AppGrowth API authentication
- Segment creation logic
- Error handling for API responses
- Bundle ID formatting

### countries.py
- Comprehensive list of countries organized by tiers:
  - Tier 1: Major markets (USA, GBR, DEU, etc.)
  - Tier 2: Growing markets (BRA, MEX, IND, etc.)
  - Tier 3: Emerging markets (including VEN, BGD, etc.)
- Format: Slack-compatible dropdown options with flags

## Deployment
- **Platform**: Fly.io
- **URL**: https://appgrowth-bot.fly.dev/
- **Repository**: https://github.com/Poxagronka/appgrowth_segments_bot

## Commands
- **Run locally**: `python app.py`
- **Deploy**: `fly deploy`
- **View logs**: `fly logs`

## Environment Variables
Required environment variables (set in Fly.io):
- `SLACK_BOT_TOKEN`
- `SLACK_CLIENT_SECRET`
- `SLACK_CLIENT_ID`
- `SLACK_SIGNING_SECRET`
- `CSRF_PROTECTION_ENABLED`

## Testing
- Use `test_segment.py` for local segment testing
- Debug CSRF issues with `debug_csrf.py`

## Recent Updates
- Added Venezuela (VEN) to Tier 3 markets
- All requested countries (AUT, VNM, BGD, PRT, CZE, THA, BLR, ZAF) confirmed present