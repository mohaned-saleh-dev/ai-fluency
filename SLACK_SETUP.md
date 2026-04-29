# Slack Thread Manager Setup

## Quick Start

To use the Slack Thread Manager, you need a Slack API token with the right permissions.

## Option 1: User OAuth Token (Recommended)

This allows the script to access your personal Slack messages and threads.

### Steps:

1. **Go to Slack API Apps**: https://api.slack.com/apps

2. **Create a new app** (or use an existing one):
   - Click "Create New App"
   - Choose "From scratch"
   - Name it (e.g., "Thread Manager")
   - Select your workspace

3. **Add OAuth Scopes**:
   - Go to "OAuth & Permissions" in the sidebar
   - Scroll to "User Token Scopes"
   - Add the following scopes:
     - **Read Scopes (required):**
       - `channels:history` - View messages in public channels
       - `groups:history` - View messages in private channels
       - `im:history` - View direct messages
       - `mpim:history` - View group direct messages
       - `channels:read` - View basic channel information
       - `groups:read` - View basic private channel information
       - `im:read` - View basic direct message information
       - `mpim:read` - View basic group direct message information
       - `users:read` - View people in the workspace
     - **Write Scopes (to mark threads as read):**
       - `channels:write` - Mark channels as read
       - `groups:write` - Mark private channels as read
       - `im:write` - Mark direct messages as read
       - `mpim:write` - Mark group direct messages as read

4. **Install to Workspace**:
   - Scroll to the top of "OAuth & Permissions"
   - Click "Install to Workspace"
   - Authorize the app

5. **Copy the User OAuth Token**:
   - After installation, you'll see "OAuth Tokens for Your Workspace"
   - Copy the "User OAuth Token" (starts with `xoxp-`)

6. **Set the token**:
   ```bash
   export SLACK_USER_TOKEN='xoxp-your-token-here'
   ```

   Or add it to your `.env` file:
   ```
   SLACK_USER_TOKEN=xoxp-your-token-here
   ```

## Option 2: Bot Token (Limited)

Bot tokens have limitations - they can't mark messages as read for users. If you use a bot token, the script will still identify important threads but won't be able to mark threads as read.

### Steps:

1. Follow steps 1-2 from Option 1
2. Add Bot Token Scopes (similar to above)
3. Install to workspace
4. Copy the Bot User OAuth Token (starts with `xoxb-`)
5. Set it:
   ```bash
   export SLACK_BOT_TOKEN='xoxb-your-token-here'
   ```

## Running the Script

Once you have your token set:

```bash
python3 slack_thread_manager.py
```

The script will:
1. ✅ Fetch all your conversations (channels, DMs, groups)
2. ✅ Find all threads with replies
3. ✅ Identify important threads (based on keywords, mentions, recency)
4. ✅ Mark old/unimportant threads as read
5. ✅ Generate a report with links to important threads

## Configuration

You can customize the script behavior by editing `slack_thread_manager.py`:

- `DAYS_OLD_THRESHOLD`: Threads older than this (default: 30 days) are considered old
- `IMPORTANT_KEYWORDS`: List of keywords that make a thread important

## Report Output

The script generates:
- Console output with summary
- A text file: `slack_important_threads_YYYYMMDD_HHMMSS.txt` with all important thread links

## Troubleshooting

**Error: "channel_not_found"**
- This is normal for some channels you don't have access to
- The script will skip them

**Error: "missing_scope"**
- You need to add the required OAuth scopes (see Option 1)
- Reinstall the app to workspace after adding scopes

**No threads found**
- Make sure you're part of conversations with threads
- Check that the scopes are correctly set

