# Gemini LLM Integration Setup

The PRD and Ticket Writing Agent uses Google's Gemini LLM for generating PRDs and Jira tickets.

## Getting Your Gemini API Key

1. **Visit Google AI Studio:**
   - Go to https://aistudio.google.com/app/apikey
   - Or visit https://makersuite.google.com/app/apikey

2. **Sign in:**
   - Sign in with your Google account

3. **Create API Key:**
   - Click "Create API Key" or "Get API Key"
   - If prompted, create a new Google Cloud project or select an existing one
   - Copy the generated API key

4. **Set Environment Variable:**
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

## Available Models

The agent supports different Gemini models. You can specify which model to use:

- `gemini-pro` (default) - Best for general text generation
- `gemini-pro-vision` - For multimodal tasks (if needed in future)

Set the model name:
```bash
export GEMINI_MODEL_NAME="gemini-pro"
```

## Configuration

### Environment Variables

```bash
export GEMINI_API_KEY="your_gemini_api_key"
export GEMINI_MODEL_NAME="gemini-pro"  # Optional
```

### Config File

Add to your `config.json`:
```json
{
  "gemini_api_key": "your_gemini_api_key",
  "gemini_model_name": "gemini-pro"
}
```

## How It Works

1. **PRD Generation:**
   - The agent builds a comprehensive prompt with context from Notion
   - Sends the prompt to Gemini with structured output requirements
   - Gemini generates all PRD sections following your format
   - The output is parsed and formatted for Notion

2. **Ticket Generation:**
   - The agent uses the PRD context and existing tickets
   - Generates user stories, acceptance criteria, and descriptions
   - Ensures consistency with existing ticket terminology
   - Applies the writing style guide

## Troubleshooting

### Error: "Gemini API key not configured"
- Make sure you've set the `GEMINI_API_KEY` environment variable
- Or added it to your `config.json` file
- The agent will fall back to empty templates if Gemini is not configured

### Error: "Error generating text with Gemini"
- Check that your API key is valid
- Verify you have internet connectivity
- Check Google AI Studio for any API quota or access issues

### Rate Limiting
- Gemini API has rate limits
- If you hit rate limits, wait a few minutes and try again
- Consider implementing retry logic for production use

## Testing the Integration

You can test if Gemini is working by running:

```python
from prd_ticket_agent.integrations.gemini_client import GeminiClient
import asyncio

async def test():
    client = GeminiClient(api_key="your_key")
    response = await client.generate_text("Say hello in one sentence")
    print(response)

asyncio.run(test())
```

## Cost Considerations

- Gemini API has free tier limits
- Check current pricing at https://ai.google.dev/pricing
- Monitor your usage in Google AI Studio dashboard



