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
JIRA_API_PATH = "/rest/api/3/issue"

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


def find_group_owners(access_token: str, display_name: str) -> tuple[dict | None, list[dict]]:
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
    if not groups:
        return None, []

    group = groups[0]
    owners = []
    url = f"{GRAPH_BASE_URL}/groups/{group['id']}/owners/microsoft.graph.user"
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

    return group, owners


def owner_reference(owner: dict) -> str:
    return f"{owner['displayName']} <{owner.get('userPrincipalName') or owner['mail']}>"


def jira_description(text: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line or " "}],
            }
            for line in text.splitlines()
        ],
    }


def jira_issue_url(issue_key: str) -> str:
    return f"{os.environ['JIRA_BASE_URL'].rstrip('/')}/browse/{issue_key}"


def create_jira_issue(summary: str, description: str) -> dict:
    jira_base_url = os.environ["JIRA_BASE_URL"].rstrip("/")
    response = requests.post(
        f"{jira_base_url}{JIRA_API_PATH}",
        auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={
            "fields": {
                "project": {"key": os.environ["JIRA_PROJECT_KEY"]},
                "summary": summary,
                "description": jira_description(description),
                "issuetype": {"name": os.environ["JIRA_ISSUE_TYPE"]},
            }
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def build_access_request_text(
    owners: list[dict],
    requester_name: str,
    group_name: str,
    catalog: str,
    schema: str,
    table: str,
    message: str,
    jira_issue: dict | None = None,
) -> str:
    owner_references = ", ".join(owner_reference(owner) for owner in owners)
    requester = requester_name or "A user"
    request_message = message or "No message provided."
    lines = [
        f"Owners: {owner_references}",
        f"Requested by: {requester}",
        f"Group: {group_name}",
        f"Catalog: {catalog}",
        f"Schema: {schema}",
        f"Table: {table or 'Not provided'}",
        f"Message: {request_message}",
    ]

    if jira_issue:
        issue_key = jira_issue["key"]
        lines.append(f"Jira: {issue_key} {jira_issue_url(issue_key)}")

    lines.append("As you are the owner, kindly look into it.")
    return "\n".join(lines)


def build_owner_request_activity(
    owners: list[dict],
    requester_name: str,
    group_name: str,
    catalog: str,
    schema: str,
    table: str,
    message: str,
    jira_issue: dict,
):
    mentions = []
    owner_texts = []

    for owner in owners:
        name = owner["displayName"]
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
    issue_key = jira_issue["key"]

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
                f"Jira: {issue_key} {jira_issue_url(issue_key)}",
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
                group, owners = find_group_owners(access_token, group_name)

                if not group:
                    await turn_context.send_activity(
                        f"No matching group found for {group_name}."
                    )
                    return

                logging.warning(
                    "DPSBot owner lookup: group_name=%s group_id=%s owner_count=%s",
                    group_name,
                    group["id"],
                    len(owners),
                )

                if not owners:
                    await turn_context.send_activity(f"No owners found for {group_name}.")
                    return

                requester = getattr(turn_context.activity.from_property, "name", None)

                description = build_access_request_text(
                    owners,
                    requester,
                    group_name,
                    LAST_CATALOG,
                    LAST_SCHEMA,
                    LAST_TABLE,
                    LAST_MESSAGE,
                )

                try:
                    jira_issue = create_jira_issue(
                        f"DPSBot access request - {group_name}",
                        description,
                    )
                    logging.warning(
                        "DPSBot Jira issue created: key=%s group_name=%s",
                        jira_issue.get("key"),
                        group_name,
                    )
                except Exception:
                    logging.exception("DPSBot Jira issue creation failed")
                    await turn_context.send_activity(
                        "Owner lookup succeeded, but Jira ticket creation failed. Check Application Insights logs."
                    )
                    return

                await turn_context.send_activity(
                    build_owner_request_activity(
                        owners,
                        requester,
                        group_name,
                        LAST_CATALOG,
                        LAST_SCHEMA,
                        LAST_TABLE,
                        LAST_MESSAGE,
                        jira_issue,
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
