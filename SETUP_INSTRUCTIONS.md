# Quick Setup Instructions

## Setting Up Your Gemini API Key

Since you're already logged in to Gemini and have Pro, follow these steps:

### Step 1: Get Your API Key

1. **Open Google AI Studio:**
   - Visit: https://aistudio.google.com/app/apikey
   - (The page should already be open in your browser from the setup script)

2. **Get Your API Key:**
   - Click **"Get API Key"** or **"Create API Key"** button
   - If prompted, select "Create API key in new project" or choose an existing project
   - **Copy the generated API key** (it will look like: `AIza...`)

### Step 2: Add It to Your .env File

1. **Open the `.env` file** in this directory:
   ```bash
   nano .env
   # or
   code .env
   # or open it in any text editor
   ```

2. **Replace the placeholder:**
   Find this line:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   
   Replace it with your actual API key:
   ```
   GEMINI_API_KEY=AIzaSyC...your_actual_key_here
   ```

3. **Save the file**

### Step 3: Test It

Run this to test if it works:
```bash
python3 -c "
from prd_ticket_agent.config import load_context_from_env
context = load_context_from_env()
if context.gemini_api_key and context.gemini_api_key != 'your_gemini_api_key_here':
    print('✅ API key is set!')
else:
    print('❌ API key not set. Please check your .env file.')
"
```

### Alternative: Set Environment Variable Directly

If you prefer, you can also set it directly in your terminal:

```bash
export GEMINI_API_KEY="your_actual_api_key_here"
```

Then test:
```bash
python3 -c "import os; print('✅ Set!' if os.getenv('GEMINI_API_KEY') else '❌ Not set')"
```

## You're Done! 🎉

Once your API key is set, you can start using the agent:

```bash
python cli.py prd --description "Add user authentication feature"
```

The agent will automatically use your Gemini API key to generate PRDs and tickets!



