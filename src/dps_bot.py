from botbuilder.core import CardFactory, MessageFactory, TurnContext
from botbuilder.core.teams import TeamsActivityHandler

from src.cards import build_pilot_card


class DPSPilotBot(TeamsActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext) -> None:
        submitted_value = turn_context.activity.value
        if isinstance(submitted_value, dict) and submitted_value.get("action") == "pilot_ack":
            await turn_context.send_activity(
                "Pilot button click received. Adaptive Card submit is working."
            )
            return

        requester = turn_context.activity.from_property
        conversation = turn_context.activity.conversation

        card = build_pilot_card(
            requester_name=getattr(requester, "name", None),
            conversation_type=getattr(conversation, "conversation_type", None),
            channel_id=turn_context.activity.channel_id,
        )

        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.adaptive_card(card))
        )
