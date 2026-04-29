#!/usr/bin/env python3
"""
Simple chat interface for PRD Agent - Terminal based
Just run this script and chat with the agent.
"""

import sys
import asyncio
import warnings
from pathlib import Path

# Suppress Python version warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='.*importlib.metadata.*')
warnings.filterwarnings('ignore', message='.*non-supported Python version.*')
warnings.filterwarnings('ignore', message='.*past its end of life.*')

# Fix for Python 3.9 compatibility with importlib.metadata
if sys.version_info < (3, 10):
    try:
        import importlib.metadata
        if not hasattr(importlib.metadata, 'packages_distributions'):
            # Add a dummy function for Python 3.9
            def packages_distributions():
                return {}
            importlib.metadata.packages_distributions = packages_distributions
    except:
        pass

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent import PRDTicketAgent
from prd_ticket_agent.config import load_context_from_env, load_context_from_file

def print_banner():
    print("\n" + "="*60)
    print("  PRD Ticket Agent - Chat Interface")
    print("="*60)
    print("Type 'quit' or 'exit' to end the conversation\n")

def _get_context_info(context, agent):
    """Get information about what context the agent has access to."""
    info_parts = []
    info_parts.append("📋 What I Have Access To:\n")
    
    # Notion access
    if context.notion_api_key:
        info_parts.append("✅ Notion Workspace")
        info_parts.append("   • I scan your entire Notion workspace automatically")
        info_parts.append("   • Access to: OKRs, Projects, PRDs, and all documents")
        workspace_id = context.notion_workspace_id or "13662429127880a291deebd5d0fdb130"
        info_parts.append(f"   • Workspace: https://notion.so/tamaracom/Agent-{workspace_id}")
        info_parts.append("   • When creating PRDs, I automatically:")
        info_parts.append("     - Find and use OKR documents")
        info_parts.append("     - Find and use project documents")
        info_parts.append("     - Find existing PRDs for format reference")
        info_parts.append("     - Extract knowledge from all workspace documents")
    else:
        info_parts.append("❌ Notion: Not configured (set NOTION_API_KEY)")
    
    info_parts.append("")
    
    # Jira access
    if context.jira_url and context.jira_email and context.jira_api_token:
        info_parts.append("✅ Jira")
        info_parts.append(f"   • Connected to: {context.jira_url}")
        info_parts.append(f"   • As: {context.jira_email}")
        info_parts.append("   • When creating PRDs/tickets, I:")
        info_parts.append("     - Search for related Jira issues")
        info_parts.append("     - Fetch recent issues (last 90 days) for context")
        info_parts.append("     - Extract knowledge base:")
        info_parts.append("       • Technical components in use")
        info_parts.append("       • Common terminology and naming conventions")
        info_parts.append("       • Writing patterns and issue formats")
        info_parts.append("     - Create tickets directly in Jira")
    else:
        info_parts.append("❌ Jira: Not configured")
    
    info_parts.append("")
    
    # Gemini AI
    if context.gemini_api_key:
        info_parts.append("✅ Gemini AI")
        info_parts.append(f"   • Model: {context.gemini_model_name}")
        info_parts.append("   • Used for: Generating PRDs and tickets with all context")
    else:
        info_parts.append("❌ Gemini AI: Not configured (required)")
    
    info_parts.append("")
    info_parts.append("What I Can Do:")
    info_parts.append("• Create PRDs using comprehensive context from:")
    info_parts.append("  - Notion workspace (OKRs, projects, existing PRDs)")
    info_parts.append("  - Jira (related issues, knowledge base, patterns)")
    info_parts.append("• Create Jira tickets with proper terminology and consistency")
    info_parts.append("• Answer questions about PRDs and tickets")
    info_parts.append("• Use all available context to ensure quality and consistency")
    
    return "\n".join(info_parts)


def _build_system_context(context):
    """Build system context information for prompts."""
    context_parts = []
    
    if context.notion_api_key:
        context_parts.append("- **Notion Workspace**: Full access to scan entire workspace")
        context_parts.append("  - Automatically finds OKRs, projects, PRDs")
        context_parts.append("  - Uses all documents for comprehensive context")
    
    if context.jira_url and context.jira_api_token:
        context_parts.append(f"- **Jira**: Connected to {context.jira_url}")
        context_parts.append("  - Can search for related issues")
        context_parts.append("  - Can fetch recent issues for context")
        context_parts.append("  - Can extract knowledge base (components, terminology)")
        context_parts.append("  - Can create tickets directly")
    
    if context.gemini_api_key:
        context_parts.append(f"- **AI Model**: {context.gemini_model_name} for generation")
    
    return "\n".join(context_parts) if context_parts else "No external context configured."


