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

Do not build these for the first connectivity milestone:

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

This keeps the first test small, reversible, and easy to explain to an admin. The Graph owner lookup pilot is a later step covered in section 17.

## 3. Permission Model For This Pilot

You need only a few permissions.

### Azure

You need permission to create or use:

- One resource group, or Contributor on an existing test resource group.
- One Storage Account, required by Azure Functions runtime.
- One Linux Azure Function App on Consumption plan.
- One Azure Bot resource on the free F0 tier.
- One Entra App Registration with a client secret, unless your admin creates it for you.

You do not need Microsoft Graph API permissions for the first connectivity pilot. Add them only when you start the owner lookup phase in section 17.

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

Do not add Graph API permissions for the first connectivity test. Add them later only for the owner lookup phase in section 17.

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

For the first connectivity test, do not enable Managed Identity for Graph, and do not grant Graph permissions. The later owner lookup phase uses Graph application permissions as described in section 17.

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
- The card shows only four input fields: `catalog`, `schema`, `table`, and `message`.
- Submitting the card makes the bot reply: `Details captured.`
- The submitted values are written to Application Insights logs for inspection.

Optional submit test:

1. Enter test values in all four fields.
2. Select `Submit`.
3. Expected bot response: `Details captured.`

## 13. Observe Logs

The Function App uses workspace-based Application Insights. The most reliable place to see the submitted form values is the Application Insights `Logs` blade, not the Azure Bot resource logs.

Portal path:

1. Open Azure portal.
2. Open the Application Insights resource named like the Function App, for example `dps-bot-func`.
3. Open `Logs`.
4. Run this query:

```kusto
AppTraces
| where TimeGenerated > ago(2h)
| where AppRoleName == "dps-bot-func"
| where Message contains "DPSBot submitted details"
| order by TimeGenerated desc
| project TimeGenerated, Message, SeverityLevel
```

Expected log line shape:

```text
DPSBot submitted details: {'catalog': '...', 'schema': '...', 'table': '...', 'message': '...'}
```

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

## 17. Next Phase: Graph Owner Lookup Pilot

Do this only after the basic form card appears reliably and `Details captured.` works.

Goal for this phase:

```text
User enters catalog/schema/table/message
  -> bot derives the expected UC group display name from the submitted fields
  -> bot queries Microsoft Graph for that group
  -> bot queries Microsoft Graph for the group owners
  -> bot displays the owner names back in the same Teams thread
```

For the first owner lookup test, use a schema-level group like the screenshot:

```text
UC|Sch|<catalog>.<schema>|Write
```

Example:

```text
UC|Sch|aba_az_ne_prod.msgraph_cleansed|Write
```

The current card also asks for `table`. For this schema-level pilot, keep collecting `table` and `message`, but build the first Graph lookup from `catalog` and `schema` only. If you later need table-level ownership, use a separate pattern such as:

```text
UC|Tbl|<catalog>.<schema>.<table>|Write
```

### 17.1 You Create A Sample UC-Style Group

Portal path:

1. Azure portal -> `Microsoft Entra ID`.
2. Open `Groups`.
3. Select `New group`.
4. Group type: `Security`.
5. Group name: `UC|Sch|aba_az_ne_prod.msgraph_cleansed|Write`.
6. Group description: `Entra group for aba_az_ne_prod.msgraph_cleansed with Write access level.`
7. Membership type: `Assigned`.
8. Owners: add yourself.
9. Members: leave empty for this owner-lookup pilot unless you also want to test membership later.
10. Create the group.

Save these values from the group Overview page:

- Display name.
- Object ID.
- Owner count.

For the first bot test, enter these values in the Adaptive Card:

```text
catalog: aba_az_ne_prod
schema: msgraph_cleansed
table: sample_table
message: test owner lookup
```

The bot should derive and query this existing group display name:

```text
UC|Sch|aba_az_ne_prod.msgraph_cleansed|Write
```

### 17.2 Add Microsoft Graph Permissions To The Bot App

Use the same Entra app registration that backs the Azure Bot resource and Function App settings.

Portal path:

1. Azure portal -> `Microsoft Entra ID`.
2. Open `App registrations`.
3. Open the DPSBot app registration.
4. Open `API permissions`.
5. Select `Add a permission`.
6. Choose `Microsoft Graph`.
7. Choose `Application permissions`.
8. Add these permissions:
   - `Group.Read.All`
   - `GroupMember.Read.All`
