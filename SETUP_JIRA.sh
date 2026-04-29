#!/bin/bash
# Quick script to set Jira credentials

echo "🔧 Jira Credentials Setup"
echo "========================="
echo ""

read -p "Enter your Jira URL (e.g., https://your-company.atlassian.net): " JIRA_URL
read -p "Enter your Jira email: " JIRA_EMAIL
read -p "Enter your Jira API token: " JIRA_API_TOKEN

# Update .env file
cd "$(dirname "$0")"

# Remove old Jira entries
sed -i.bak '/^JIRA_/d' .env 2>/dev/null || sed -i '' '/^JIRA_/d' .env 2>/dev/null

# Add new entries
echo "" >> .env
echo "# Jira API Configuration" >> .env
echo "JIRA_URL=$JIRA_URL" >> .env
echo "JIRA_EMAIL=$JIRA_EMAIL" >> .env
echo "JIRA_API_TOKEN=$JIRA_API_TOKEN" >> .env

echo ""
echo "✅ Jira credentials saved to .env file!"
echo ""
echo "To verify, run:"
echo "  python3 -c \"from prd_ticket_agent.config import load_context_from_env; ctx = load_context_from_env(); print('✅ Jira configured!' if ctx.jira_url else '❌ Not configured')\""












