# Quick Start - PRD Agent

## Access the Agent

**Easiest way:** Double-click `PRD Agent Chat.command` on your Desktop

**Or in terminal:**
```bash
cd ~/prd-ticket-agent
python3 chat_with_agent.py
```

**Or use the alias:**
```bash
prd-chat
```
(After opening a new terminal or running `source ~/.zshrc`)

## Usage

Once the chat starts, just type your requests:

- `create prd for user authentication feature`
- `help me write a PRD for a new dashboard`
- `what information do I need for a PRD?`
- `quit` to exit

## About the Warnings

You may see warnings about:
- Python 3.9 compatibility
- Deprecated packages

**These are safe to ignore** - the agent works fine despite these warnings. They're just compatibility notices from Google's libraries.

## Troubleshooting

**Agent not initialized:**
- Make sure `GEMINI_API_KEY` is set: `echo $GEMINI_API_KEY`
- Or create a `.env` file in the project directory with: `GEMINI_API_KEY=your_key`

**Command not found:**
- Run: `source ~/.zshrc` to load the alias
- Or use the full path: `cd ~/prd-ticket-agent && python3 chat_with_agent.py`