9. Select `Add permissions`.
10. Select `Grant admin consent` for the tenant.

Why these permissions:

- `Group.Read.All` lets the app find the group by display name.
- `GroupMember.Read.All` lets the app read group owners.

Do not add broad permissions such as `Directory.ReadWrite.All` for this pilot.

### 17.3 Confirm Function App Settings

The Function App already needs these settings for bot authentication, and the owner lookup can reuse them for Graph client credentials:

```text
MicrosoftAppId
MicrosoftAppPassword
MicrosoftAppTenantId
```

Confirm they are configured on the Function App:

```bash
az functionapp config appsettings list \
  --name "$FUNCTIONAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "[?name=='MicrosoftAppId' || name=='MicrosoftAppTenantId' || name=='MicrosoftAppPassword'].{name:name,configured:length(value) > \`0\`}" \
  -o table
```

Do not print or paste the secret value into chat, screenshots, logs, or documentation.

### 17.4 Graph Calls The Bot Will Need

The code change for this phase should do these calls with the app-only client credentials flow.

Token endpoint:

```text
POST https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
```

Token request fields:

```text
client_id=<MicrosoftAppId>
client_secret=<MicrosoftAppPassword>
scope=https://graph.microsoft.com/.default
grant_type=client_credentials
```

Find the group by exact display name:

```http
GET https://graph.microsoft.com/v1.0/groups?$filter=displayName eq 'UC|Sch|aba_az_ne_prod.msgraph_cleansed|Write'&$select=id,displayName
```

Then list the group owners:

```http
GET https://graph.microsoft.com/v1.0/groups/<group-id>/owners?$select=id,displayName,userPrincipalName,mail
```

Expected bot output for this pilot can be simple text, for example:

```text
Found owners for UC|Sch|aba_az_ne_prod.msgraph_cleansed|Write:
- Owner Name <owner@company.com>
```

If no owners are found, the bot should say:

```text
No owners found for UC|Sch|aba_az_ne_prod.msgraph_cleansed|Write.
```

If the group is not found, the bot should say:

```text
No matching group found for UC|Sch|aba_az_ne_prod.msgraph_cleansed|Write.
```

### 17.5 Code Update Checklist For The Next Step

When you implement the owner lookup, keep the change small:

1. Keep the existing Adaptive Card fields: `catalog`, `schema`, `table`, and `message`.
2. On submit, derive the existing group display name: `UC|Sch|{catalog}.{schema}|Write`.
3. Request a Graph token using `MicrosoftAppId`, `MicrosoftAppPassword`, and `MicrosoftAppTenantId`.
4. Query Graph for the group by exact display name.
5. Query Graph for owners using the returned group ID.
6. Send owner names and email/UPN back to the same Teams thread.
7. Log the group name, group ID, and owner count; do not log secrets or access tokens.

Suggested dependency if using HTTP calls from Python:

```text
requests
```

Add it to `requirements.txt` only when you implement the Graph calls.

### 17.6 Rollback For This Phase

If the Graph test is not approved or does not work:

1. Remove the Graph API permissions from the app registration.
2. Remove admin consent if your tenant process requires it.
3. Delete the sample UC-style group.
4. Revert the code to the form-only version.

## 18. What Comes After The Owner Lookup Pilot

Only after owner lookup works should you add the next layer.

Suggested order:

1. Add a cleaner owner response card in the same Teams thread.
2. Add owner mention formatting in Teams.
3. Add Azure Table Storage for simple request/session state.
4. Add an audit channel, still without proactive DMs.
5. Add owner approval cards.
6. Add Jira integration.

This order keeps permissions review manageable.

## 19. Questions To Confirm Before You Touch The Org Tenant

Ask or verify these before you deploy:

- Can you create a private Microsoft Team, or should a Teams admin create it?
- Is custom app upload enabled for your user account?
- Are you allowed to create App Registrations in Entra ID?
- Are you allowed to create Azure Bot resources in the subscription?
- Which Azure subscription and region should the pilot use?
- Does your org prefer Teams apps to be uploaded through Teams Admin Center instead of sideloaded?
- Should the pilot app name include `Pilot` or `Test` so nobody confuses it with production?
