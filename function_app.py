import json
import logging
import os

import azure.functions as func
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

from src.dps_bot import DPSPilotBot

logging.basicConfig(level=logging.INFO)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

SETTINGS = BotFrameworkAdapterSettings(
    app_id=os.environ.get("MicrosoftAppId", ""),
    app_password=os.environ.get("MicrosoftAppPassword", ""),
)
ADAPTER = BotFrameworkAdapter(SETTINGS)
BOT = DPSPilotBot()


async def on_error(context: TurnContext, error: Exception) -> None:
    logging.error("Unhandled bot error: %s", error, exc_info=True)
    await context.send_activity(
        "DPSBot pilot hit an error. Check the Azure Function log stream for details."
    )


ADAPTER.on_turn_error = on_error


@app.route(route="messages", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        raw_body = req.get_body().decode("utf-8")
        if not raw_body:
            return func.HttpResponse("Missing activity body.", status_code=400)
        body = json.loads(raw_body)

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    invoke_response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if invoke_response:
        return func.HttpResponse(
            body=json.dumps(invoke_response.body),
            status_code=invoke_response.status,
            mimetype="application/json",
        )

    return func.HttpResponse(status_code=200)
