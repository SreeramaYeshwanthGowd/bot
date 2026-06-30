import logging
import os

import azure.functions as func
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

from src.dps_bot import DPSBot

logging.basicConfig(level=logging.INFO)

# Azure Functions looks for this app object when the Python worker starts.
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# These settings let the Bot Framework adapter authenticate requests from Azure Bot Service.
SETTINGS = BotFrameworkAdapterSettings(
    app_id=os.environ.get("MicrosoftAppId", ""),
    app_password=os.environ.get("MicrosoftAppPassword", ""),
    channel_auth_tenant=os.environ.get("MicrosoftAppTenantId", ""),
)

# Reuse one adapter and bot instance across Function invocations.
ADAPTER = BotFrameworkAdapter(SETTINGS)
BOT = DPSBot()

@app.route(route="messages", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    # Azure Bot Service posts each incoming activity to this /api/messages route.
    body = req.get_json()

    # Convert the request JSON into a Bot Framework Activity object.
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    # The adapter validates the request, creates a turn context, and calls BOT.on_turn.
    await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)

    # Normal message activities are acknowledged with HTTP 200 after the bot sends its reply.
    return func.HttpResponse(status_code=200)
    
    # If a user mentions @bot inteam from their own chat or from any where then 
    # query the owners of the UC group with graph API (https://learn.microsoft.com/en-us/azure/governance/resource-graph/first-query-rest-api?tabs=powershell)
    # prep the request body json with the details of the request.
    # run a query to graph API to get the owners of the UC group with REST API URI
    # with owner details in the request body json, mention the owners in the same thread saying As you are the owner of so and so group please approve the request.

    # mention them in the same thread. saying As you are the owner of so and so group please approve the request..