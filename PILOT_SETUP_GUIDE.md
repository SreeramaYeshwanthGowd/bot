# DPSBot Pilot Setup Guide

This guide is for the first safe milestone only: prove that `@DPSBot` in Teams can reach an Azure-hosted bot and return an Adaptive Card.

The production guide in the repository is useful, but it jumps quickly into Graph permissions, owner resolution, audit channels, Jira, storage, and proactive messages. Do not start there. Start here.

## 1. What The Existing Material Says

From the architecture guide and the Teams chat history:

- Most real requests are access-related. The repeated pattern is Databricks access through Entra groups such as `UC|Sch|catalog.schema|Read`.
- The full design wants Microsoft Graph later so the bot can find Entra group owners, post audit messages, and DM approvers.
- The chat history confirms the same categories as the guide: access requests, Genie access, workspace onboarding, cluster/warehouse issues, Power BI connection issues, GitHub auth, and feature-preview requests.
- There are already simple support-request style test messages in the chat history, so a small Teams pilot is a realistic first step.

For this first milestone, none of that production workflow is required.

## 2. Pilot Scope

Build only this path:

```text
Teams message with @DPSBot
  -> Azure Bot Service Teams channel
  -> Azure Function HTTP endpoint /api/messages
  -> Python bot handler
  -> Adaptive Card response in Teams
```

Do not build these yet:

- Microsoft Graph calls.
- Graph application permissions.
- Managed Identity Graph grants.
- Jira integration.
- Azure Table Storage request/session state.
- Owner lookup.
- Owner approval DMs.
- Databricks API calls.
- Audit channel posting.
- App-wide Teams deployment.

This keeps the first test small, reversible, and easy to explain to an admin.

## 3. Permission Model For This Pilot

You need only a few permissions.

### Azure

You need permission to create or use:

- One resource group, or Contributor on an existing test resource group.
- One Storage Account, required by Azure Functions runtime.
- One Linux Azure Function App on Consumption plan.
- One Azure Bot resource on the free F0 tier.
- One Entra App Registration with a client secret, unless your admin creates it for you.

You do not need Microsoft Graph API permissions for this pilot.

### Teams

You need permission to:

- Create a private test team, or have an admin create one for you.
- Add a custom Teams app to that test team, or have Teams admin upload/allow it only for you.
- Add the bot app to the test team.

### Entra ID

For this pilot app registration:

- Supported account type: single tenant is preferred for an org-only test.
- API permissions: leave default only. Do not add Graph permissions.
- Secret: required for Bot Service auth in this minimal sample.

## 4. Important Teams Isolation Choice

If you want a channel-like test that is visible only to you, use a private team with only you as a member, then test in its standard `General` channel.

Avoid using a private channel inside an existing team for this first bot test. Teams app and bot behavior in private/shared channels has limitations, and testing in a normal channel inside a private team is less surprising.

Recommended setup:

1. Teams -> Join or create a team -> Create team.
2. Choose `From scratch`.
3. Choose `Private`.
4. Name it something clearly temporary, for example `DPSBot Pilot - YourName`.
5. Do not add other members.
6. Use the default `General` channel for the test.

Reality check: this is private from normal Teams users, but Teams admins, compliance/eDiscovery, and tenant administrators may still have administrative visibility. Nothing in Microsoft 365 is truly hidden from tenant governance.

If your organization blocks team creation, ask a Teams admin for a temporary private team with only you as owner/member.

## 5. Local Prerequisites

Install these locally if you want to develop or test from VS Code:

- Python 3.11.
- Azure Functions Core Tools v4.
- Azure CLI.
- Optional for local Teams testing: ngrok or Microsoft Dev Tunnels.

Check versions:

```bash
python3 --version
func --version
az --version
```

If `func` is missing on Linux, install Azure Functions Core Tools v4 using Microsoft package instructions for your distribution.

## 6. Create The Entra App Registration

Use the Azure portal for the first run so every permission is visible.

1. Go to Azure portal.
2. Open `Microsoft Entra ID`.
3. Open `App registrations`.
4. Select `New registration`.
5. Name: `DPSBot Pilot YourName`.
6. Supported account types: `Accounts in this organizational directory only`.
7. Redirect URI: leave empty.
8. Select `Register`.

Save these values from the Overview page:

- Application client ID: this becomes `MicrosoftAppId`.
- Directory tenant ID: this becomes `MicrosoftAppTenantId`.

Create the bot secret:

1. App registration -> `Certificates & secrets`.
2. `New client secret`.
3. Description: `dpsbot-pilot-bot-secret`.
4. Expiry: choose a short pilot period if possible, for example 3 or 6 months.
5. Select `Add`.
6. Copy the secret value immediately. You will not be able to see it again.

Do not add Graph API permissions.

## 7. Create Azure Resources

Use a clearly named pilot resource group. Example names:

```bash
RESOURCE_GROUP="rg-dpsbot-pilot-yourname"
LOCATION="northeurope"
STORAGE_NAME="stdpsbotpilot$RANDOM"
FUNCTIONAPP_NAME="func-dpsbot-pilot-yourname"
BOT_NAME="bot-dpsbot-pilot-yourname"
APP_ID="paste-application-client-id"
APP_SECRET="paste-client-secret"
TENANT_ID="paste-tenant-id"
```

