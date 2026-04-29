# Jira Credentials Setup

## Quick Setup Options

You have 3 ways to set your Jira credentials. Choose the one that works best for you:

## Option 1: Environment Variables (Recommended)

Set these in your terminal session or add to `~/.zshrc`:

```bash
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_EMAIL="your_email@company.com"
export JIRA_API_TOKEN="your_jira_api_token"
```

**To make it permanent**, add to `~/.zshrc`:
```bash
echo 'export JIRA_URL="https://your-company.atlassian.net"' >> ~/.zshrc
echo 'export JIRA_EMAIL="your_email@company.com"' >> ~/.zshrc
echo 'export JIRA_API_TOKEN="your_jira_api_token"' >> ~/.zshrc
source ~/.zshrc
```

## Option 2: .env File (Easiest)

Create a `.env` file in the project root (`~/prd-ticket-agent/.env`):

```bash
cd ~/prd-ticket-agent
cat > .env << 'EOF'
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your_email@company.com
JIRA_API_TOKEN=your_jira_api_token
EOF
```

The agent will automatically load this file.

## Option 3: config.json File

Create a `config.json` file in the project root:

```json
{
  "jira_url": "https://your-company.atlassian.net",
  "jira_email": "your_email@company.com",
  "jira_api_token": "your_jira_api_token",
  "gemini_api_key": "your_gemini_key",
  "notion_api_key": "your_notion_key"
}
```

Then use it with: `prd-agent prd --description "..." --config config.json`

## Getting Your Jira API Token

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label (e.g., "PRD Agent")
4. Copy the token (you'll only see it once!)
5. Use your email address (not username) for `JIRA_EMAIL`

## Verify Your Setup

Test if your credentials work:

```bash
cd ~/prd-ticket-agent
python3 -c "
from prd_ticket_agent.config import load_context_from_env
context = load_context_from_env()
if context.jira_url and context.jira_email and context.jira_api_token:
    print('✅ Jira credentials configured!')
    print(f'   URL: {context.jira_url}')
    print(f'   Email: {context.jira_email}')
else:
    print('❌ Jira credentials missing')
"
```

## Priority Order

The agent checks credentials in this order:
1. Environment variables (highest priority)
2. `.env` file in project root
3. `config.json` file (if specified with `--config`)

## Security Note

⚠️ **Never commit your `.env` or `config.json` files to git!** They contain sensitive credentials.

Make sure `.env` is in your `.gitignore`:
```bash
echo ".env" >> ~/prd-ticket-agent/.gitignore
```












