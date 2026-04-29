#!/usr/bin/env python3
"""
PRD Ticket Agent - GUI Chat Interface
Simple, reliable chat interface for the PRD Ticket Agent.
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import asyncio
import threading
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from prd_ticket_agent import PRDTicketAgent
    from prd_ticket_agent.config import load_context_from_env, load_context_from_file
except ImportError as e:
    print(f"Import error: {e}")
    PRDTicketAgent = None


class PRDAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PRD Ticket Agent")
        self.root.geometry("800x600")
        
        # Initialize agent
        self.agent = None
        self.context = None
        self._init_agent()
        
        # Create UI - simple and direct
        self._create_ui()
        
        # Show welcome after UI is ready
        self.root.after(100, self._show_welcome)
    
    def _init_agent(self):
        """Initialize the agent."""
        try:
            try:
                self.context = load_context_from_env()
            except:
                config_path = Path(__file__).parent / "config.json"
                if config_path.exists():
                    self.context = load_context_from_file(str(config_path))
                else:
                    self.context = None
            
            if self.context and self.context.gemini_api_key and PRDTicketAgent:
                self.agent = PRDTicketAgent(self.context)
        except Exception as e:
            print(f"Agent init error: {e}")
            self.agent = None
    
    def _create_ui(self):
        """Create the user interface."""
        # Title
        title = tk.Label(
            self.root,
            text="PRD Ticket Agent",
            font=("Arial", 18, "bold"),
            bg="#f0f0f0"
        )
        title.pack(pady=10)
        
        # Chat area
        chat_frame = tk.Frame(self.root, bg="#f0f0f0")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chat_text = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Arial", 11),
            bg="white",
            fg="black",
            state=tk.DISABLED
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        
        # Input area
        input_frame = tk.Frame(self.root, bg="#f0f0f0")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.input_entry = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="white",
            fg="black"
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", self._on_enter)
        self.input_entry.bind("<Shift-Return>", lambda e: None)
        
        send_btn = tk.Button(
            input_frame,
            text="Send",
            command=self._send_message,
            width=12,
            height=2,
            bg="#0066cc",
            fg="white",
            font=("Arial", 11, "bold")
        )
        send_btn.pack(side=tk.RIGHT)
        
        # Status
        status_text = "Ready" if self.agent else "⚠️ Set GEMINI_API_KEY"
        self.status = tk.Label(
            self.root,
            text=status_text,
            bg="#f0f0f0",
            anchor=tk.W,
            padx=10,
            pady=5
        )
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Focus on input
        self.root.after(200, lambda: self.input_entry.focus_set())
    
    def _show_welcome(self):
        """Show welcome message."""
        welcome = """👋 Hello! I'm your PRD Ticket Agent.

I can help you:
• Create Product Requirements Documents (PRDs)
• Generate Jira tickets  
• Answer questions about PRDs and tickets

What would you like to do?"""
        self._add_to_chat("Agent", welcome)
    
    def _add_to_chat(self, sender, message):
        """Add message to chat."""
        self.chat_text.config(state=tk.NORMAL)
        
        if sender == "You":
            self.chat_text.insert(tk.END, "You: ", "user")
            self.chat_text.tag_config("user", foreground="blue", font=("Arial", 11, "bold"))
        else:
            self.chat_text.insert(tk.END, "Agent: ", "agent")
            self.chat_text.tag_config("agent", foreground="black")
        
        self.chat_text.insert(tk.END, message + "\n\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def _on_enter(self, event):
        """Handle Enter key."""
        if not (event.state & 0x1):  # Not Shift
            self._send_message()
            return "break"
    
    def _send_message(self):
        """Send user message."""
        text = self.input_entry.get("1.0", tk.END).strip()
        if not text:
            return
        
        # Clear input
        self.input_entry.delete("1.0", tk.END)
        
        # Show user message
        self._add_to_chat("You", text)
        
        # Update status
        self.status.config(text="Thinking...")
        self.root.update()
        
        # Process in background
        threading.Thread(target=self._process, args=(text,), daemon=True).start()
    
    def _process(self, user_input):
        """Process user input."""
        try:
            if not self.agent:
                response = "⚠️ Agent not initialized. Please set GEMINI_API_KEY environment variable."
                self.root.after(0, lambda: self._add_to_chat("Agent", response))
                self.root.after(0, lambda: self.status.config(text="Ready"))
                return
            
            # Check for PRD creation
            if any(k in user_input.lower() for k in ["create prd", "make prd", "generate prd", "new prd"]):
                response = self._create_prd(user_input)
            elif any(k in user_input.lower() for k in ["create ticket", "make ticket", "generate ticket"]):
                response = self._create_ticket_help()
            else:
                response = self._answer_question(user_input)
            
            self.root.after(0, lambda: self._add_to_chat("Agent", response))
            self.root.after(0, lambda: self.status.config(text="Ready"))
            
        except Exception as e:
            error = f"Error: {str(e)}"
            self.root.after(0, lambda: self._add_to_chat("Agent", error))
            self.root.after(0, lambda: self.status.config(text="Error"))
    
    def _create_prd(self, user_input):
        """Create a PRD."""
        # Extract description
        desc = user_input
        for phrase in ["create prd", "make prd", "generate prd", "new prd", "for"]:
            if phrase in desc.lower():
                parts = desc.lower().split(phrase, 1)
                if len(parts) > 1:
                    desc = parts[-1].strip()
        
        if len(desc) < 10:
            return "I need more details. Please describe the project or feature you want to create a PRD for."
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            prd = loop.run_until_complete(
                self.agent.create_prd(project_description=desc)
            )
            loop.close()
            
            result = "✅ PRD Created!\n\n"
            if prd.get('content'):
                for section, content in prd['content'].items():
                    result += f"📋 {section.upper().replace('_', ' ')}:\n"
                    if isinstance(content, list):
                        for item in content:
                            result += f"  • {item}\n"
                    else:
                        result += f"  {content}\n"
                    result += "\n"
            
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _create_ticket_help(self):
        """Help with ticket creation."""
        return """To create a Jira ticket, I need:
1. A PRD (Notion ID or JSON file)
2. Project key (e.g., 'PROJ')
3. Ticket description

Say 'create prd' first to create a PRD, or provide the PRD details."""
    
    def _answer_question(self, question):
        """Answer general questions."""
        try:
            from prd_ticket_agent.integrations.gemini_client import GeminiClient
            
            if not self.context or not self.context.gemini_api_key:
                return "I need GEMINI_API_KEY to answer questions."
            
            client = GeminiClient(self.context.gemini_api_key, self.context.gemini_model_name)
            
            prompt = f"""You are a PRD and Jira Ticket Writing Agent. Help the user.

User: {question}

Provide a helpful, concise response."""
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(
                client.generate_text(prompt=prompt, temperature=0.7, max_tokens=500)
            )
            loop.close()
            
            return response
        except Exception as e:
            return f"Error: {str(e)}"


def main():
    """Launch the app."""
    try:
        root = tk.Tk()
        app = PRDAgentGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"Failed to start: {e}")
        except:
            pass


if __name__ == "__main__":
    main()