Create the resource group:

```bash
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"
```

Create the Storage Account for the Function runtime:

```bash
az storage account create \
  --name "$STORAGE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2
```

Create the Python Function App:

```bash
az functionapp create \
  --resource-group "$RESOURCE_GROUP" \
  --consumption-plan-location "$LOCATION" \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name "$FUNCTIONAPP_NAME" \
  --storage-account "$STORAGE_NAME" \
  --os-type Linux
```

Configure the bot app settings on the Function App:

```bash
az functionapp config appsettings set \
  --name "$FUNCTIONAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    "MicrosoftAppId=$APP_ID" \
    "MicrosoftAppPassword=$APP_SECRET" \
    "MicrosoftAppTenantId=$TENANT_ID"
```

For this pilot, do not enable Managed Identity for Graph, and do not grant Graph permissions.

## 8. Deploy The Function Code

The folder `dpsbot-mention-card-pilot` already exists in this workspace because it was generated for this pilot. You do not need to create it again. Step into that existing folder before running the commands.

If your Azure Function App is already connected to a Git repo through Deployment Center, push this pilot code to that connected repo instead of running `func azure functionapp publish`. Azure will deploy from the branch configured in Deployment Center.

Important: for the simplest Azure Functions deployment, the contents of this folder should be at the root of the connected repo:

```text
connected-repo/
  function_app.py
  host.json
  requirements.txt
  src/
  .funcignore
```

Do not push it as `connected-repo/dpsbot-mention-card-pilot/function_app.py` unless your GitHub Actions or Azure DevOps pipeline is explicitly configured to deploy from that subfolder.

Typical repo push flow:

```bash
git clone <YOUR_CONNECTED_REPO_URL>
cd <YOUR_CONNECTED_REPO_FOLDER>

# Copy the pilot files into the repo root.
# From /home/bglpg05etwm/ABT, this copies the contents, not the parent folder.
cp -R /home/bglpg05etwm/ABT/dpsbot-mention-card-pilot/. .

git status
git add function_app.py host.json requirements.txt src .funcignore .gitignore local.settings.sample.json teams-manifest scripts README.md PILOT_SETUP_GUIDE.md
git commit -m "Add DPSBot Teams mention card pilot"
git push
```

After the push, go to your Function App in Azure Portal:

1. Open `Deployment Center`.
2. Confirm the connected branch is the branch you pushed to.
3. Open `Logs` and verify the deployment starts and succeeds.
4. Open `Functions` and confirm the `messages` function appears.

If your connected repo already has other Function App code, do not overwrite it blindly. Add this pilot in a separate branch and compare files first.

If your terminal is at the workspace root, `/home/bglpg05etwm/ABT`, run:

```bash
cd dpsbot-mention-card-pilot
```

If your terminal already shows `/home/bglpg05etwm/ABT/dpsbot-mention-card-pilot`, skip the `cd` command and run only:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Deploy with Azure Functions Core Tools:

```bash
func azure functionapp publish "$FUNCTIONAPP_NAME" --python
```

The endpoint will be:

```text
https://FUNCTIONAPP_NAME.azurewebsites.net/api/messages
```

For example:

```text
https://func-dpsbot-pilot-yourname.azurewebsites.net/api/messages
```

The endpoint is anonymous at the Azure Functions HTTP layer because Bot Framework authentication is handled by the Bot Framework adapter using `MicrosoftAppId` and `MicrosoftAppPassword`. This is the normal bot hosting pattern.

## 9. Create The Azure Bot Resource

Portal path:

1. Azure portal -> search `Azure Bot`.
2. Select `Create`.
3. Bot handle: `dpsbot-pilot-yourname`.
4. Subscription/resource group: use your pilot resource group.
5. Pricing tier: `F0`.
6. Microsoft App ID type: use existing app registration if the portal offers that option.
7. Microsoft App ID: paste the app registration client ID.
8. App secret: paste the client secret.
9. Messaging endpoint: use `https://FUNCTIONAPP_NAME.azurewebsites.net/api/messages`.
10. Create.

After it is created:

1. Open the Azure Bot resource.
2. Open `Channels`.
3. Select `Microsoft Teams`.
4. Accept terms if prompted.
5. Save or apply.

Do not enable other channels for this pilot.

## 10. Build The Teams App Package

Teams needs an app manifest that points to the bot app ID.

Run this from the pilot folder, replacing values:

```bash
python scripts/build_teams_package.py \
  --app-id "$APP_ID" \
  --function-host "$FUNCTIONAPP_NAME.azurewebsites.net" \
  --short-name "DPSBotPilot" \
  --full-name "DPSBot Pilot - Mention Card Test" \
  --developer-name "Your Organization" \
  --website-url "https://your-company.example" \
  --privacy-url "https://your-company.example/privacy" \
  --terms-url "https://your-company.example/terms"
```

This creates:

```text
teams-manifest/dist/dpsbot-pilot-teams-app.zip
```

