# PRD Ticket Agent - MCP Setup Complete! 🎉

Your PRD Ticket Agent has been successfully set up as an MCP server and is now accessible in Cursor!

## What's Been Set Up

### 1. ✅ MCP Server
- **Location**: `/Users/mohaned.saleh/prd-ticket-agent/mcp_server.py`
- **Configuration**: Added to `~/.config/cursor/mcp.json`
- **Status**: Ready to use in Cursor chat

### 2. ✅ macOS Application
- **Location**: `/Users/mohaned.saleh/PRDTicketAgent.app` (also copied to Desktop)
- **Custom Icon**: Created with a document and checkmark design
- **Dock**: Added to your dock for easy access

### 3. ✅ Available Tools in Cursor

You can now use these tools in Cursor chat:

1. **`create_prd`** - Create a Product Requirements Document
   - Usage: "Create a PRD for [your project description]"
   - The agent will gather context from Notion and generate a comprehensive PRD

2. **`create_ticket`** - Create a Jira ticket linked to a PRD
   - Usage: "Create a ticket for project PROJ based on [PRD description]"

3. **`get_notion_context`** - Retrieve context from Notion
   - Usage: "Get the current Notion context"

## How to Use

### In Cursor Chat:
Simply ask me to create PRDs or tickets! For example:
- "Create a PRD for adding user authentication"
- "Create a ticket for the authentication PRD in project ENG"
- "Get the current Notion context"

### Via the Dock App:
Click the "PRD Ticket Agent" icon in your dock to:
- Open Cursor with the agent directory
- Get a notification that the agent is ready

### Via CLI (Terminal):
```bash
cd /Users/mohaned.saleh/prd-ticket-agent
python3 cli.py prd --description "Your project description"
python3 cli.py ticket --prd-id "notion_id" --project PROJ --description "Ticket description"
```

## Configuration

The agent uses environment variables from `.env` file. Make sure your `.env` file has:
- `NOTION_API_KEY`
- `GEMINI_API_KEY`
- `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` (for ticket creation)
- Notion page IDs for context

## Next Steps

1. **Restart Cursor** to load the MCP server configuration
2. **Test it out** by asking me to create a PRD in chat
3. **Move the app** from Desktop to Applications if you want (drag and drop)
4. **Keep in Dock** - Right-click the dock icon → Options → Keep in Dock

## Troubleshooting

If the MCP server doesn't work:
1. Check that Python 3.9+ is available: `python3 --version`
2. Verify the MCP config: `cat ~/.config/cursor/mcp.json`
3. Check the server script is executable: `ls -la /Users/mohaned.saleh/prd-ticket-agent/mcp_server.py`
4. Restart Cursor completely

Enjoy your PRD Ticket Agent! 🚀

