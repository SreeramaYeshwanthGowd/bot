import logging
import os

import requests
from botbuilder.core import CardFactory, MessageFactory, TurnContext
from botbuilder.core.teams import TeamsActivityHandler
from botbuilder.schema import ChannelAccount, Mention

from src.cards import build_request_card


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_SELECT = "$select"
OWNER_SELECT = "id,displayName,userPrincipalName,mail"

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
            GRAPH_SELECT: "id,displayName",
        },
        timeout=10,
    )
    response.raise_for_status()
    groups = response.json().get("value", [])
    return groups[0] if groups else None


def list_group_owners(access_token: str, group_id: str) -> list[dict]:
    owners = []
    url = f"{GRAPH_BASE_URL}/groups/{group_id}/owners/microsoft.graph.user"
    params = {GRAPH_SELECT: OWNER_SELECT}

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


def get_user(access_token: str, user_id: str) -> dict:
    response = requests.get(
        f"{GRAPH_BASE_URL}/users/{user_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={GRAPH_SELECT: OWNER_SELECT},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def resolve_owner(access_token: str, owner: dict) -> dict:
    if owner.get("displayName") or owner.get("userPrincipalName") or owner.get("mail"):
        return owner

    owner_id = owner.get("id")
    if not owner_id:
        return owner

    try:
        return get_user(access_token, owner_id)
    except requests.RequestException:
        logging.warning("DPSBot could not resolve owner details for id=%s", owner_id)
        return owner


def owner_name(owner: dict) -> str:
    return owner.get("displayName") or owner.get("userPrincipalName") or owner.get("id") or "Owner"


def build_owner_request_activity(
    owners: list[dict],
    requester_name: str,
    group_name: str,
    catalog: str,
    schema: str,
    table: str,
    message: str,
):
    mentions = []
    owner_texts = []

    for owner in owners:
        name = owner_name(owner)
        owner_id = owner.get("id")

        if owner_id:
            mention_text = f"<at>{name}</at>"
            owner_texts.append(mention_text)
            mentions.append(
                Mention(
                    mentioned=ChannelAccount(
                        id=owner_id,
                        name=name,
                        aad_object_id=owner_id,
                    ),
                    text=mention_text,
                    type="mention",
                )
            )
        else:
            owner_texts.append(name)

    owner_mentions = ", ".join(owner_texts)
    requester = requester_name or "A user"
    request_message = message or "No message provided."

    activity = MessageFactory.text(
        "\n".join(
            [
                f"{owner_mentions}, please review this access request.",
                f"Requested by: {requester}",
                f"Group: {group_name}",
                f"Catalog: {catalog}",
                f"Schema: {schema}",
                f"Table: {table or 'Not provided'}",
                f"Message: {request_message}",
                "As you are the owner, kindly look into it.",
            ]
        )
    )
    activity.entities = mentions
    return activity


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

                resolved_owners = [resolve_owner(access_token, owner) for owner in owners]
                requester = getattr(turn_context.activity.from_property, "name", None)
                await turn_context.send_activity(
                    build_owner_request_activity(
                        resolved_owners,
                        requester,
                        group_name,
                        LAST_CATALOG,
                        LAST_SCHEMA,
                        LAST_TABLE,
                        LAST_MESSAGE,
                    )
                )
            except Exception:
                logging.exception("DPSBot owner lookup failed")
                await turn_context.send_activity(
                    "Owner lookup failed. Check Application Insights logs."
                )
            return

        # Any normal message or @mention shows the request form card.
        activity = MessageFactory.attachment(CardFactory.adaptive_card(build_request_card()))
        await turn_context.send_activity(activity)