The script also creates valid placeholder PNG icons so the package can upload. Replace the icons later if you publish beyond the pilot.

## 11. Upload The App To Teams Carefully

Preferred pilot path:

1. Open Microsoft Teams.
2. Open `Apps`.
3. Select `Manage your apps` or `Upload an app`.
4. Choose `Upload a custom app`.
5. Choose `Upload for me or my teams`.
6. Select `teams-manifest/dist/dpsbot-pilot-teams-app.zip`.
7. Add it only to your private pilot team.

If `Upload a custom app` is blocked, ask Teams admin for one of these low-risk options:

- Enable custom app upload only for your account through a Teams app permission/setup policy.
- Upload the package to the tenant app catalog but make it available only to your account or pilot team.
- Create the private pilot team and install the app there for you.

Do not publish the app org-wide for this milestone.

## 12. Test In Teams

In your private pilot team's `General` channel, send:

```text
@DPSBotPilot test
```

Expected result:

- An Adaptive Card appears in the channel thread.
- The card says the Teams message reached Azure Bot Service, Azure Functions, and the Python handler.
- The card facts show conversation type and channel ID.
- The card says no Graph, Jira, Databricks, or storage actions were performed.

Optional submit test:

1. Select `I can see the card`.
2. Expected bot response: `Pilot button click received. Adaptive Card submit is working.`

## 13. Observe Logs

Portal path:

1. Open the Function App.
2. Go to `Log stream`.
3. Mention the bot again.
4. Confirm the function invocation appears.

Useful things to check:

- Did the function receive a request?
- Did Bot Framework auth reject the activity?
- Did the bot handler log an exception?

## 14. Common Troubleshooting

### The bot does not appear in Teams search

The Teams app package may not be uploaded or allowed by policy. Check custom app upload settings or ask Teams admin to assign the app only to you.

### The bot can be added but does not respond

Check the Azure Bot messaging endpoint. It must be exactly:

```text
https://FUNCTIONAPP_NAME.azurewebsites.net/api/messages
```

No trailing slash is needed.

### The Function App logs show unauthorized or auth errors

Check these values match the Entra app registration and Azure Bot resource:

- `MicrosoftAppId`
- `MicrosoftAppPassword`
- `MicrosoftAppTenantId`

If you rotated the secret, update both the Azure Bot resource and Function App setting.

### Teams says the app package is invalid

Check:

- Manifest `id` equals the App Registration client ID.
- Manifest `bots[0].botId` equals the same App Registration client ID.
- `validDomains` contains only the host name, for example `func-dpsbot-pilot-yourname.azurewebsites.net`.
- Icons are PNG files and included in the zip.

### You tried a private channel and the bot does not work

Move the test to a standard channel inside a private team. That gives you the isolation you want without private-channel bot limitations.

## 15. Optional Local Tunnel Test

Only use this if you are comfortable temporarily exposing your local function through a tunnel.

Create a real `local.settings.json` from the sample:

```bash
cp local.settings.sample.json local.settings.json
```

Fill in:

- `MicrosoftAppId`
- `MicrosoftAppPassword`
- `MicrosoftAppTenantId`

Start locally:

```bash
func start
```

In another terminal:

```bash
ngrok http 7071
```

Temporarily set the Azure Bot messaging endpoint to:

```text
https://YOUR-NGROK-HOST.ngrok-free.app/api/messages
```

After local testing, set the messaging endpoint back to the Azure Function URL.

## 16. Rollback And Cleanup

If anything feels wrong, rollback is simple:

1. Remove the app from the Teams pilot team.
2. Disable the Teams channel on the Azure Bot resource.
3. Delete the Azure Bot resource.
4. Delete the Function App.
5. Delete the Storage Account.
6. Delete the pilot resource group if it contains only pilot resources.
7. Delete the Entra app registration, or at least delete its client secret.

CLI cleanup if the resource group contains only pilot resources:

```bash
az group delete --name "$RESOURCE_GROUP"
```

Then delete the app registration in Entra ID if it was created only for this pilot.

## 17. What Comes After This Pilot

Only after the card appears reliably should you add the next layer.

Suggested order:

1. Add a two-step Adaptive Card flow in the same Teams thread.
2. Add Azure Table Storage for simple session state.
3. Add an audit channel, still without Graph proactive DMs.
4. Add Graph read permissions for group lookup only.
5. Add owner resolution from `UC|Sch|catalog.schema|Read` groups.
6. Add owner approval cards.
7. Add Jira integration.

This order keeps permissions review manageable.

## 18. Questions To Confirm Before You Touch The Org Tenant

Ask or verify these before you deploy:

- Can you create a private Microsoft Team, or should a Teams admin create it?
- Is custom app upload enabled for your user account?
- Are you allowed to create App Registrations in Entra ID?
- Are you allowed to create Azure Bot resources in the subscription?
- Which Azure subscription and region should the pilot use?
- Does your org prefer Teams apps to be uploaded through Teams Admin Center instead of sideloaded?
- Should the pilot app name include `Pilot` or `Test` so nobody confuses it with production?
