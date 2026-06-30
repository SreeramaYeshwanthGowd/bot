import logging

from botbuilder.core import CardFactory, MessageFactory, TurnContext
from botbuilder.core.teams import TeamsActivityHandler

from src.cards import build_request_card


# Latest submitted values are kept only in this running Function worker's memory.
LAST_CATALOG = ""
LAST_SCHEMA = ""
LAST_TABLE = ""
LAST_MESSAGE = ""

class DPSBot(TeamsActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext) -> None:
        global LAST_CATALOG, LAST_SCHEMA, LAST_TABLE, LAST_MESSAGE

        # Adaptive Card submits arrive here with form values in activity.value.
        submitted_value = turn_context.activity.value
        if isinstance(submitted_value, dict) and submitted_value.get("action") == "submit_table_details":
            LAST_CATALOG = str(submitted_value.get("catalog", "")).strip()
            LAST_SCHEMA = str(submitted_value.get("schema", "")).strip()
            LAST_TABLE = str(submitted_value.get("table", "")).strip()
            LAST_MESSAGE = str(submitted_value.get("message", "")).strip()

            captured = {
                "catalog": LAST_CATALOG,
                "schema": LAST_SCHEMA,
                "table": LAST_TABLE,
                "message": LAST_MESSAGE,
            }

            logging.warning("DPSBot submitted details: %s", captured)
            print(f"DPSBot submitted details: {captured}")
            await turn_context.send_activity("Details captured.")
            return

        # Any normal message or @mention shows the request form card.
        activity = MessageFactory.attachment(CardFactory.adaptive_card(build_request_card()))
        activity.text = "DPSBot request form."
        activity.summary = "DPSBot request form."
        await turn_context.send_activity(activity)
