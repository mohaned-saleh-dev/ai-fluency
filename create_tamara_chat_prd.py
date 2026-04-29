#!/usr/bin/env python3
"""
Create comprehensive PRD for Tamara Chat System.
This PRD covers the Flutter Chat SDK, Web Chat Widget, and Salesforce integration.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent.integrations.notion_client import NotionClient
from prd_ticket_agent.config import load_context_from_env


def create_rich_text(text: str, bold: bool = False, italic: bool = False, code: bool = False, link: str = None) -> dict:
    """Create a rich text object."""
    annotations = {}
    if bold:
        annotations["bold"] = True
    if italic:
        annotations["italic"] = True
    if code:
        annotations["code"] = True
    
    result = {
        "type": "text",
        "text": {"content": text}
    }
    
    if annotations:
        result["annotations"] = annotations
    
    if link:
        result["text"]["link"] = {"url": link}
    
    return result


def create_heading_1(text: str) -> dict:
    """Create a heading 1 block."""
    return {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [create_rich_text(text)],
            "is_toggleable": True
        }
    }


def create_heading_2(text: str, toggleable: bool = True) -> dict:
    """Create a heading 2 block."""
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [create_rich_text(text)],
            "is_toggleable": toggleable
        }
    }


def create_heading_3(text: str, toggleable: bool = False) -> dict:
    """Create a heading 3 block."""
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [create_rich_text(text)],
            "is_toggleable": toggleable
        }
    }


def create_paragraph(rich_text_items: list) -> dict:
    """Create a paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": rich_text_items
        }
    }


def create_simple_paragraph(text: str) -> dict:
    """Create a simple paragraph with plain text."""
    return create_paragraph([create_rich_text(text)])


def create_bullet(text: str, bold_prefix: str = None) -> dict:
    """Create a bulleted list item."""
    if bold_prefix:
        rich_text = [
            create_rich_text(f"{bold_prefix}: ", bold=True),
            create_rich_text(text)
        ]
    else:
        rich_text = [create_rich_text(text)]
    
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": rich_text
        }
    }


def create_numbered(text: str) -> dict:
    """Create a numbered list item."""
    return {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {
            "rich_text": [create_rich_text(text)]
        }
    }


def create_callout(text: str, emoji: str = "💡") -> dict:
    """Create a callout block."""
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [create_rich_text(text)],
            "icon": {"type": "emoji", "emoji": emoji}
        }
    }


def create_divider() -> dict:
    """Create a divider block."""
    return {
        "object": "block",
        "type": "divider",
        "divider": {}
    }


def create_code_block(code: str, language: str = "mermaid") -> dict:
    """Create a code block."""
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [create_rich_text(code)],
            "language": language
        }
    }


def create_table_of_contents() -> dict:
    """Create a table of contents block."""
    return {
        "object": "block",
        "type": "table_of_contents",
        "table_of_contents": {
            "color": "default"
        }
    }


def create_toggle(title: str, children: list = None) -> dict:
    """Create a toggle block."""
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [create_rich_text(title, bold=True)],
            "children": children or []
        }
    }


