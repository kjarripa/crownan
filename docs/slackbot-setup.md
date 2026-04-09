# Slack Bot Setup

## Prerequisites

- `crownan` installed with the slackbot extra: `pip install crownan[slackbot]`
- Managed Agent already deployed (run `crownan-agent-setup` first -- see [agent-setup.md](agent-setup.md))
- `KRONAN_API_KEY` and `ANTHROPIC_API_KEY` configured in `.env.local`

## 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** > **From scratch**
3. Name: "Crownan" (or whatever you prefer)
4. Pick your workspace

## 2. Enable Socket Mode

1. Go to **Socket Mode** in the sidebar
2. Enable Socket Mode
3. Create an App-Level Token with scope `connections:write`
4. Save the token as `SLACK_APP_TOKEN` in `.env.local`

## 3. Configure Bot Permissions

Go to **OAuth & Permissions** > **Bot Token Scopes** and add:

| Scope | Purpose |
|---|---|
| `app_mentions:read` | Receive @crownan mentions |
| `chat:write` | Send messages |
| `im:history` | Read DM history |
| `im:read` | View DM metadata |
| `im:write` | Start DMs |

## 4. Enable Events

Go to **Event Subscriptions**:

1. Enable Events
2. Subscribe to bot events:
   - `app_mention`
   - `message.im`

## 5. Enable App Home Messages

1. Go to **App Home** in the sidebar
2. Under "Show Tabs", enable the **Messages Tab**
3. Check the box: **"Allow users to send Slash commands and messages from the messages tab"**

Without this step, users won't be able to DM the bot.

## 6. Install the App

1. Go to **Install App**
2. Install to your workspace
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. Save as `SLACK_BOT_TOKEN` in `.env.local`

> **Note:** If you change any permissions or settings after installing, you must **Reinstall to Workspace** for the changes to take effect.

## 7. Configure Environment

Your `.env.local` should now have all four keys:

```
KRONAN_API_KEY=act_...
ANTHROPIC_API_KEY=sk-ant-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

## 8. Run the Bot

```bash
python -m crownan.slackbot
```

The bot connects via Socket Mode -- no public URL or webhook setup required.

## Usage

- **DM the bot** -- send any message in Icelandic or English
- **@mention in channels** -- `@Crownan hvad er i korfunni minni?`
- **Reset session** -- type `/reset` or `/byrja aftur` as a regular message in a DM (these are not Slack slash commands, just message text the bot recognizes)

## Example Queries

| Icelandic | What it does |
|---|---|
| `hvad er i korfunni minni?` | View your cart |
| `baettu vid gurkum i korfuna` | Add cucumbers to cart |
| `budu til nyja korfu med somu pontun og sidast` | Reorder your last order |
| `leitadu ad mjolk` | Search for milk |
| `hvada flokkar eru i bodi?` | List categories |
| `hreinsa korfuna` | Clear the cart |
