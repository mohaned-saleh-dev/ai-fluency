# Installation Guide

## PRD Ticket Agent - Installation Instructions

This guide will help you install the PRD Ticket Agent as a standalone application.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation Methods

### Method 1: Install from Local Directory (Recommended)

1. **Navigate to the project directory:**
   ```bash
   cd prd-ticket-agent
   ```

2. **Install the package:**
   ```bash
   pip install -e .
   ```
   
   The `-e` flag installs in "editable" mode, so changes to the code are immediately available.

3. **Verify installation:**
   ```bash
   prd-agent --help
   ```
   
   You should see the help message with available commands.

### Method 2: Install as Regular Package

1. **Navigate to the project directory:**
   ```bash
   cd prd-ticket-agent
   ```

2. **Install the package:**
   ```bash
   pip install .
   ```

3. **Verify installation:**
   ```bash
   prd-agent --help
   ```

### Method 3: Install from Git Repository

If the repository is hosted on GitHub or another Git service:

```bash
pip install git+https://github.com/yourusername/prd-ticket-agent.git
```

## Configuration

After installation, you need to configure the agent with your API keys and credentials.

### Option 1: Environment Variables (Recommended)

Create a `.env` file in your home directory or project root:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Notion (optional but recommended)
NOTION_API_KEY=your_notion_api_key
NOTION_PRD_DATABASE_ID=your_prd_database_id
NOTION_TICKETS_DATABASE_ID=your_tickets_database_id
NOTION_ALL_PRDS_PAGE_ID=your_all_prds_page_id
NOTION_ALL_TICKETS_PAGE_ID=your_all_tickets_page_id
NOTION_SQUAD_PRIORITIES_PAGE_ID=your_squad_priorities_page_id

# Jira (optional, needed for ticket creation)
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your_email@company.com
JIRA_API_TOKEN=your_jira_api_token

# Optional
AI_CHATBOT_CSV_PATH=path/to/ai_chatbot_requirements.csv
GEMINI_MODEL_NAME=gemini-2.5-pro
```

### Option 2: Configuration File

Create a `config.json` file:

```json
{
  "gemini_api_key": "your_gemini_api_key_here",
  "notion_api_key": "your_notion_api_key",
  "notion_prd_database_id": "your_prd_database_id",
  "notion_tickets_database_id": "your_tickets_database_id",
  "notion_all_prds_page_id": "your_all_prds_page_id",
  "notion_all_tickets_page_id": "your_all_tickets_page_id",
  "notion_squad_priorities_page_id": "your_squad_priorities_page_id",
  "jira_url": "https://your-company.atlassian.net",
  "jira_email": "your_email@company.com",
  "jira_api_token": "your_jira_api_token",
  "ai_chatbot_csv_path": "path/to/ai_chatbot_requirements.csv",
  "gemini_model_name": "gemini-2.5-pro"
}
```

Then use it with the `--config` flag:
```bash
prd-agent prd --description "My project" --config config.json
```

## Usage

### Create a PRD

```bash
# Using description directly
prd-agent prd --description "Add user authentication feature"

# Using a file
prd-agent prd --file project_description.txt

# With custom config file
prd-agent prd --description "Feature X" --config my_config.json

# JSON output
prd-agent prd --description "Feature X" --format json
```

### Create a Jira Ticket

```bash
# With PRD ID from Notion
prd-agent ticket --prd-id "notion_page_id" --project PROJ --description "Implement login UI"

# With PRD JSON file
prd-agent ticket --prd-file prd.json --project PROJ --description "Implement login UI"
```

## Uninstallation

To uninstall the agent:

```bash
pip uninstall prd-ticket-agent
```

## Troubleshooting

### Command not found

If `prd-agent` command is not found after installation:

1. Check that Python's bin directory is in your PATH:
   ```bash
   echo $PATH | grep -i python
   ```

2. Try using the full path:
   ```bash
   python -m prd_ticket_agent.cli prd --help
   ```

3. Reinstall with user flag:
   ```bash
   pip install --user -e .
   ```

### Import errors

If you get import errors, make sure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### API Key errors

Make sure your `GEMINI_API_KEY` is set correctly:
```bash
echo $GEMINI_API_KEY
```

## Next Steps

- Read the [README.md](README.md) for detailed usage instructions
- Check [QUICKSTART.md](QUICKSTART.md) for a quick tutorial
- Review example usage in [example_usage.py](example_usage.py)