def create_notion_blocks():
    """Create all Notion blocks for the Tamara Chat System PRD."""
    blocks = []
    
    # ========== DOCUMENT HEADER ==========
    blocks.append(create_callout(
        "This PRD defines the comprehensive requirements for building a native chat system for Tamara, "
        "including Flutter Chat SDK for mobile apps, Web Chat Widget for all web platforms, and full "
        "Salesforce integration for case management. Target launch: April 1st, 2026.",
        "📋"
    ))
    
    blocks.append(create_divider())
    
    # Metadata section
    blocks.append(create_paragraph([
        create_rich_text("Version: ", bold=True),
        create_rich_text("1.0 | "),
        create_rich_text("Status: ", bold=True),
        create_rich_text("Draft | "),
        create_rich_text("Created: ", bold=True),
        create_rich_text("February 3, 2026 | "),
        create_rich_text("Target Launch: ", bold=True),
        create_rich_text("April 1, 2026")
    ]))
    
    blocks.append(create_divider())
    
    # Table of Contents
    blocks.append(create_heading_2("📑 Table of Contents", toggleable=False))
    blocks.append(create_table_of_contents())
    
    blocks.append(create_divider())
    
    # ========== 1. EXECUTIVE SUMMARY ==========
    blocks.append(create_heading_1("1. 📌 Executive Summary"))
    
    blocks.append(create_simple_paragraph(
        "Tamara currently uses the Salesforce Chat SDK embedded in a WebView within its mobile applications. "
        "This approach creates a suboptimal user experience with slow load times, limited native functionality, "
        "and inconsistent behavior across platforms. Additionally, the web chat widget used across various "
        "Tamara web properties lacks integration with our AI chatbot orchestrator and has limited customization options."
    ))
    
    blocks.append(create_simple_paragraph(
        "This PRD outlines the requirements for building a comprehensive, native chat solution that includes:"
    ))
    
    blocks.append(create_bullet("A Flutter Chat SDK for iOS and Android (Customer and Partner apps)"))
    blocks.append(create_bullet("A Web Chat Widget for all Tamara web platforms"))
    blocks.append(create_bullet("Full integration with Salesforce Service Cloud for case management"))
    blocks.append(create_bullet("Seamless integration with Tamara's AI Chatbot Orchestrator"))
    blocks.append(create_bullet("Support for authenticated and non-authenticated user experiences"))
    blocks.append(create_bullet("Rich messaging capabilities including carousels, buttons, and file attachments"))
    
    blocks.append(create_divider())
    
    # ========== 2. PROBLEM STATEMENT ==========
    blocks.append(create_heading_1("2. ❗ Problem Statement"))
    
    blocks.append(create_heading_3("Current State Issues"))
    
    blocks.append(create_bullet("WebView-based implementation causes slow load times and laggy interactions", "Performance"))
    blocks.append(create_bullet("Limited access to native device features (camera, file system, push notifications)", "Native Features"))
    blocks.append(create_bullet("Inconsistent UI/UX across iOS and Android platforms", "Consistency"))
    blocks.append(create_bullet("No integration with Tamara's internal AI chatbot - relies on Salesforce Einstein", "AI Integration"))
    blocks.append(create_bullet("Limited customization and branding options", "Branding"))
    blocks.append(create_bullet("Difficult to implement advanced message types (carousels, quick replies)", "Rich Messaging"))
    blocks.append(create_bullet("Maintenance overhead with Salesforce SDK version updates", "Maintenance"))
    
    blocks.append(create_heading_3("Business Impact"))
    
    blocks.append(create_bullet("Current BSAT (Bot Satisfaction) score: 88% - target is 92%"))
    blocks.append(create_bullet("High customer effort scores due to poor chat experience"))
    blocks.append(create_bullet("Increased support costs from chat abandonment and repeat contacts"))
    blocks.append(create_bullet("Limited data insights due to Salesforce SDK constraints"))
    blocks.append(create_bullet("18,000-30,000 daily chats impacted by suboptimal experience"))
    
    blocks.append(create_divider())
    
    # ========== 3. GOALS & OBJECTIVES ==========
    blocks.append(create_heading_1("3. 🎯 Goals & Objectives"))
    
    blocks.append(create_heading_3("Primary Goals"))
    
    blocks.append(create_numbered("Replace Salesforce Chat SDK/Widget with native solutions across all platforms"))
    blocks.append(create_numbered("Improve BSAT from 88% to 92% through enhanced chat experience"))
    blocks.append(create_numbered("Enable seamless integration with Tamara's AI Chatbot Orchestrator"))
    blocks.append(create_numbered("Maintain full Salesforce case management integration"))
    blocks.append(create_numbered("Support multi-threaded, persistent chat conversations"))
    
    blocks.append(create_heading_3("Secondary Goals"))
    
    blocks.append(create_bullet("Reduce chat widget load time by 60%"))
    blocks.append(create_bullet("Enable rich messaging features (carousels, buttons, quick replies)"))
    blocks.append(create_bullet("Improve file attachment experience with native integrations"))
    blocks.append(create_bullet("Support RTL languages (Arabic) with full formatting support"))
    blocks.append(create_bullet("Enable comprehensive data traceability for analytics"))
    
    blocks.append(create_divider())
    
    # ========== 4. SUCCESS METRICS ==========
    blocks.append(create_heading_1("4. 📊 Success Metrics"))
    
    blocks.append(create_heading_2("4.1 Primary Business Metrics"))
    
    blocks.append(create_bullet("Successful phase-out of Salesforce Chat SDKs/Widgets across all platforms", "Salesforce Replacement"))
    blocks.append(create_bullet("Increase from 88% to 92% (4 percentage point improvement)", "BSAT Improvement"))
    blocks.append(create_bullet("100% of agent-handled cases successfully created in Salesforce", "Case Creation Rate"))
    
    blocks.append(create_heading_2("4.2 Product Success Metrics"))
    
    # Create a simple table using paragraphs
    blocks.append(create_paragraph([
        create_rich_text("Metric", bold=True),
        create_rich_text(" | "),
        create_rich_text("Target", bold=True),
        create_rich_text(" | "),
        create_rich_text("Measurement Method", bold=True)
    ]))
    
    metrics = [
        ("System Uptime", "99.9%", "Infrastructure monitoring (DataDog/CloudWatch)"),
        ("Error Rate", "< 0.1%", "Error tracking (Sentry/DataDog)"),
        ("Message Delivery Latency (P95)", "< 500ms", "APM metrics"),
        ("Chat Widget Load Time", "< 2 seconds", "RUM metrics"),
        ("File Upload Success Rate", "> 99%", "Backend metrics"),
        ("WebSocket Connection Stability", "> 99.5%", "Connection monitoring"),
        ("Message Send Success Rate", "> 99.9%", "Backend metrics"),
        ("Salesforce Sync Success Rate", "> 99.5%", "Integration monitoring"),
    ]
    
    for metric, target, method in metrics:
        blocks.append(create_bullet(f"{metric}: {target} - {method}"))
    
    blocks.append(create_heading_2("4.3 User Experience Metrics"))
    
    blocks.append(create_bullet("Chat session completion rate > 85%", "Completion Rate"))
    blocks.append(create_bullet("Average chat response time < 1 second for bot responses", "Response Time"))
    blocks.append(create_bullet("User satisfaction rating improvement from 3.5 to 4.2+ stars", "Satisfaction"))
    blocks.append(create_bullet("Chat abandonment rate < 10%", "Abandonment"))
    
    blocks.append(create_divider())
    
    # ========== 5. SOLUTION OVERVIEW ==========
    blocks.append(create_heading_1("5. 💡 Solution Overview"))
    
    blocks.append(create_simple_paragraph(
        "The solution consists of three main components that work together to provide a unified, "
        "native chat experience across all Tamara platforms."
    ))
    
    blocks.append(create_heading_2("5.1 Solution Components"))
    
    blocks.append(create_heading_3("5.1.1 Flutter Chat SDK"))
    blocks.append(create_bullet("Native Flutter package for iOS and Android"))
    blocks.append(create_bullet("Integrated with Tamara Customer App and Partner App"))
    blocks.append(create_bullet("Full access to device features (camera, gallery, file system)"))
    blocks.append(create_bullet("Push notification support for new messages"))
    blocks.append(create_bullet("Offline message queuing and sync"))
    
    blocks.append(create_heading_3("5.1.2 Web Chat Widget"))
    blocks.append(create_bullet("React-based embeddable widget"))
    blocks.append(create_bullet("Compatible with all Tamara web platforms:"))
    blocks.append(create_bullet("  - Tamara Customer Web App"))
    blocks.append(create_bullet("  - Tamara Partner Portal"))
    blocks.append(create_bullet("  - Tamara Partner Onboarding Portal"))
    blocks.append(create_bullet("  - Support Website (support.tamara.co - Contentful CMS)"))
    blocks.append(create_bullet("Lightweight and fast-loading"))
    blocks.append(create_bullet("Responsive design for all screen sizes"))
    
    blocks.append(create_heading_3("5.1.3 Chat Backend Service"))
    blocks.append(create_bullet("New microservice to handle chat operations"))
    blocks.append(create_bullet("Real-time messaging infrastructure"))
    blocks.append(create_bullet("Integration layer with AI Chatbot Orchestrator"))
    blocks.append(create_bullet("Salesforce API integration for case management"))
    blocks.append(create_bullet("File storage and management"))
    
    blocks.append(create_heading_2("5.2 High-Level Architecture"))
    
    # Architecture diagram
    blocks.append(create_code_block("""flowchart TB
    subgraph "Client Layer"
        A[Flutter SDK<br/>iOS/Android] --> G[Chat Backend Service]
        B[Web Widget<br/>React] --> G
    end
    
    subgraph "Backend Services"
        G[Chat Backend Service] --> H[AI Chatbot<br/>Orchestrator]
        G --> I[Message Queue<br/>Redis/Kafka]
        G --> J[File Storage<br/>S3]
        G --> K[WebSocket Server]
    end
    
    subgraph "External Integrations"
        G --> L[Salesforce<br/>Service Cloud]
        G --> M[Tamara Core API]
        G --> N[Push Notification<br/>Service]
    end
    
    subgraph "Data Layer"
        G --> O[(PostgreSQL<br/>Chat History)]
        G --> P[(Redis<br/>Session Cache)]
    end
    
    L --> Q[Omni-Channel]
    L --> R[Case Management]
    L --> S[Messaging Sessions]""", "mermaid"))
    
    blocks.append(create_divider())
    
    # ========== 6. DETAILED REQUIREMENTS ==========
    blocks.append(create_heading_1("6. 📋 Detailed Requirements"))
    
    # 6.1 Flutter Chat SDK
    blocks.append(create_heading_2("6.1 Flutter Chat SDK Requirements"))
    
    blocks.append(create_heading_3("6.1.1 Core Chat Functionality"))
    
    core_features = [
        "Real-time bidirectional messaging using WebSocket connections",
        "Message status indicators (sent, delivered, read)",
        "Typing indicators",
        "Message timestamps with timezone support",
        "Message persistence and history (5-year retention)",
        "Offline message queuing with automatic retry",
        "Multi-threaded conversation support",
        "Thread management (create, archive, search)",
        "Unread message counts and badges",
    ]
    for feature in core_features:
        blocks.append(create_bullet(feature))
    
    blocks.append(create_heading_3("6.1.2 Rich Message Types"))
    
    message_types = [
        ("Text Messages", "Plain text with emoji support, RTL formatting, links"),
        ("Image Messages", "JPEG, PNG, GIF, WebP support with preview"),
        ("Document Messages", "PDF with file size display and download"),
        ("Carousel Messages", "Horizontal scrollable cards with images, titles, descriptions, and actions"),
        ("Quick Reply Buttons", "Tappable action buttons for common responses"),
        ("List Messages", "Vertical list of selectable options"),
        ("System Messages", "Status updates, ticket events, agent handoffs"),
    ]
    for msg_type, desc in message_types:
        blocks.append(create_bullet(desc, msg_type))
    
    blocks.append(create_heading_3("6.1.3 File Handling"))
    
    blocks.append(create_bullet("Maximum file size: 5MB per file"))
    blocks.append(create_bullet("Supported formats: JPEG, PNG, GIF, WebP, PDF"))
    blocks.append(create_bullet("Native camera and gallery integration"))
    blocks.append(create_bullet("Document picker integration"))
    blocks.append(create_bullet("Image compression before upload"))
    blocks.append(create_bullet("Upload progress indicator"))
    blocks.append(create_bullet("Retry mechanism for failed uploads"))
    blocks.append(create_bullet("Storage: Tamara S3 with Salesforce sync"))
    
    blocks.append(create_heading_3("6.1.4 Authentication"))
    
    blocks.append(create_bullet("Seamless integration with Tamara authentication"))
    blocks.append(create_bullet("Support for authenticated users (customer_id available)"))
    blocks.append(create_bullet("Support for non-authenticated/guest users"))
    blocks.append(create_bullet("Session management and token refresh"))
    blocks.append(create_bullet("Secure token storage using platform keychain"))
    
    blocks.append(create_heading_3("6.1.5 Localization"))
    
    blocks.append(create_bullet("Full Arabic and English support"))
    blocks.append(create_bullet("RTL layout support for Arabic"))
    blocks.append(create_bullet("RTL text formatting including:"))
    blocks.append(create_bullet("  - Bullet points and numbered lists"))
    blocks.append(create_bullet("  - Text alignment"))
    blocks.append(create_bullet("  - Date and time formatting"))
    blocks.append(create_bullet("Dynamic language switching based on app locale"))
    
    # 6.2 Web Chat Widget
    blocks.append(create_heading_2("6.2 Web Chat Widget Requirements"))
    
    blocks.append(create_heading_3("6.2.1 Platform Compatibility"))
    
    blocks.append(create_bullet("React-based component (compatible with all Tamara web platforms)"))
    blocks.append(create_bullet("Contentful CMS integration for support.tamara.co"))
    blocks.append(create_bullet("Embeddable via script tag or npm package"))
    blocks.append(create_bullet("Responsive design (mobile-first)"))
    blocks.append(create_bullet("Cross-browser support (Chrome, Safari, Firefox, Edge)"))
    
    blocks.append(create_heading_3("6.2.2 Widget Features"))
    
    blocks.append(create_bullet("Floating chat button with unread count badge"))
    blocks.append(create_bullet("Expandable/collapsible chat window"))
    blocks.append(create_bullet("Minimized state persistence"))
    blocks.append(create_bullet("Pre-chat form for non-authenticated users"))
    blocks.append(create_bullet("All message types supported (same as Flutter SDK)"))
    blocks.append(create_bullet("File upload via drag-and-drop or file picker"))
    blocks.append(create_bullet("Keyboard shortcuts for power users"))
    
    blocks.append(create_heading_3("6.2.3 Theming & Branding"))
    
    blocks.append(create_bullet("Tamara brand colors and typography"))
    blocks.append(create_bullet("Configurable primary/secondary colors"))
    blocks.append(create_bullet("Custom logo support"))
    blocks.append(create_bullet("Light and dark mode support"))
    blocks.append(create_bullet("CSS variables for easy customization"))
    
    # 6.3 Chat Backend Service
    blocks.append(create_heading_2("6.3 Chat Backend Service Requirements"))
    
    blocks.append(create_heading_3("6.3.1 Real-Time Communication"))
    
    blocks.append(create_callout(
        "Recommended Protocol: Socket.IO over WebSocket\n\n"
        "Justification:\n"
        "• Built-in fallback to HTTP long-polling for restricted networks\n"
        "• Automatic reconnection with exponential backoff\n"
        "• Room-based messaging for thread management\n"
        "• Acknowledgments for message delivery confirmation\n"
        "• Binary data support for file transfers\n"
        "• Extensive ecosystem and battle-tested in production\n\n"
        "Alternatives Considered:\n"
        "• Raw WebSocket: Lower-level, requires custom reconnection logic\n"
        "• Server-Sent Events (SSE): Unidirectional, not suitable for chat\n"
        "• gRPC: Overkill for this use case, limited browser support",
        "⚡"
    ))
    
    blocks.append(create_heading_3("6.3.2 Message Processing"))
    
    blocks.append(create_bullet("Message validation and sanitization"))
    blocks.append(create_bullet("PII detection and masking"))
    blocks.append(create_bullet("Rate limiting per user/session"))
    blocks.append(create_bullet("Message queuing for reliability"))
    blocks.append(create_bullet("Idempotency keys to prevent duplicates"))
    
    blocks.append(create_heading_3("6.3.3 Integration with AI Chatbot Orchestrator"))
    
    blocks.append(create_bullet("Route all messages to existing AI Chatbot Orchestrator"))
    blocks.append(create_bullet("Receive routing decisions and response content from orchestrator"))
    blocks.append(create_bullet("Handle hand-off scenarios as defined by the chatbot"))
    blocks.append(create_bullet("Pass context data (customer_id, order_id, etc.) to orchestrator"))
    blocks.append(create_bullet("Receive routing fields for Salesforce queue assignment"))
    
    blocks.append(create_divider())
    
    # ========== 7. SALESFORCE INTEGRATION ==========
    blocks.append(create_heading_1("7. 🔗 Salesforce Integration"))
    
    blocks.append(create_callout(
        "All agent-handled cases must be pushed to Salesforce as Messaging Sessions with automatically "
        "created Cases. This ensures continuity with existing Care operations and reporting.",
        "⚠️"
    ))
    
    blocks.append(create_heading_2("7.1 Integration Architecture"))
    
    blocks.append(create_code_block("""sequenceDiagram
    participant User
    participant ChatSDK as Chat SDK/Widget
    participant Backend as Chat Backend
    participant Bot as AI Chatbot Orchestrator
    participant SF as Salesforce

    User->>ChatSDK: Start Chat
    ChatSDK->>Backend: Initialize Session
    Backend->>Bot: Route Message
    Bot-->>Backend: Bot Response
    Backend-->>ChatSDK: Display Response
    
    Note over Bot: Escalation Triggered
    
    Bot->>Backend: Hand-off to Agent
    Backend->>SF: Create Messaging Session
    SF-->>Backend: Session ID
    Backend->>SF: Create Case (linked to Session)
    SF-->>Backend: Case ID
    Backend->>SF: Lookup/Create Account
    SF-->>Backend: Account ID
    Backend->>SF: Link Case to Account
    
    Note over SF: Agent picks up case
    
    SF->>Backend: Agent Message
    Backend->>ChatSDK: Display Agent Message
    User->>ChatSDK: User Reply
    ChatSDK->>Backend: Send Message
    Backend->>SF: Update Messaging Session""", "mermaid"))
    
    blocks.append(create_heading_2("7.2 Customer Care - Authenticated Chat"))
    
    blocks.append(create_simple_paragraph(
        "When an authenticated chat session gets handed off by the chatbot to an agent:"
    ))
    
    blocks.append(create_numbered("Chat Backend creates a Messaging Session in Salesforce"))
    blocks.append(create_numbered("Salesforce looks up customer account using customer_id"))
    blocks.append(create_numbered("If account exists, link session to existing account"))
    blocks.append(create_numbered("If account doesn't exist, fetch from Tamara Core and create Person Account"))
    blocks.append(create_numbered("Create Case linked to Messaging Session and Account"))
    blocks.append(create_numbered("Assign to appropriate queue based on routing fields from chatbot"))
    
    blocks.append(create_heading_3("Case Fields Mapping"))
    
    case_fields = [
        ("Order ID", "Pushed by chat system", "Yes"),
        ("Merchant Name", "Pushed by chat system", "Yes"),
        ("Merchant ID", "Pushed by chat system", "Yes"),
        ("Order Status", "Pushed by chat system", "Yes"),
        ("Order Amount", "Pushed by chat system", "Yes"),
        ("Authenticated Contact", "Yes/No", "No"),
        ("Channel", "Chat (Customer iOS App), Chat (Customer Android App), Chat (Customer Web App)", "No"),
        ("Case Language", "AR, EN", "No"),
        ("Interaction Type", "Complaint, Request, Inquiry, Feedback", "Yes"),
        ("Case Subject", "Generated from chat context", "No"),
    ]
    
    blocks.append(create_paragraph([
        create_rich_text("Field", bold=True),
        create_rich_text(" | "),
        create_rich_text("Source", bold=True),
        create_rich_text(" | "),
        create_rich_text("Can be Blank?", bold=True)
    ]))
    
    for field, source, blank in case_fields:
        blocks.append(create_bullet(f"{field}: {source} (Blank: {blank})"))
    
    blocks.append(create_heading_2("7.3 Customer Care - Non-Authenticated Chat"))
    
    blocks.append(create_simple_paragraph(
        "For non-authenticated chat sessions (e.g., from support website):"
    ))
    
    blocks.append(create_bullet("Messaging Session created without customer_id"))
    blocks.append(create_bullet("No Account or Contact is created"))
    blocks.append(create_bullet("Case created and linked to Messaging Session only"))
    blocks.append(create_bullet("Agent can manually identify and link customer later"))
    
    blocks.append(create_heading_2("7.4 Partner Care - Authenticated Chat"))
    
    blocks.append(create_simple_paragraph(
        "Similar flow for partner users from Partner Portal or Partner Mobile App:"
    ))
    
    blocks.append(create_numbered("Lookup SF Contact using merchant user credentials"))
    blocks.append(create_numbered("If Contact doesn't exist, fetch from Tamara Core and create"))
    blocks.append(create_numbered("Create Case linked to Contact and parent Account (Merchant)"))
    blocks.append(create_numbered("Route to Partner Care queue"))
    
    blocks.append(create_heading_2("7.5 File Attachments Sync"))
    
    blocks.append(create_bullet("Files uploaded during chat are stored in Tamara S3"))
    blocks.append(create_bullet("On case creation/update, files are synced to Salesforce Files"))
    blocks.append(create_bullet("ContentVersion records created and linked to Case"))
    blocks.append(create_bullet("Bi-directional sync: agent attachments also sent to chat"))
    
    blocks.append(create_heading_2("7.6 API Endpoints"))
    
    blocks.append(create_heading_3("Create Messaging Session"))
    blocks.append(create_code_block("""POST /services/data/v65.0/sobjects/MessagingSession

{
  "MessagingChannelId": "{{CHANNEL_ID}}",
  "MessagingUserId": "{{USER_ID}}",
  "Status": "Active",
  "StartTime": "2026-02-03T10:00:00Z"
}""", "json"))
    
    blocks.append(create_heading_3("Create Case"))
    blocks.append(create_code_block("""POST /services/data/v65.0/sobjects/Case

{
  "AccountId": "{{ACCOUNT_ID}}",
  "Origin": "Chat",
  "Subject": "Chat - Authenticated - EN - SA - John Doe - 2026-02-03T10:00:00Z",
  "Description": "Chat conversation from Tamara App",
  "Order_ID__c": "{{ORDER_ID}}",
  "Channel__c": "Chat (Customer iOS App)",
  "Case_Language__c": "EN",
  "Authenticated_Contact__c": "Yes"
}""", "json"))
    
    blocks.append(create_heading_3("Fetch Customer Details (Tamara Core)"))
    blocks.append(create_code_block("""POST {{API_URL}}/customer-care/salesforce/customer

{
  "search_type": "customer_id",
  "search_value": "{{CUSTOMER_ID}}"
}

Response:
{
  "customer_id": "C-12345",
  "first_name": "John",
  "last_name": "Doe",
  "verified_email_address": "john@example.com",
  "phone_number": "+966500000000",
  "country_code": "SA",
  "locale": "en_US",
  "segment": "High Value",
  "membership_tier": "Smart Plus",
  "is_blacklisted": false,
  "is_vulnerable": false
}""", "json"))
    
    blocks.append(create_divider())
    
    # ========== 8. AUTHENTICATION ==========
    blocks.append(create_heading_1("8. 🔐 Authentication & Security"))
    
    blocks.append(create_heading_2("8.1 Authentication Flow"))
    
    blocks.append(create_code_block("""sequenceDiagram
    participant User
    participant App as Mobile App/Web
    participant ChatSDK as Chat SDK
    participant Backend as Chat Backend
    participant Auth as Tamara Auth Service

    User->>App: Login to Tamara
    App->>Auth: Authenticate
    Auth-->>App: Access Token + Refresh Token
    
    User->>App: Open Chat
    App->>ChatSDK: Initialize with Auth Token
    ChatSDK->>Backend: Connect (with token)
    Backend->>Auth: Validate Token
    Auth-->>Backend: Token Valid + User Claims
    Backend-->>ChatSDK: Connection Established
    
    Note over Backend: Extract customer_id from claims
    
    Backend->>Backend: Fetch user context
    ChatSDK-->>User: Chat Ready""", "mermaid"))
    
    blocks.append(create_heading_2("8.2 Authentication Methods"))
    
    blocks.append(create_heading_3("Authenticated Users"))
    blocks.append(create_bullet("JWT token passed from parent application"))
    blocks.append(create_bullet("Token validated against Tamara Auth Service"))
    blocks.append(create_bullet("customer_id extracted from token claims"))
    blocks.append(create_bullet("Session linked to authenticated user"))
    blocks.append(create_bullet("Token refresh handled automatically"))
    
    blocks.append(create_heading_3("Non-Authenticated Users (Guest Mode)"))
    blocks.append(create_bullet("Anonymous session created with unique session_id"))
    blocks.append(create_bullet("Optional pre-chat form to collect basic info"))
    blocks.append(create_bullet("Session data stored temporarily (24-hour TTL)"))
    blocks.append(create_bullet("Can be upgraded to authenticated session if user logs in"))
    
    blocks.append(create_heading_2("8.3 Security Requirements"))
    
    blocks.append(create_bullet("All communication over TLS 1.3"))
    blocks.append(create_bullet("WebSocket connections authenticated"))
    blocks.append(create_bullet("Rate limiting: 60 messages per minute per user"))
    blocks.append(create_bullet("PII masking for sensitive data in logs"))
    blocks.append(create_bullet("Data residency: All data hosted in GCC region"))
    blocks.append(create_bullet("Encryption at rest for stored messages"))
    blocks.append(create_bullet("Webhook signature validation for Salesforce callbacks"))
    
    blocks.append(create_callout(
        "Security Review Required: This section requires approval from the Cyber Security team "
        "before implementation begins.",
        "🔒"
    ))
    
    blocks.append(create_divider())
    
    # ========== 9. DATA & ANALYTICS ==========
    blocks.append(create_heading_1("9. 📈 Data & Analytics"))
    
    blocks.append(create_heading_2("9.1 Data Traceability Requirements"))
    
    blocks.append(create_callout(
        "⚠️ PLACEHOLDER: The following data requirements need to be reviewed and approved by the Data Team.",
        "📊"
    ))
    
    blocks.append(create_heading_3("Events to Track"))
    
    events = [
        ("chat_session_started", "When a user initiates a chat session", "session_id, user_id, platform, timestamp"),
        ("message_sent", "When a user sends a message", "message_id, session_id, message_type, timestamp"),
        ("message_received", "When a message is received from bot/agent", "message_id, session_id, sender_type, timestamp"),
        ("bot_handoff", "When conversation is handed to an agent", "session_id, handoff_reason, queue, timestamp"),
        ("file_uploaded", "When a user uploads a file", "file_id, session_id, file_type, file_size, timestamp"),
        ("chat_session_ended", "When a chat session ends", "session_id, duration, resolution_status, timestamp"),
        ("csat_submitted", "When user submits satisfaction rating", "session_id, rating, feedback, timestamp"),
    ]
    
    for event, desc, fields in events:
        blocks.append(create_bullet(f"{event}: {desc}"))
        blocks.append(create_bullet(f"  Fields: {fields}"))
    
    blocks.append(create_heading_3("Data Storage"))
    
    blocks.append(create_bullet("Chat history: PostgreSQL with 5-year retention"))
    blocks.append(create_bullet("Session metadata: Redis with 24-hour TTL"))
    blocks.append(create_bullet("Analytics events: BigQuery via event pipeline"))
    blocks.append(create_bullet("Files: S3 with Salesforce sync"))
    
    blocks.append(create_heading_3("Data Pipeline"))
    
    blocks.append(create_code_block("""flowchart LR
    A[Chat Backend] --> B[Event Publisher]
    B --> C[Pub/Sub]
    C --> D[Event Processor]
    D --> E[BigQuery]
    D --> F[DataDog Metrics]
    E --> G[Looker Dashboards]""", "mermaid"))
    
    blocks.append(create_divider())
    
    # ========== 10. ROLLOUT PLAN ==========
    blocks.append(create_heading_1("10. 🚀 Rollout Plan"))
    
    blocks.append(create_heading_2("10.1 Timeline Overview"))
    
    blocks.append(create_simple_paragraph(
        "Development Start: February 10, 2026\n"
        "Target Launch: April 1, 2026\n"
        "Total Duration: ~7 weeks"
    ))
    
    blocks.append(create_heading_2("10.2 Phase 1: Development (Feb 10 - Mar 15)"))
    
    blocks.append(create_heading_3("Week 1-2: Foundation"))
    blocks.append(create_bullet("Set up Chat Backend Service infrastructure"))
    blocks.append(create_bullet("Implement WebSocket/Socket.IO server"))
    blocks.append(create_bullet("Design and implement database schema"))
    blocks.append(create_bullet("Create Flutter SDK project structure"))
    blocks.append(create_bullet("Create Web Widget project structure"))
    
    blocks.append(create_heading_3("Week 3-4: Core Features"))
    blocks.append(create_bullet("Implement message sending/receiving"))
    blocks.append(create_bullet("AI Chatbot Orchestrator integration"))
    blocks.append(create_bullet("Basic message types (text, image, document)"))
    blocks.append(create_bullet("Authentication integration"))
    
    blocks.append(create_heading_3("Week 5-6: Advanced Features"))
    blocks.append(create_bullet("Rich message types (carousel, buttons)"))
    blocks.append(create_bullet("File upload functionality"))
    blocks.append(create_bullet("Salesforce integration"))
    blocks.append(create_bullet("Multi-threading support"))
    
    blocks.append(create_heading_2("10.3 Phase 2: Testing (Mar 16 - Mar 25)"))
    
    blocks.append(create_bullet("Internal testing with QA team"))
    blocks.append(create_bullet("Integration testing with Salesforce"))
    blocks.append(create_bullet("Performance testing (load testing up to 30k concurrent sessions)"))
    blocks.append(create_bullet("Security testing and penetration testing"))
    blocks.append(create_bullet("UAT with internal stakeholders"))
    
    blocks.append(create_heading_2("10.4 Phase 3: Phased Rollout (Mar 26 - Apr 1)"))
    
    blocks.append(create_callout(
        "Feature Gate: Statsig will be used to control which users see the new chat experience. "
        "This allows for gradual rollout and instant rollback if issues arise.",
        "🚦"
    ))
    
    blocks.append(create_heading_3("Rollout Schedule"))
    
    blocks.append(create_bullet("Mar 26: 5% of users (internal + beta testers)"))
    blocks.append(create_bullet("Mar 28: 25% of users"))
    blocks.append(create_bullet("Mar 30: 50% of users"))
    blocks.append(create_bullet("Apr 1: 100% of users (GA)"))
    
    blocks.append(create_heading_3("Rollback Criteria"))
    
    blocks.append(create_bullet("Error rate exceeds 1%"))
    blocks.append(create_bullet("Message delivery latency exceeds 2 seconds (P95)"))
    blocks.append(create_bullet("Salesforce sync failure rate exceeds 5%"))
    blocks.append(create_bullet("Critical bugs reported by users"))
    
    blocks.append(create_heading_2("10.5 Fallback Mechanism"))
    
    blocks.append(create_callout(
        "Automatic Fallback: If the new chat system experiences issues, users will automatically "
        "be redirected to the existing Salesforce Chat Widget. This is controlled by the Statsig "
        "feature gate and health check monitoring.",
        "⚡"
    ))
    
    blocks.append(create_bullet("Health check endpoint monitors new chat system"))
    blocks.append(create_bullet("If health check fails 3 consecutive times, trigger fallback"))
    blocks.append(create_bullet("Users seamlessly redirected to Salesforce Chat Widget"))
    blocks.append(create_bullet("Automatic recovery when health check passes"))
    
    blocks.append(create_divider())
    
    # ========== 11. TECHNICAL SPECIFICATIONS ==========
    blocks.append(create_heading_1("11. ⚙️ Technical Specifications"))
    
    blocks.append(create_heading_2("11.1 Technology Stack"))
    
    blocks.append(create_heading_3("Flutter SDK"))
    blocks.append(create_bullet("Flutter 3.x"))
    blocks.append(create_bullet("Dart 3.x"))
    blocks.append(create_bullet("socket_io_client for WebSocket"))
    blocks.append(create_bullet("flutter_secure_storage for token storage"))
    blocks.append(create_bullet("cached_network_image for image handling"))
    
    blocks.append(create_heading_3("Web Widget"))
    blocks.append(create_bullet("React 18"))
    blocks.append(create_bullet("TypeScript"))
    blocks.append(create_bullet("Socket.IO client"))
    blocks.append(create_bullet("Styled Components / CSS Modules"))
    blocks.append(create_bullet("Bundled as UMD for easy embedding"))
    
    blocks.append(create_heading_3("Chat Backend"))
    blocks.append(create_bullet("Node.js / Go (TBD based on team expertise)"))
    blocks.append(create_bullet("Socket.IO server"))
    blocks.append(create_bullet("PostgreSQL for persistence"))
    blocks.append(create_bullet("Redis for caching and pub/sub"))
    blocks.append(create_bullet("Kubernetes deployment"))
    
    blocks.append(create_heading_2("11.2 API Contracts"))
    
    blocks.append(create_heading_3("WebSocket Events"))
    
    blocks.append(create_code_block("""// Client -> Server Events
{
  "connect": { token: string },
  "message:send": { 
    thread_id: string, 
    content: string, 
    type: "text" | "image" | "document",
    attachments?: [{ url: string, type: string, name: string }]
  },
  "typing:start": { thread_id: string },
  "typing:stop": { thread_id: string },
  "thread:create": { initial_message: string },
  "thread:archive": { thread_id: string }
}

// Server -> Client Events
{
  "message:new": {
    id: string,
    thread_id: string,
    content: string,
    type: "text" | "carousel" | "buttons" | "system",
    sender: "user" | "bot" | "agent",
    timestamp: string,
    metadata?: object
  },
  "thread:updated": { thread_id: string, status: string },
  "typing:indicator": { thread_id: string, sender: string },
  "agent:assigned": { thread_id: string, agent_name: string },
  "error": { code: string, message: string }
}""", "typescript"))
    
    blocks.append(create_heading_3("REST API Endpoints"))
    
    blocks.append(create_code_block("""// Chat Service REST API

GET /api/v1/threads
  - List all threads for authenticated user
  - Query params: status, limit, cursor

GET /api/v1/threads/:thread_id/messages
  - Get messages for a thread
  - Query params: limit, before_id, after_id

POST /api/v1/threads
  - Create new thread
  - Body: { initial_message: string }

POST /api/v1/threads/:thread_id/messages
  - Send message (alternative to WebSocket)
  - Body: { content: string, type: string, attachments?: [] }

POST /api/v1/upload
  - Upload file
  - Multipart form data
  - Returns: { url: string, file_id: string }

GET /api/v1/health
  - Health check endpoint
  - Returns: { status: "healthy" | "degraded" | "unhealthy" }""", "typescript"))
    
    blocks.append(create_heading_2("11.3 Database Schema"))
    
    blocks.append(create_code_block("""erDiagram
    THREADS ||--o{ MESSAGES : contains
    THREADS }o--|| USERS : belongs_to
    THREADS ||--o| SF_CASES : linked_to
    MESSAGES }o--|| ATTACHMENTS : has
    
    THREADS {
        uuid id PK
        uuid user_id FK
        string customer_id
        string title
        string status
        string channel
        datetime created_at
        datetime updated_at
        string sf_case_id
        string sf_messaging_session_id
        json metadata
    }
    
    MESSAGES {
        uuid id PK
        uuid thread_id FK
        string sender_type
        string sender_id
        text content
        string message_type
        datetime sent_at
        boolean is_read
        json rich_content
    }
    
    ATTACHMENTS {
        uuid id PK
        uuid message_id FK
        string file_name
        string file_type
        integer file_size
        string s3_url
        string sf_content_version_id
        datetime uploaded_at
    }
    
    USERS {
        uuid id PK
        string customer_id
        string email
        string phone
        string name
        string locale
        datetime created_at
    }
    
    SF_CASES {
        uuid id PK
        uuid thread_id FK
        string case_id
        string case_number
        string status
        datetime created_at
        datetime synced_at
    }""", "mermaid"))
    
    blocks.append(create_divider())
    
    # ========== 12. DESIGN GUIDELINES ==========
    blocks.append(create_heading_1("12. 🎨 Design Guidelines & Branding"))
    
    blocks.append(create_callout(
        "⚠️ PLACEHOLDER: Design specifications, mockups, and branding guidelines to be added by the Design Team.",
        "🎨"
    ))
    
    blocks.append(create_heading_2("12.1 Design Requirements"))
    
    blocks.append(create_bullet("Follow Tamara Design System"))
    blocks.append(create_bullet("Consistent with existing app UI/UX"))
    blocks.append(create_bullet("Mobile-first responsive design"))
    blocks.append(create_bullet("Accessibility compliance (WCAG 2.1 AA)"))
    blocks.append(create_bullet("Support for both light and dark modes"))
    
    blocks.append(create_heading_2("12.2 Branding Elements"))
    
    blocks.append(create_bullet("Primary brand colors"))
    blocks.append(create_bullet("Typography (font family, sizes, weights)"))
    blocks.append(create_bullet("Icon library"))
    blocks.append(create_bullet("Animation guidelines"))
    blocks.append(create_bullet("Spacing and layout grid"))
    
    blocks.append(create_heading_2("12.3 Design Deliverables"))
    
    blocks.append(create_bullet("Figma designs for Flutter SDK UI components"))
    blocks.append(create_bullet("Figma designs for Web Widget"))
    blocks.append(create_bullet("Interactive prototypes"))
    blocks.append(create_bullet("Design specifications document"))
    blocks.append(create_bullet("Asset library (icons, illustrations)"))
    
    blocks.append(create_divider())
    
    # ========== 13. STAKEHOLDERS ==========
    blocks.append(create_heading_1("13. 👥 Key Stakeholders & Approvers"))
    
    blocks.append(create_callout(
        "⚠️ PLACEHOLDER: Stakeholder and approver details to be added.",
        "👤"
    ))
    
    blocks.append(create_heading_2("13.1 Product"))
    blocks.append(create_bullet("[Name] - Product Manager"))
    blocks.append(create_bullet("[Name] - Product Owner"))
    
    blocks.append(create_heading_2("13.2 Engineering"))
    blocks.append(create_bullet("[Name] - Engineering Manager"))
    blocks.append(create_bullet("[Name] - Tech Lead - Mobile"))
    blocks.append(create_bullet("[Name] - Tech Lead - Backend"))
    blocks.append(create_bullet("[Name] - Tech Lead - Web"))
    
    blocks.append(create_heading_2("13.3 Operations"))
    blocks.append(create_bullet("[Name] - Customer Care Operations Lead"))
    blocks.append(create_bullet("[Name] - Partner Care Operations Lead"))
    
    blocks.append(create_heading_2("13.4 Other Stakeholders"))
    blocks.append(create_bullet("[Name] - Cyber Security"))
    blocks.append(create_bullet("[Name] - Data Team"))
    blocks.append(create_bullet("[Name] - Design Lead"))
    blocks.append(create_bullet("[Name] - Salesforce Admin"))
    
    blocks.append(create_heading_2("13.5 Approvals Required"))
    
    blocks.append(create_bullet("[ ] Product Review"))
    blocks.append(create_bullet("[ ] Technical Review"))
    blocks.append(create_bullet("[ ] Security Review"))
    blocks.append(create_bullet("[ ] Data Team Review"))
    blocks.append(create_bullet("[ ] Design Review"))
    blocks.append(create_bullet("[ ] Operations Review"))
    
    blocks.append(create_divider())
    
    # ========== 14. DEPENDENCIES & RISKS ==========
    blocks.append(create_heading_1("14. ⚠️ Dependencies & Risks"))
    
    blocks.append(create_heading_2("14.1 Dependencies"))
    
    blocks.append(create_bullet("AI Chatbot Orchestrator must be ready for integration", "AI Team"))
    blocks.append(create_bullet("Salesforce API access and permissions", "Salesforce Admin"))
    blocks.append(create_bullet("Tamara Auth Service token validation endpoint", "Platform Team"))
    blocks.append(create_bullet("S3 bucket setup for file storage", "Infrastructure"))
    blocks.append(create_bullet("Statsig feature gate configuration", "Infrastructure"))
    blocks.append(create_bullet("Push notification service integration", "Mobile Team"))
    
    blocks.append(create_heading_2("14.2 Risks & Mitigations"))
    
    risks = [
        ("Timeline Risk", "Aggressive 7-week timeline", "Prioritize MVP features, defer nice-to-haves", "Medium"),
        ("Integration Risk", "Complex Salesforce integration", "Early integration testing, dedicated SF admin support", "High"),
        ("Performance Risk", "Handling 30k daily chats", "Load testing, auto-scaling infrastructure", "Medium"),
        ("Adoption Risk", "Users may resist change", "Phased rollout, fallback mechanism, user feedback loop", "Low"),
        ("Data Loss Risk", "Message delivery failures", "Message queuing, retry mechanisms, monitoring", "Medium"),
    ]
    
    for risk, desc, mitigation, severity in risks:
        blocks.append(create_bullet(f"{risk} ({severity}): {desc}"))
        blocks.append(create_bullet(f"  Mitigation: {mitigation}"))
    
    blocks.append(create_divider())
    
    # ========== 15. APPENDIX ==========
    blocks.append(create_heading_1("15. 📎 Appendix"))
    
    blocks.append(create_heading_2("15.1 Glossary"))
    
    glossary = [
        ("BSAT", "Bot Satisfaction Score - measure of customer satisfaction with chatbot interactions"),
        ("Messaging Session", "Salesforce object representing a chat conversation"),
        ("Person Account", "Salesforce account type for B2C customers"),
        ("Omni-Channel", "Salesforce feature for routing cases to agents"),
        ("Socket.IO", "Real-time bidirectional event-based communication library"),
        ("Statsig", "Feature flagging and A/B testing platform"),
    ]
    
    for term, definition in glossary:
        blocks.append(create_bullet(f"{term}: {definition}"))
    
    blocks.append(create_heading_2("15.2 Related Documents"))
    
    blocks.append(create_bullet("Salesforce for Care - Integration Technical Documentation"))
    blocks.append(create_bullet("AI Chatbot Orchestrator PRD"))
    blocks.append(create_bullet("Tamara Design System"))
    blocks.append(create_bullet("Tamara API Documentation"))
    
    blocks.append(create_heading_2("15.3 Change Log"))
    
    blocks.append(create_bullet("v1.0 (Feb 3, 2026) - Initial draft"))
    
    blocks.append(create_divider())
    
    blocks.append(create_paragraph([
        create_rich_text("End of Document", italic=True)
    ]))
    
    return blocks


