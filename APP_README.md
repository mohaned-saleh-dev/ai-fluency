# PRD Ticket Agent - macOS App

## Quick Start

1. **Double-click** `PRD Ticket Agent.app` in Finder
2. The app will open with a chat interface
3. Start chatting with the PRD agent!

## Features

- 💬 Chat-based interface for interacting with the PRD agent
- 📝 Create PRDs by describing your project
- 🎫 Generate Jira tickets
- 🤖 Powered by Gemini AI

## Configuration

The app will automatically load configuration from:
1. Environment variables (from your shell)
2. `.env` file in the project root
3. `config.json` file in the project root

**Required:**
- `GEMINI_API_KEY` - Your Google Gemini API key

**Optional:**
- `NOTION_API_KEY` - For Notion integration
- `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` - For Jira integration

## Usage Examples

**Create a PRD:**
```
You: Create a PRD for a user authentication feature
```

**Ask questions:**
```
You: What information do I need to create a PRD?
```

**Create a ticket:**
```
You: Create a ticket for implementing login UI
```

## Troubleshooting

**App won't open:**
- Make sure Python 3.8+ is installed
- Check that tkinter is available: `python3 -c "import tkinter"`
- Try running from terminal: `open "PRD Ticket Agent.app"`

**Agent not initialized:**
- Set your `GEMINI_API_KEY` environment variable
- Or create a `.env` file with: `GEMINI_API_KEY=your_key_here`

**Icon not showing:**
- The icon should appear automatically in the Dock
- If not, try rebuilding: `touch "PRD Ticket Agent.app"`












