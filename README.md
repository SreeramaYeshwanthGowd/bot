# DPSBot Mention Card Pilot

This folder is a deliberately small first step for the DPSBot idea.

It does one thing only:

1. A user mentions the bot in a Microsoft Teams test team/channel.
2. Azure Bot Service forwards the activity to an Azure Function.
3. The Python bot handler returns one Adaptive Card.
4. An optional button click confirms Adaptive Card submit events work.

It does not call Microsoft Graph, Jira, Databricks, or Azure Storage application tables. It does not read or change any Databricks access. It does not send proactive messages. Those are later phases after the Teams and Bot Framework plumbing is proven.

Start with [PILOT_SETUP_GUIDE.md](PILOT_SETUP_GUIDE.md).

## Files

- [function_app.py](function_app.py) - Azure Functions HTTP endpoint for Bot Framework activities.
- [src/dps_bot.py](src/dps_bot.py) - Minimal Teams bot handler.
- [src/cards.py](src/cards.py) - The pilot Adaptive Card.
- [requirements.txt](requirements.txt) - Python dependencies.
- [host.json](host.json) - Azure Functions host settings.
- [local.settings.sample.json](local.settings.sample.json) - Local settings template. Do not commit a real `local.settings.json`.
- [teams-manifest/manifest.sample.json](teams-manifest/manifest.sample.json) - Readable manifest template.
- [scripts/build_teams_package.py](scripts/build_teams_package.py) - Builds a Teams app package with placeholder PNG icons.