async def create_prd_page(parent_page_id: str):
    """Create the PRD page in Notion under the specified parent page."""
    context = load_context_from_env()
    
    if not context.notion_api_key:
        print("❌ Notion API key not configured.")
        print("   Please set NOTION_API_KEY in your .env file")
        return None
    
    notion_client = NotionClient(context.notion_api_key)
    
    # Create blocks
    blocks = create_notion_blocks()
    
    print(f"Creating Tamara Chat System PRD in Notion...")
    print(f"Parent page ID: {parent_page_id}")
    print(f"Total blocks to create: {len(blocks)}")
    
    # Create page properties
    properties = {
        "title": {
            "title": [
                {"type": "text", "text": {"content": "PRD: Tamara Native Chat System (Flutter SDK + Web Widget)"}}
            ]
        }
    }
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create page as child of parent page
            payload = {
                "parent": {"page_id": parent_page_id},
                "properties": properties
            }
            
            print("Creating page...")
            response = await client.post(
                f"{notion_client.base_url}/pages",
                headers=notion_client.headers,
                json=payload
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to create page: {response.status_code}")
                print(f"Response: {response.text}")
                return None
            
            page_data = response.json()
            page_id = page_data["id"]
            print(f"✅ Page created with ID: {page_id}")
            
            # Add content blocks in batches (Notion API limit is 100 blocks per request)
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i:i + batch_size]
                print(f"Adding blocks {i + 1} to {min(i + batch_size, len(blocks))}...")
                
                response = await client.patch(
                    f"{notion_client.base_url}/blocks/{page_id}/children",
                    headers=notion_client.headers,
                    json={"children": batch}
                )
                
                if response.status_code != 200:
                    print(f"⚠️ Warning: Failed to add blocks {i + 1} to {min(i + batch_size, len(blocks))}")
                    print(f"Response: {response.text}")
                else:
                    print(f"✅ Added blocks successfully")
            
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            print(f"\n✅ PRD page created successfully!")
            print(f"   Page ID: {page_id}")
            print(f"   View at: {page_url}")
            return page_data
            
    except Exception as e:
        print(f"❌ Error creating page: {e}")
        import traceback
        traceback.print_exc()
        return None


def format_page_id(page_id: str) -> str:
    """Format page ID to include dashes."""
    # Remove any existing dashes
    clean_id = page_id.replace('-', '')
    
    # If it's a 32-char hex string, add dashes
    if len(clean_id) == 32:
        return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    
    return page_id


if __name__ == "__main__":
    # PRD Drafts page ID from the URL: https://www.notion.so/tamaracom/PRD-Drafts-2d462429127880968d0ac88efea7071e
    default_parent_page_id = "2d462429-1278-8096-8d0a-c88efea7071e"
    
    # Allow override via command line argument
    parent_page_id = sys.argv[1] if len(sys.argv) > 1 else default_parent_page_id
    parent_page_id = format_page_id(parent_page_id)
    
    print("=" * 80)
    print("Creating PRD: Tamara Native Chat System")
    print("=" * 80)
    print(f"\nTarget parent page: {parent_page_id}")
    print()
    
    result = asyncio.run(create_prd_page(parent_page_id))
    
    if not result:
        print("\n❌ Failed to create PRD page. Please check the error messages above.")
        sys.exit(1)

