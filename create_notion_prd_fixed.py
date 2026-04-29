#!/usr/bin/env python3
"""
Create a Notion-friendly PRD with all diagrams in markdown format.
Notion supports mermaid diagrams natively, so we'll use that.
"""

from pathlib import Path
from datetime import datetime


def create_notion_prd():
    """Create comprehensive PRD in markdown format for Notion."""
    
    date_str = datetime.now().strftime("%B %d, %Y")
    
    # Mermaid diagrams as separate strings to avoid f-string issues
    system_arch = """```mermaid
graph TB
    subgraph "Client Layer"
        A[Mobile App iOS] --> B[In-App Messaging UI]
        C[Mobile App Android] --> B
        D[Web App] --> B
    end
    
    subgraph "API Gateway"
        B --> E[Message API]
        B --> F[Thread API]
        B --> G[Notification API]
    end
    
    subgraph "Core Services"
        E --> H[Message Service]
        F --> I[Thread Management Service]
        G --> J[Push Notification Service]
        H --> K[Message Queue]
        I --> L[Thread Database]
        H --> L
    end
    
    subgraph "AI & Chatbot"
        K --> M[Chatbot Service]
        M --> N[Intent Detection]
        M --> O[Thread Titling AI]
        M --> P[Response Generation]
    end
    
    subgraph "Support Systems"
        H --> Q[Ticketing System]
        Q --> R[Ticket Status Updates]
        R --> H
        I --> S[Agent Workspace]
        S --> H
    end
    
    subgraph "Data Layer"
        L --> T[(PostgreSQL)]
        K --> U[(Redis Cache)]
        V[(Message History DB)] --> H
    end
    
    subgraph "External Services"
        J --> W[FCM/APNS]
        O --> X[Gemini AI API]
        N --> X
    end
```"""
    
    sequence_diagram = """```mermaid
sequenceDiagram
    participant C as Customer
    participant UI as In-App UI
    participant API as Message API
    participant MSG as Message Service
    participant CHAT as Chatbot
    participant TICKET as Ticketing System
    participant AGENT as Support Agent
    participant NOTIF as Notification Service
    
    C->>UI: Opens Messages tab
    UI->>API: Get all threads
    API->>MSG: Fetch user threads
    MSG-->>API: Return thread list
    API-->>UI: Display threads
    UI-->>C: Show inbox
    
    C->>UI: Starts new conversation
    UI->>API: Create new thread
    API->>MSG: Initialize thread
    MSG->>CHAT: Route message
    CHAT->>CHAT: Detect intent
    CHAT->>CHAT: Generate thread title
    CHAT-->>MSG: Response + title
    MSG->>API: Thread created
    API->>NOTIF: Send notification
    API-->>UI: Display thread
    UI-->>C: Show conversation
    
    alt Chatbot resolves
        CHAT-->>C: Provide solution
    else Escalation needed
        CHAT->>TICKET: Create ticket
        TICKET->>MSG: Ticket created event
        MSG->>API: Status update
        API->>UI: Show ticket status
        UI-->>C: "Ticket created"
        TICKET->>AGENT: Assign ticket
        AGENT->>MSG: Agent response
        MSG->>API: New message
        API->>NOTIF: Push notification
        API->>UI: Update thread
        UI-->>C: Show agent message
    end
```"""
    
    journey_diagram = """```mermaid
journey
    title Customer Support Journey - In-App Messaging
    section Discovery
      Customer has issue: 3: Customer
      Opens Tamara app: 4: Customer
      Navigates to Messages tab: 5: Customer
    section Initiation
      Starts new conversation: 5: Customer
      Chatbot greets and understands intent: 4: System
      AI creates thread with title: 5: System
    section Resolution
      Chatbot attempts resolution: 4: System
      Customer provides info: 3: Customer
      Issue resolved OR escalated: 5: System
    section Escalation (if needed)
      Ticket created automatically: 4: System
      Agent assigned: 4: System
      Customer sees status update: 5: Customer
      Agent responds in thread: 5: Agent
      Issue resolved: 5: Customer
    section Follow-up
      Customer returns to thread: 4: Customer
      Sees full history: 5: Customer
      Continues conversation: 4: Customer
```"""
    
    state_machine = """```mermaid
stateDiagram-v2
    [*] --> New: Customer starts conversation
    New --> ChatbotActive: First message sent
    ChatbotActive --> ChatbotActive: Chatbot responds
    ChatbotActive --> Resolved: Issue resolved by chatbot
    ChatbotActive --> Escalated: Escalation needed
    Escalated --> TicketCreated: Ticket system creates ticket
    TicketCreated --> AgentAssigned: Agent assigned
    AgentAssigned --> InProgress: Agent responds
    InProgress --> WaitingForCustomer: Agent asks for info
    WaitingForCustomer --> InProgress: Customer responds
    InProgress --> Resolved: Issue resolved
    Resolved --> [*]
    ChatbotActive --> Archived: Customer abandons
    InProgress --> Archived: No activity for 30 days
    Archived --> [*]
```"""
    
    erd_diagram = """```mermaid
erDiagram
    THREADS ||--o{ MESSAGES : contains
    THREADS ||--o| TICKETS : linked_to
    THREADS }o--|| USERS : belongs_to
    MESSAGES }o--|| USERS : sent_by
    MESSAGES }o--o| AGENTS : handled_by
    TICKETS ||--o{ TICKET_EVENTS : has
    THREADS }o--o{ THREAD_METADATA : has
    
    THREADS {
        uuid id PK
        uuid user_id FK
        string title
        string status
        datetime created_at
        datetime updated_at
        json metadata
        string ai_title
    }
    
    MESSAGES {
        uuid id PK
        uuid thread_id FK
        uuid user_id FK
        uuid agent_id FK
        string content
        string type
        datetime sent_at
        boolean read
        json attachments
    }
    
    TICKETS {
        uuid id PK
        uuid thread_id FK
        string status
        string priority
        datetime created_at
        datetime resolved_at
        uuid assigned_agent_id FK
    }
    
    TICKET_EVENTS {
        uuid id PK
        uuid ticket_id FK
        string event_type
        string description
        datetime occurred_at
    }
    
    USERS {
        uuid id PK
        string email
        string name
    }
    
    AGENTS {
        uuid id PK
        string name
        string email
    }
    
    THREAD_METADATA {
        uuid id PK
        uuid thread_id FK
        string intent
        json entities
        string category
    }
```"""
    
    integration_diagram = """```mermaid
flowchart LR
    subgraph "In-App Messaging Inbox"
        A[Thread Management]
        B[Message Handling]
        C[UI Components]
    end
    
    subgraph "Unified Messaging Platform"
        D[Message Router]
        E[Notification Center]
        F[Channel Manager]
    end
    
    subgraph "AI Sidekick"
        G[Chatbot Engine]
        H[Intent Detection]
        I[Thread Titling]
    end
    
    subgraph "Support Systems"
        J[Ticketing System]
        K[Agent Workspace]
        L[Knowledge Base]
    end
    
    A --> D
    B --> D
    D --> G
    G --> H
    G --> I
    D --> J
    J --> K
    G --> L
    D --> E
    E --> C
    K --> B
```"""
    
    content = f"""# Product Requirements Document

# In-App Customer Messaging Inbox

**Version:** 1.0  
**Phase:** Phase 1 - Q1 2026  
**Generated:** {date_str}

---

## 📌 Introduction

This PRD defines the comprehensive requirements for building an **In-App Customer Messaging Inbox** to replace email as the primary asynchronous communication channel between customers and Tamara. This initiative will embed live chat conversations and support ticket updates in one unified, persistent experience within the Tamara mobile and web applications.

The end-state user experience will be similar to **Airbnb's Messages tab**, which serves as a single inbox for all conversations (including support) with clear threads, search functionality, and a consistent place for customers to follow up on ongoing issues.

This work is a critical component of Tamara's customer support transformation and must align with the **Unified In-App Messaging and AI Sidekick** initiative being developed by another team. This PRD focuses specifically on the customer-facing messaging inbox experience while ensuring seamless integration with the broader messaging infrastructure.

**Related PRD:** [Unified In-App Messaging and AI Sidekick](https://www.notion.so/tamaracom/PRD-Unified-in-app-messaging-AI-sidekick-for-Q1-2026-2aa62429127880769e6dc4e481985a5a)

---

## ❗ Problem Statement

Currently, customer support communication at Tamara relies heavily on email, which creates several significant problems that impact both customer satisfaction and operational efficiency.

### Core Problems

**1. Fragmented Communication Channels**
- Customers lose context when switching between email, in-app chat, and other channels
- No single source of truth for support interactions
- *Impact:* High customer effort, context loss, repeat explanations

**2. Slow Response Times**
- Email-based support creates delays and requires customers to check multiple inboxes
- Customers cannot see real-time status of their requests
- *Impact:* Poor customer experience, perceived lack of responsiveness

**3. Poor Thread Tracking**
- Email threads are difficult to track across devices and sessions
- Customers lose track of previous conversations
- *Impact:* Increased repeat contacts, customer frustration

**4. Lack of Visibility**
- Customers cannot easily see the status of their support requests without sending follow-up emails
- No real-time updates on ticket progress
- *Impact:* Reduced transparency, increased support volume

**5. Context Loss**
- Each new email or chat session starts from scratch, requiring customers to re-explain their issues
- No persistent conversation history
- *Impact:* Inefficient support operations, poor customer experience

**6. Mixed Topics**
- Without clear thread separation, customers mix unrelated issues in single conversations
- Makes it hard to track and resolve multiple problems
- *Impact:* Confusion, delayed resolution, poor organization

**7. No Unified History**
- Support interactions, chatbot conversations, and ticket updates exist in separate systems
- No unified view of customer journey
- *Impact:* Incomplete customer journey visibility, fragmented experience

### Quantitative Impact

Based on current support metrics:

- Email support accounts for **65%** of all support contacts
- Average time to first response: **4.2 hours** via email
- Repeat contact rate: **42%** (customers contacting again for same issue)
- Customer satisfaction (CSAT) for email support: **3.2/5.0**
- Average resolution time: **48 hours** for email-based issues
- Chatbot containment rate: **35%** (65% escalate to email)

---

## 🎯 Goals

### 1. Replace Email as Primary Async Channel
**Description:** Make in-app messaging the default and preferred method for asynchronous customer support communication.

**Target:** Reduce reliance on email by at least **60%** within 6 months of launch

### 2. Unify Customer Communication Experience
**Description:** Provide a single, persistent inbox where customers can access all their conversations with Tamara, including chatbot interactions, agent conversations, and support ticket updates.

**Target:** **80%** of support interactions happen in-app within 3 months

### 3. Improve Customer Visibility and Transparency
**Description:** Give customers real-time visibility into the status of their support requests without requiring them to contact support again.

**Target:** Reduce "status check" contacts by **50%**

### 4. Reduce Repeat Contacts
**Description:** Enable customers to easily find and continue previous conversations, reducing the need to re-explain issues.

**Target:** Decrease repeat contact rate by **30%**

### 5. Increase Chatbot Containment
**Description:** Keep the entire support journey within a single thread, allowing chatbot to handle initial intents and seamlessly escalate to agents when needed.

**Target:** Increase chatbot containment by **25%**

### 6. Enable Multi-Threaded Conversations
**Description:** Allow customers to maintain separate conversation threads for different topics (e.g., refunds, order issues, account problems).

**Target:** **70%** of customers with multiple issues use separate threads

---

## 📊 Success Metrics (must align with CPX 2025)

The following metrics will be tracked to measure success. All metrics align with CPX 2025 objectives and squad priorities.

| Metric | Target | Baseline | Measurement |
|--------|--------|----------|-------------|
| **Email Support Volume Reduction** | 60% reduction within 6 months | Current monthly email support volume | Monthly email support ticket count |
| **Repeat Contact Rate** | 30% reduction | Current repeat contact rate (42%) | Percentage of contacts that reference a previous interaction |
| **Customer Satisfaction (CSAT)** | 15% increase | Current support CSAT (3.2/5.0) | Post-interaction CSAT surveys |
| **Chatbot Containment Rate** | 25% increase | Current chatbot containment (35%) | Percentage of chatbot conversations resolved without agent escalation |
| **Time to Resolution Perception** | 20% improvement | Current customer-reported wait time perception | Customer surveys and feedback |
| **In-App Messaging Adoption** | 80% of eligible customers use it within 3 months | 0% (new feature) | Percentage of active customers who initiate at least one in-app message |
| **Thread Continuity** | 70% of conversations continue in same thread | N/A (new capability) | Percentage of threads with multiple messages across different sessions |

---

## 👤 User Personas

### Frequent Support User
**Description:** Customers who regularly contact support for order issues, refunds, or account problems. They value quick responses and the ability to track multiple ongoing issues.

**Key Needs:**
- Quick access to all ongoing conversations
- Clear status updates on open issues
- Ability to attach documents and screenshots
- Search functionality to find previous conversations

### Occasional Support Seeker
**Description:** Customers who contact support infrequently but need help when they do. They may not be familiar with support processes and need clear guidance.

**Key Needs:**
- Easy-to-find support entry point
- Clear instructions on how to get help
- Reassurance that their issue is being tracked
- Simple interface that doesn't require learning

### Tech-Savvy Power User
**Description:** Customers comfortable with technology who expect modern, efficient communication channels. They prefer in-app experiences over email.

**Key Needs:**
- Fast, responsive interface
- Rich features like file sharing and formatting
- Keyboard shortcuts and efficiency features
- Integration with other app features

### Mobile-First User
**Description:** Customers who primarily or exclusively use mobile devices. They need a mobile-optimized experience that works well on small screens.

**Key Needs:**
- Mobile-optimized interface
- Push notifications for new messages
- Easy photo/document attachment from mobile
- Offline message queuing

---

## 💡 Solution

Implement an **In-App Customer Messaging Inbox (Phase 1)** as a replacement for email-based customer support communication, centered around a persistent support inbox inside the Tamara app.

### Core Components (Phase 1)

#### 1. Support Inbox (Async Messaging)

A dedicated inbox where customers can message Tamara directly from the app. Conversations are asynchronous by default, allowing replies over hours or days without losing context (unlike email). Each conversation persists as a long-lived thread rather than a one-off chat session.

**Key Features:**
- Dedicated "Messages" or "Support" tab in the app navigation
- Inbox view showing all conversation threads
- Thread list with preview of last message, timestamp, and status
- Unread message indicators and badges
- Persistent conversation history across app sessions
- Cross-device synchronization
- Push notifications for new messages

#### 2. Multi-Threaded Chat Conversations

Every new chatbot conversation creates a new thread in the inbox (even if it never gets handed to an agent). Threads are titled automatically using AI, based on detected intent and key entities (e.g., "Refund status – Order 12345", "Card verification issue", "Payment not reflected"). This keeps conversations clean and searchable, and prevents customers from mixing unrelated topics in one long chat history.

**Key Features:**
- Automatic thread creation for each new conversation
- AI-powered thread titling based on intent and entities
- Manual thread creation option for customers
- Thread organization and categorization
- Thread search and filtering
- Thread archiving and deletion
- Thread status indicators (active, waiting, resolved)

#### 3. Ticket Updates Embedded in Threads

When a support ticket is created, updated, or resolved, the customer sees system messages inside the relevant thread (e.g., "Ticket created", "Awaiting information", "Resolved"). This removes the need for status update emails and gives customers real-time visibility into progress without contacting support again.

**Key Features:**
- Automatic ticket creation from conversations
- Real-time ticket status updates in thread
- System messages for key ticket events
- Visual indicators for ticket status
- Link to full ticket details when needed
- Timeline view of ticket lifecycle
- Integration with existing ticketing system

**Note:** Phase 1 intentionally excludes advanced automation and focuses on clarity, continuity, and replacing email as the primary async channel.

---

## 📐 Solution Design

### User Experience Flow

1. Customer opens the Tamara app and navigates to the "Messages" or "Support" tab
2. Inbox view displays all conversation threads, sorted by most recent activity
3. Customer can:
   - Tap an existing thread to continue the conversation
   - Tap "New Message" to start a new conversation
   - Use search to find previous conversations
4. When starting a new conversation, chatbot handles initial interaction
5. If escalation is needed, conversation seamlessly transitions to an agent
6. Ticket updates appear as system messages in the thread
7. Customer receives push notifications for new messages
8. Conversation persists across app sessions and devices

### System Architecture

{system_arch}

### Message Flow Sequence Diagram

{sequence_diagram}

### Customer Journey Flow

{journey_diagram}

### Thread State Machine

{state_machine}

### Database Schema (Entity Relationship Diagram)

{erd_diagram}

### Integration Architecture

{integration_diagram}

### System Components

**Client Layer:**
- Mobile App (iOS and Android)
- Web App
- In-App Messaging UI components

**API Gateway:**
- Message API - handles message operations
- Thread API - manages thread lifecycle
- Notification API - push notification management

**Core Services:**
- Message Service - message processing and delivery
- Thread Management Service - thread creation, organization, and metadata
- Push Notification Service - cross-platform notification delivery
- Message Queue - async message processing
- Thread Database - persistent storage

**AI & Chatbot Integration:**
- Chatbot Service - handles initial customer interactions
- Intent Detection - identifies customer needs
- Thread Titling AI - generates descriptive thread titles using Gemini
- Response Generation - creates contextual responses

**Support Systems Integration:**
- Ticketing System - creates and manages support tickets
- Ticket Status Updates - real-time status synchronization
- Agent Workspace - enables agent responses within threads

**Data Layer:**
- PostgreSQL - primary database for threads and messages
- Redis Cache - real-time data and session management
- Message History DB - long-term message storage

**External Services:**
- FCM/APNS - push notification delivery
- Gemini AI API - thread titling and intent detection

### Integration Points

This initiative must align with:

- **Unified In-App Messaging and AI Sidekick PRD** - [Reference](https://www.notion.so/tamaracom/PRD-Unified-in-app-messaging-AI-sidekick-for-Q1-2026-2aa62429127880769e6dc4e481985a5a)
- Existing chatbot and AI infrastructure
- Current support ticketing system
- Notification center (being built by another team)

---

## 🔧 Technical Specifications

### Performance Requirements

- **Message delivery:** < 2 seconds p95 latency
- **Thread loading:** < 1 second for inbox view
- **Real-time updates:** WebSocket connection with < 500ms latency
- **Offline support:** Queue messages locally, sync when online
- **Search functionality:** < 500ms response time for thread search

### Scalability Requirements

- Support **1M+** concurrent users
- Handle **10K+** messages per minute
- **99.9%** uptime SLA
- Horizontal scaling capability
- Database sharding support for high-volume users

### Security Requirements

- End-to-end encryption for sensitive data
- PII compliance (GDPR, local regulations)
- Authentication via existing Tamara auth system
- Rate limiting and abuse prevention
- Message content moderation
- Secure file attachment handling

### Database Schema Details

**THREADS Table:**
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key to USERS)
- `title` (String) - AI-generated or manual
- `status` (String) - active, waiting, resolved, archived
- `created_at` (Timestamp)
- `updated_at` (Timestamp)
- `metadata` (JSON) - additional thread information

**MESSAGES Table:**
- `id` (UUID, Primary Key)
- `thread_id` (UUID, Foreign Key to THREADS)
- `user_id` (UUID, Foreign Key to USERS) - nullable for system messages
- `agent_id` (UUID, Foreign Key to AGENTS) - nullable
- `content` (Text)
- `type` (String) - user, agent, system
- `sent_at` (Timestamp)
- `read` (Boolean)
- `attachments` (JSON) - file metadata

**TICKETS Table:**
- `id` (UUID, Primary Key)
- `thread_id` (UUID, Foreign Key to THREADS)
- `status` (String) - created, assigned, in_progress, waiting, resolved
- `priority` (String) - low, medium, high, urgent
- `created_at` (Timestamp)
- `resolved_at` (Timestamp) - nullable
- `assigned_agent_id` (UUID, Foreign Key to AGENTS)

**Relationships:**
- One user can have many threads
- One thread can have many messages
- One thread can be linked to one ticket
- Messages can be from user or agent
- Thread metadata stores AI-generated title and intent

### API Specifications

#### REST Endpoints

**Threads API:**
- `GET /api/v1/threads` - List all user threads
- `POST /api/v1/threads` - Create new thread
- `GET /api/v1/threads/{{id}}` - Get thread details
- `PATCH /api/v1/threads/{{id}}` - Update thread (archive, etc.)

**Messages API:**
- `GET /api/v1/threads/{{id}}/messages` - Get thread messages
- `POST /api/v1/threads/{{id}}/messages` - Send message
- `PUT /api/v1/messages/{{id}}/read` - Mark as read

#### WebSocket Events

- `thread.updated` - Thread metadata changed
- `message.new` - New message received
- `ticket.status_changed` - Ticket status updated

---

## ✅ Inclusions and Exclusions

### Phase 1 Inclusions

- Support inbox with thread list and conversation view
- Async messaging (send/receive messages over time)
- Multi-threaded conversations with AI-powered titling
- Ticket status updates embedded in threads
- Basic search functionality
- Push notifications for new messages
- Cross-device synchronization
- Integration with existing chatbot
- Integration with ticketing system for status updates
- Mobile (iOS/Android) and web support
- Message persistence and history
- Real-time message delivery via WebSocket
- Offline message queuing
- File attachment support (images and documents)

### Phase 1 Exclusions

- Advanced automation and workflows
- Rich media support beyond basic images and documents
- Voice or video messaging
- Group conversations or team collaboration
- Advanced analytics dashboard for customers
- Custom notification preferences (beyond basic on/off)
- Integration with external messaging platforms
- Proactive messaging from Tamara (beyond ticket updates)
- Advanced AI features beyond thread titling
- Customer-facing admin or moderation tools
- Message editing or deletion
- Read receipts (beyond basic read/unread)
- Typing indicators

---

## 🚀 Roll-out Plan

### Phase 1 Timeline (Q1 2026)

#### Week 1-2: Design and Architecture
- Finalize UI/UX designs with design team
- Define API contracts and integration points
- Technical architecture review with platform team
- Database schema design and review
- Security and compliance review

#### Week 3-6: Core Development
- Build inbox UI and thread management
- Implement async messaging infrastructure
- Integrate with chatbot and ticketing system
- Develop AI thread titling feature
- Set up WebSocket infrastructure
- Implement push notifications
- Build search functionality

#### Week 7-8: Testing and Refinement
- Internal testing and bug fixes
- Integration testing with related systems
- Performance testing and optimization
- Security testing
- Load testing
- User acceptance testing with internal team

#### Week 9-10: Beta Launch
- Limited beta release to 5% of users
- Monitor metrics and gather feedback
- Iterate based on beta learnings
- Fix critical issues
- Prepare for full launch

#### Week 11-12: Full Launch
- Gradual rollout to 100% of users (10% → 50% → 100%)
- Marketing and user education
- Monitor success metrics
- Collect feedback
- Plan Phase 2 features

### Success Criteria for Launch

Before moving to full launch, we must achieve:

- **70%** of beta users successfully send at least one message
- Average response time under **2 seconds** for message delivery
- **Zero** critical bugs or data loss incidents
- **Positive feedback** from 80% of beta users
- Successful integration with all required systems
- All performance benchmarks met
- Security audit passed

---

## Hypothesis

If we replace email with an in-app support inbox that supports persistent, multi-threaded conversations and surfaces ticket updates directly in the conversation, customers will have better visibility into their issues, leading to:

- Fewer repeat contacts (**30% reduction**)
- Lower effort to follow up on issues
- Improved customer satisfaction (**15% increase in CSAT**)
- Higher chatbot containment rates (**25% increase**)
- Reduced email support volume (**60% reduction**)
- Better perceived transparency and trust

This will be measured through the success metrics defined above, with data collection starting from beta launch.

---

## Appendix

### Related Documents

**Unified In-App Messaging and AI Sidekick PRD:**
https://www.notion.so/tamaracom/PRD-Unified-in-app-messaging-AI-sidekick-for-Q1-2026-2aa62429127880769e6dc4e481985a5a

### Reference UX

**Airbnb Messages Tab:**
https://www.airbnb.ae/resources/hosting-homes/a/getting-the-most-out-of-the-messages-tab-678

---

*End of Document*
"""
    
    return content


if __name__ == "__main__":
    print("Creating Notion-friendly PRD with all diagrams...")
    content = create_notion_prd()
    
    output_file = Path("PRD_In-App_Messaging_Notion.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Notion-friendly PRD created!")
    print(f"📄 Saved to: {output_file.absolute()}")
    print(f"\nThis markdown file includes:")
    print("  ✅ All mermaid diagrams (Notion renders these natively)")
    print("  ✅ System architecture diagram")
    print("  ✅ Sequence diagrams")
    print("  ✅ State machine diagrams")
    print("  ✅ Database ERD")
    print("  ✅ Customer journey flow")
    print("  ✅ Integration architecture")
    print("  ✅ All sections properly formatted")
    print("\n💡 To use in Notion:")
    print("  1. Open the .md file")
    print("  2. Copy all content")
    print("  3. Paste into Notion - it will render all diagrams automatically!")



