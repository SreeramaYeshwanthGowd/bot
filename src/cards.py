from datetime import datetime, timezone
from typing import Optional


def build_pilot_card(
    requester_name: Optional[str],
    conversation_type: Optional[str],
    channel_id: Optional[str],
) -> dict:
    requested_by = requester_name or "Unknown user"
    conversation = conversation_type or "unknown"
    channel = channel_id or "unknown"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return {
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "DPSBot pilot is connected",
                "weight": "Bolder",
                "size": "Large",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": (
                    "Your Teams mention reached Azure Bot Service, "
                    "Azure Functions, and the Python bot handler."
                ),
                "wrap": True,
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Requested by", "value": requested_by},
                    {"title": "Conversation", "value": conversation},
                    {"title": "Teams channel", "value": channel},
                    {"title": "UTC time", "value": timestamp},
                ],
            },
            {
                "type": "TextBlock",
                "text": (
                    "Pilot safety: no Microsoft Graph calls, no Jira calls, "
                    "no Databricks calls, and no request data was stored."
                ),
                "isSubtle": True,
                "wrap": True,
                "spacing": "Medium",
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "I can see the card",
                "data": {"action": "pilot_ack"},
            }
        ],
    }