async def chat_loop():
    """Main chat loop."""
    # Load context
    try:
        try:
            context = load_context_from_env()
        except:
            config_path = Path(__file__).parent / "config.json"
            if config_path.exists():
                context = load_context_from_file(str(config_path))
            else:
                print("❌ Error: No configuration found. Set GEMINI_API_KEY or create config.json")
                return
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return
    
    if not context or not context.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found. Please set it as an environment variable.")
        return
    
    # Initialize agent
    try:
        # Suppress warnings during initialization
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            agent = PRDTicketAgent(context)
        print("✅ Agent initialized successfully!\n")
    except Exception as e:
        error_msg = str(e)
        if "importlib.metadata" in error_msg or "packages_distributions" in error_msg:
            print("⚠️ Python 3.9 compatibility warning (this is safe to ignore)")
            print("✅ Agent initialized (warnings suppressed)\n")
            # Try to continue anyway
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    agent = PRDTicketAgent(context)
            except:
                print(f"❌ Error initializing agent: {e}")
                return
        else:
            print(f"❌ Error initializing agent: {e}")
            return
    
    print_banner()
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Process message
            print("\n🤖 Agent: ", end="", flush=True)
            
            # Check if user wants to create PRD
            if any(k in user_input.lower() for k in ["create prd", "make prd", "generate prd", "new prd"]):
                # Extract description
                desc = user_input
                for phrase in ["create prd", "make prd", "generate prd", "new prd", "for"]:
                    if phrase in desc.lower():
                        parts = desc.lower().split(phrase, 1)
                        if len(parts) > 1:
                            desc = parts[-1].strip()
                
                if len(desc) < 10:
                    print("I need more details. Please describe the project or feature.")
                else:
                    try:
                        prd = await agent.create_prd(project_description=desc)
                        print("\n✅ PRD Created Successfully!\n")
                        if prd.get('content'):
                            for section, content in prd['content'].items():
                                print(f"📋 {section.upper().replace('_', ' ')}:")
                                if isinstance(content, list):
                                    for item in content:
                                        print(f"  • {item}")
                                else:
                                    print(f"  {content}")
                                print()
                    except Exception as e:
                        print(f"❌ Error: {e}")
            
            # Check if user wants to create ticket
            elif any(k in user_input.lower() for k in ["create ticket", "make ticket", "generate ticket"]):
                print("To create a Jira ticket, I need:\n1. A PRD (Notion ID or JSON file)\n2. Project key (e.g., 'PROJ')\n3. Ticket description\n\nSay 'create prd' first, or provide PRD details.")
            
            # General question
            else:
                try:
                    # Check for context questions
                    if any(phrase in user_input.lower() for phrase in [
                        "what do you have access to", "what context", "what can you access",
                        "what do you know", "what information", "what data"
                    ]):
                        response = _get_context_info(context, agent)
                        print(response)
                    else:
                        # Suppress warnings for this call
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            from prd_ticket_agent.integrations.gemini_client import GeminiClient
                            client = GeminiClient(context.gemini_api_key, context.gemini_model_name)
                            
                            # Build system context info
                            context_info = _build_system_context(context)
                            
                            prompt = f"""You are a PRD and Jira Ticket Writing Agent with access to:

{context_info}

User question: {user_input}

Provide a helpful, concise response. If they're asking about creating PRDs or tickets, explain how you can help."""
                            
                            response = await client.generate_text(prompt=prompt, temperature=0.7, max_tokens=500)
                            print(response)
                except Exception as e:
                    error_msg = str(e)
                    # Clean up error message - suppress importlib.metadata errors
                    if "importlib.metadata" in error_msg or "packages_distributions" in error_msg:
                        # This is a Python 3.9 compatibility issue, but it shouldn't break functionality
                        # Try direct Gemini API call
                        try:
                            import google.generativeai as genai
                            genai.configure(api_key=context.gemini_api_key)
                            model = genai.GenerativeModel(context.gemini_model_name)
                            response = model.generate_content(prompt)
                            print(response.text if hasattr(response, 'text') else str(response))
                        except Exception as e2:
                            print(f"Error: {e2}")
                    else:
                        print(f"Error: {error_msg}")
            
            print()  # Empty line for spacing
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(chat_loop())

