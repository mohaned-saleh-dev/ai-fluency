#!/usr/bin/env python3
"""
Helper script to set up Gemini API key.
Opens Google AI Studio in your browser and helps you configure the API key.
"""

import os
import webbrowser
import sys
from pathlib import Path

def get_gemini_api_key():
    """Get Gemini API key from user."""
    print("\n" + "="*60)
    print("Gemini API Key Setup")
    print("="*60)
    print("\n1. Opening Google AI Studio in your browser...")
    print("   (If it doesn't open, visit: https://aistudio.google.com/app/apikey)")
    
    # Open Google AI Studio
    webbrowser.open("https://aistudio.google.com/app/apikey")
    
    print("\n2. In Google AI Studio:")
    print("   - Click 'Create API Key' or 'Get API Key'")
    print("   - Select 'Create API key in new project' or choose existing project")
    print("   - Copy the generated API key")
    
    print("\n3. Paste your API key below:")
    api_key = input("\nGemini API Key: ").strip()
    
    if not api_key:
        print("\n❌ No API key provided. Exiting.")
        return None
    
    if len(api_key) < 20:
        print("\n⚠️  Warning: API key seems too short. Please verify it's correct.")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return None
    
    return api_key

def update_env_file(api_key: str):
    """Update or create .env file with Gemini API key."""
    env_path = Path(".env")
    
    # Read existing .env if it exists
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Update or add Gemini API key
    env_vars['GEMINI_API_KEY'] = api_key
    
    # Set default model if not specified
    if 'GEMINI_MODEL_NAME' not in env_vars:
        env_vars['GEMINI_MODEL_NAME'] = 'gemini-pro'
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        f.write("# Environment variables for PRD Ticket Agent\n")
        f.write("# Generated/updated by setup_gemini.py\n\n")
        
        # Write Notion config
        f.write("# Notion API Configuration\n")
        f.write(f"NOTION_API_KEY={env_vars.get('NOTION_API_KEY', 'your_notion_api_key_here')}\n")
        f.write(f"NOTION_PRD_DATABASE_ID={env_vars.get('NOTION_PRD_DATABASE_ID', 'your_prd_database_id')}\n")
        f.write(f"NOTION_TICKETS_DATABASE_ID={env_vars.get('NOTION_TICKETS_DATABASE_ID', 'your_tickets_database_id')}\n")
        f.write(f"NOTION_ALL_PRDS_PAGE_ID={env_vars.get('NOTION_ALL_PRDS_PAGE_ID', 'your_all_prds_page_id')}\n")
        f.write(f"NOTION_ALL_TICKETS_PAGE_ID={env_vars.get('NOTION_ALL_TICKETS_PAGE_ID', 'your_all_tickets_page_id')}\n")
        f.write(f"NOTION_SQUAD_PRIORITIES_PAGE_ID={env_vars.get('NOTION_SQUAD_PRIORITIES_PAGE_ID', 'your_squad_priorities_page_id')}\n\n")
        
        # Write Jira config
        f.write("# Jira API Configuration\n")
        f.write(f"JIRA_URL={env_vars.get('JIRA_URL', 'https://your-company.atlassian.net')}\n")
        f.write(f"JIRA_EMAIL={env_vars.get('JIRA_EMAIL', 'your_email@company.com')}\n")
        f.write(f"JIRA_API_TOKEN={env_vars.get('JIRA_API_TOKEN', 'your_jira_api_token')}\n\n")
        
        # Write Gemini config
        f.write("# Gemini API Configuration\n")
        f.write(f"GEMINI_API_KEY={api_key}\n")
        f.write(f"GEMINI_MODEL_NAME={env_vars.get('GEMINI_MODEL_NAME', 'gemini-pro')}\n\n")
        
        # Write optional config
        f.write("# Optional\n")
        f.write(f"AI_CHATBOT_CSV_PATH={env_vars.get('AI_CHATBOT_CSV_PATH', 'path/to/ai_chatbot_requirements.csv')}\n")
    
    print(f"\n✅ API key saved to {env_path}")
    return True

def test_api_key(api_key: str):
    """Test if the API key works."""
    print("\n🧪 Testing API key...")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Simple test
        response = model.generate_content("Say 'Hello' in one word.")
        
        if response and response.text:
            print("✅ API key is valid and working!")
            print(f"   Test response: {response.text.strip()}")
            return True
        else:
            print("❌ API key test failed: Empty response")
            return False
            
    except ImportError:
        print("⚠️  google-generativeai package not installed.")
        print("   Install it with: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ API key test failed: {e}")
        print("   Please check that your API key is correct.")
        return False

def main():
    """Main setup function."""
    print("\n🚀 Gemini API Key Setup for PRD Ticket Agent\n")
    
    # Check if .env already has a key
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
            if 'GEMINI_API_KEY' in content and 'your_gemini_api_key' not in content:
                existing_key = None
                for line in content.split('\n'):
                    if line.startswith('GEMINI_API_KEY=') and 'your_gemini_api_key' not in line:
                        existing_key = line.split('=', 1)[1].strip()
                        break
                
                if existing_key:
                    print(f"⚠️  Found existing API key in .env file")
                    replace = input("Replace it? (y/n): ").strip().lower()
                    if replace != 'y':
                        print("Keeping existing API key.")
                        return
    
    # Get API key from user
    api_key = get_gemini_api_key()
    if not api_key:
        return
    
    # Update .env file
    if update_env_file(api_key):
        print("\n✅ Configuration saved!")
        
        # Test the API key
        test = input("\nTest the API key now? (y/n): ").strip().lower()
        if test == 'y':
            test_api_key(api_key)
        
        print("\n" + "="*60)
        print("Setup Complete!")
        print("="*60)
        print("\nYou can now use the agent:")
        print("  python cli.py prd --description 'Your project description'")
        print("\nThe API key is saved in .env file.")
        print("Make sure .env is in .gitignore (it should be by default).\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled.")
        sys.exit(1)



