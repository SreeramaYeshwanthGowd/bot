import logging
import os

import requests
from botbuilder.core import CardFactory, MessageFactory, TurnContext
from botbuilder.core.teams import TeamsActivityHandler

from src.cards import build_request_card


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Latest submitted values are kept only in this running Function worker's memory.
LAST_CATALOG = ""
LAST_SCHEMA = ""
LAST_TABLE = ""
LAST_MESSAGE = ""


def get_graph_token() -> str:
    tenant_id = os.environ["MicrosoftAppTenantId"]
    response = requests.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": os.environ["MicrosoftAppId"],
            "client_secret": os.environ["MicrosoftAppPassword"],
            "scope": GRAPH_SCOPE,
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def find_group(access_token: str, display_name: str) -> dict | None:
    escaped_name = display_name.replace("'", "''")
    response = requests.get(
        f"{GRAPH_BASE_URL}/groups",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "$filter": f"displayName eq '{escaped_name}'",
            "$select": "id,displayName",
        },
        timeout=10,
    )
    response.raise_for_status()
    groups = response.json().get("value", [])
    return groups[0] if groups else None


def list_group_owners(access_token: str, group_id: str) -> list[dict]:
    owners = []
    url = f"{GRAPH_BASE_URL}/groups/{group_id}/owners"
    params = {"$select": "id,displayName,userPrincipalName,mail"}

    while url:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        owners.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
        params = None

    return owners


def owner_line(owner: dict) -> str:
    name = owner.get("displayName") or owner.get("id") or "Unknown owner"
    contact = owner.get("userPrincipalName") or owner.get("mail")
    return f"- {name} <{contact}>" if contact else f"- {name}"


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

            if not LAST_CATALOG or not LAST_SCHEMA:
                await turn_context.send_activity("Please enter catalog and schema.")
                return

            group_name = f"UC|Sch|{LAST_CATALOG}.{LAST_SCHEMA}|Write"

            try:
                access_token = get_graph_token()
                group = find_group(access_token, group_name)

                if not group:
                    await turn_context.send_activity(
                        f"No matching group found for {group_name}."
                    )
                    return

                owners = list_group_owners(access_token, group["id"])
                logging.warning(
                    "DPSBot owner lookup: group_name=%s group_id=%s owner_count=%s",
                    group_name,
                    group["id"],
                    len(owners),
                )

                if not owners:
                    await turn_context.send_activity(f"No owners found for {group_name}.")
                    return

                owner_lines = "\n".join(owner_line(owner) for owner in owners)
                await turn_context.send_activity(
                    f"Found owners for {group_name}:\n{owner_lines}"
                )
            except Exception:
                logging.exception("DPSBot owner lookup failed")
                await turn_context.send_activity(
                    "Owner lookup failed. Check Application Insights logs."
                )
            return

        # Any normal message or @mention shows the request form card.
        activity = MessageFactory.attachment(CardFactory.adaptive_card(build_request_card()))
        activity.text = "DPSBot request form."
        activity.summary = "DPSBot request form."
        await turn_context.send_activity(activity)
