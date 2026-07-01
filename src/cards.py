INPUT_TEXT = "Input.Text"
INPUT_CHOICE_SET = "Input.ChoiceSet"


def build_request_launcher_card() -> dict:
    return {
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
            {
                "type": "TextBlock",
                "text": "DPSBot access request",
                "weight": "Bolder",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": "Open the request form to select catalog, schema, or table access.",
                "wrap": True,
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Request access",
                "data": {
                    "action": "open_access_request_dialog",
                    "msteams": {"type": "task/fetch"},
                },
            }
        ],
    }


def build_request_card() -> dict:
    return {
        "type": "AdaptiveCard",
        "version": "1.2",
        "fallbackText": "DPSBot request form.",
        "body": [
            {
                "type": INPUT_CHOICE_SET,
                "id": "accessScope",
                "label": "Access scope",
                "style": "expanded",
                "value": "schema",
                "choices": [
                    {"title": "Catalog", "value": "catalog"},
                    {"title": "Schema", "value": "schema"},
                    {"title": "Table", "value": "table"},
                ],
            },
            {
                "type": INPUT_CHOICE_SET,
                "id": "accessType",
                "label": "Access type",
                "style": "expanded",
                "value": "Read",
                "choices": [
                    {"title": "Read", "value": "Read"},
                    {"title": "Write", "value": "Write"},
                ],
            },
            {
                "type": INPUT_TEXT,
                "id": "catalog",
                "placeholder": "Catalog",
            },
            {"type": INPUT_TEXT, "id": "schema", "placeholder": "Schema, required for schema/table access"},
            {"type": INPUT_TEXT, "id": "table", "placeholder": "Table, required for table access"},
            {
                "type": INPUT_TEXT,
                "id": "message",
                "placeholder": "Message",
                "isMultiline": True,
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Submit",
                "data": {"action": "submit_access_request"},
            }
        ],
    }
