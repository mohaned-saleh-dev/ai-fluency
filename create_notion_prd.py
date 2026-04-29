#!/usr/bin/env python3
"""
Create the PRD as a new Notion page in "My Space" folder.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent.integrations.notion_client import NotionClient
from prd_ticket_agent.config import load_context_from_env


def create_notion_blocks():
    """Create Notion blocks for the PRD content."""
    blocks = []
    
    # Title will be set as page property, so we start with content
    
    # Introduction
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "📌 Introduction"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": "This PRD defines the requirements for building an "},
                {"type": "text", "text": "In-App Customer Messaging Inbox", "bold": True},
                {"type": "text", "text": " to replace email as the primary asynchronous communication channel between customers and Tamara. This initiative will embed live chat conversations and support ticket updates in one unified, persistent experience within the Tamara mobile and web applications."}
            ]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "The end-state user experience will be similar to Airbnb's Messages tab, which serves as a single inbox for all conversations (including support) with clear threads, search functionality, and a consistent place for customers to follow up on ongoing issues."}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "This work aligns with and complements the Unified In-App Messaging and AI Sidekick initiative being developed by another team. This PRD focuses specifically on the customer-facing messaging inbox experience."}]
        }
    })
    
    # Problem Statement
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "❗ Problem Statement"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "Currently, customer support communication at Tamara relies heavily on email, which creates several significant problems:"}]
        }
    })
    
    problems = [
        "Fragmented communication: Customers lose context when switching between email, in-app chat, and other channels",
        "Slow response times: Email-based support creates delays and requires customers to check multiple inboxes",
        "Poor thread tracking: Email threads are difficult to track across devices and sessions",
        "Lack of visibility: Customers cannot easily see the status of their support requests without sending follow-up emails",
        "Context loss: Each new email or chat session starts from scratch, requiring customers to re-explain their issues",
        "Mixed topics: Without clear thread separation, customers mix unrelated issues in single conversations",
        "No unified history: Support interactions, chatbot conversations, and ticket updates exist in separate systems"
    ]
    
    for problem in problems:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": problem}]
            }
        })
    
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "These issues lead to:"}]
        }
    })
    
    impacts = [
        "Increased repeat contacts as customers lose track of previous conversations",
        "Higher customer effort to follow up on issues",
        "Reduced customer satisfaction due to perceived lack of transparency",
        "Lower chatbot containment rates as customers abandon chat and switch to email",
        "Inefficient support operations as agents spend time re-establishing context"
    ]
    
    for impact in impacts:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": impact}]
            }
        })
    
    # Goals
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "🎯 Goals"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "The primary goals of this initiative are:"}]
        }
    })
    
    goals = [
        ("Replace Email as Primary Async Channel", "Make in-app messaging the default and preferred method for asynchronous customer support communication, reducing reliance on email by at least 60% within 6 months of launch."),
        ("Unify Customer Communication Experience", "Provide a single, persistent inbox where customers can access all their conversations with Tamara, including chatbot interactions, agent conversations, and support ticket updates."),
        ("Improve Customer Visibility and Transparency", "Give customers real-time visibility into the status of their support requests without requiring them to contact support again, reducing perceived wait times and increasing trust."),
        ("Reduce Repeat Contacts", "Enable customers to easily find and continue previous conversations, reducing the need to re-explain issues and decreasing repeat contact rate by 30%."),
        ("Increase Chatbot Containment", "Keep the entire support journey within a single thread, allowing chatbot to handle initial intents and seamlessly escalate to agents when needed, improving containment rates."),
        ("Enable Multi-Threaded Conversations", "Allow customers to maintain separate conversation threads for different topics (e.g., refunds, order issues, account problems), preventing context mixing and improving organization.")
    ]
    
    for title, desc in goals:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": title, "bold": True}
                ]
            }
        })
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": desc}]
            }
        })
    
    # Success Metrics
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "📊 Success Metrics (must align with CPX 2025)"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "The following metrics will be tracked to measure success:"}]
        }
    })
    
    metrics = [
        ("Email Support Volume Reduction", "60% reduction in email-based support contacts within 6 months", "Current monthly email support volume", "Monthly email support ticket count"),
        ("Repeat Contact Rate", "30% reduction in repeat contacts for the same issue", "Current repeat contact rate", "Percentage of contacts that reference a previous interaction"),
        ("Customer Satisfaction (CSAT)", "Increase CSAT for support interactions by 15%", "Current support CSAT score", "Post-interaction CSAT surveys"),
        ("Chatbot Containment Rate", "Increase chatbot containment by 25%", "Current chatbot containment rate", "Percentage of chatbot conversations resolved without agent escalation"),
        ("Time to Resolution Perception", "Improve customer perception of response time by 20%", "Current customer-reported wait time perception", "Customer surveys and feedback"),
        ("In-App Messaging Adoption", "80% of eligible customers use in-app messaging for at least one support interaction within 3 months", "0% (new feature)", "Percentage of active customers who initiate at least one in-app message"),
        ("Thread Continuity", "70% of conversations continue in the same thread across multiple sessions", "N/A (new capability)", "Percentage of threads with multiple messages across different sessions")
    ]
    
    for metric, target, baseline, measurement in metrics:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": metric, "bold": True}
                ]
            }
        })
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"type": "text", "text": f"Target: {target}"}
                ]
            }
        })
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"type": "text", "text": f"Baseline: {baseline}"}
                ]
            }
        })
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"type": "text", "text": f"Measurement: {measurement}"}
                ]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": []}
        })
    
    # User Personas
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "👤 User Personas"}]
        }
    })
    
    personas = [
        ("Frequent Support User", "Customers who regularly contact support for order issues, refunds, or account problems. They value quick responses and the ability to track multiple ongoing issues.", [
            "Quick access to all ongoing conversations",
            "Clear status updates on open issues",
            "Ability to attach documents and screenshots",
            "Search functionality to find previous conversations"
        ]),
        ("Occasional Support Seeker", "Customers who contact support infrequently but need help when they do. They may not be familiar with support processes and need clear guidance.", [
            "Easy-to-find support entry point",
            "Clear instructions on how to get help",
            "Reassurance that their issue is being tracked",
            "Simple interface that doesn't require learning"
        ]),
        ("Tech-Savvy Power User", "Customers comfortable with technology who expect modern, efficient communication channels. They prefer in-app experiences over email.", [
            "Fast, responsive interface",
            "Rich features like file sharing and formatting",
            "Keyboard shortcuts and efficiency features",
            "Integration with other app features"
        ]),
        ("Mobile-First User", "Customers who primarily or exclusively use mobile devices. They need a mobile-optimized experience that works well on small screens.", [
            "Mobile-optimized interface",
            "Push notifications for new messages",
            "Easy photo/document attachment from mobile",
            "Offline message queuing"
        ])
    ]
    
    for name, desc, needs in personas:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": name, "bold": True}
                ]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": desc}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": "Key Needs:"}]
            }
        })
        for need in needs:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": need}]
                }
            })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": []}
        })
    
    # Solution
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "💡 Solution"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "Implement an In-App Customer Messaging Inbox (Phase 1) as a replacement for email-based customer support communication, centered around a persistent support inbox inside the Tamara app."}]
        }
    })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "Core Components (Phase 1)"}]
        }
    })
    
    components = [
        ("Support Inbox (Async Messaging)", "A dedicated inbox where customers can message Tamara directly from the app. Conversations are asynchronous by default, allowing replies over hours or days without losing context (unlike email). Each conversation persists as a long-lived thread rather than a one-off chat session.", [
            "Dedicated \"Messages\" or \"Support\" tab in the app navigation",
            "Inbox view showing all conversation threads",
            "Thread list with preview of last message, timestamp, and status",
            "Unread message indicators and badges",
            "Persistent conversation history across app sessions",
            "Cross-device synchronization",
            "Push notifications for new messages"
        ]),
        ("Multi-Threaded Chat Conversations", "Every new chatbot conversation creates a new thread in the inbox (even if it never gets handed to an agent). Threads are titled automatically using AI, based on detected intent and key entities (e.g., \"Refund status – Order 12345\", \"Card verification issue\", \"Payment not reflected\"). This keeps conversations clean and searchable, and prevents customers from mixing unrelated topics in one long chat history.", [
            "Automatic thread creation for each new conversation",
            "AI-powered thread titling based on intent and entities",
            "Manual thread creation option for customers",
            "Thread organization and categorization",
            "Thread search and filtering",
            "Thread archiving and deletion",
            "Thread status indicators (active, waiting, resolved)"
        ]),
        ("Ticket Updates Embedded in Threads", "When a support ticket is created, updated, or resolved, the customer sees system messages inside the relevant thread (e.g., \"Ticket created\", \"Awaiting information\", \"Resolved\"). This removes the need for status update emails and gives customers real-time visibility into progress without contacting support again.", [
            "Automatic ticket creation from conversations",
            "Real-time ticket status updates in thread",
            "System messages for key ticket events",
            "Visual indicators for ticket status",
            "Link to full ticket details when needed",
            "Timeline view of ticket lifecycle",
            "Integration with existing ticketing system"
        ])
    ]
    
    for name, desc, features in components:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": name, "bold": True}
                ]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": desc}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": "Key Features:"}]
            }
        })
        for feature in features:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": feature}]
                }
            })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": []}
        })
    
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "Phase 1 intentionally excludes advanced automation and focuses on clarity, continuity, and replacing email as the primary async channel."}]
        }
    })
    
    # Solution Design
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "📐 Solution Design"}]
        }
    })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "User Experience Flow"}]
        }
    })
    
    ux_steps = [
        "Customer opens the Tamara app and navigates to the \"Messages\" or \"Support\" tab",
        "Inbox view displays all conversation threads, sorted by most recent activity",
        "Customer can:",
        "  - Tap an existing thread to continue the conversation",
        "  - Tap \"New Message\" to start a new conversation",
        "  - Use search to find previous conversations",
        "When starting a new conversation, chatbot handles initial interaction",
        "If escalation is needed, conversation seamlessly transitions to an agent",
        "Ticket updates appear as system messages in the thread",
        "Customer receives push notifications for new messages",
        "Conversation persists across app sessions and devices"
    ]
    
    for i, step in enumerate(ux_steps):
        if step.startswith("  -"):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": step.strip()}]
                }
            })
        elif step.endswith(":"):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": step}]
                }
            })
        else:
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": step}]
                }
            })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "Technical Architecture"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "The solution will integrate with:"}]
        }
    })
    
    integrations = [
        "Existing chatbot infrastructure",
        "Current ticketing system (for status updates)",
        "Unified messaging platform (being built by another team)",
        "Push notification service",
        "User authentication and session management"
    ]
    
    for integration in integrations:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": integration}]
            }
        })
    
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "Key technical requirements:"}]
        }
    })
    
    tech_reqs = [
        "Real-time message delivery and synchronization",
        "Message persistence and history storage",
        "Thread management and organization",
        "AI integration for thread titling",
        "Cross-platform compatibility (iOS, Android, Web)",
        "Offline message queuing"
    ]
    
    for req in tech_reqs:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": req}]
            }
        })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "Integration Points"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "This initiative must align with:"}]
        }
    })
    
    alignment_points = [
        ("Unified In-App Messaging and AI Sidekick PRD", "https://www.notion.so/tamaracom/PRD-Unified-in-app-messaging-AI-sidekick-for-Q1-2026-2aa62429127880769e6dc4e481985a5a"),
        "Existing chatbot and AI infrastructure",
        "Current support ticketing system",
        "Notification center (being built by another team)"
    ]
    
    for point in alignment_points:
        if isinstance(point, tuple):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": f"{point[0]}: "},
                        {"type": "text", "text": point[1], "annotations": {"link": {"url": point[1]}}}
                    ]
                }
            })
        else:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": point}]
                }
            })
    
    # Inclusions and Exclusions
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "✅ Inclusions and Exclusions"}]
        }
    })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "Phase 1 Inclusions"}]
        }
    })
    
    inclusions = [
        "Support inbox with thread list and conversation view",
        "Async messaging (send/receive messages over time)",
        "Multi-threaded conversations with AI-powered titling",
        "Ticket status updates embedded in threads",
        "Basic search functionality",
        "Push notifications for new messages",
        "Cross-device synchronization",
        "Integration with existing chatbot",
        "Integration with ticketing system for status updates",
        "Mobile and web support",
        "Message persistence and history"
    ]
    
    for inclusion in inclusions:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": inclusion}]
            }
        })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "Phase 1 Exclusions"}]
        }
    })
    
    exclusions = [
        "Advanced automation and workflows",
        "Rich media support beyond basic images and documents",
        "Voice or video messaging",
        "Group conversations or team collaboration",
        "Advanced analytics dashboard for customers",
        "Custom notification preferences (beyond basic on/off)",
        "Integration with external messaging platforms",
        "Proactive messaging from Tamara (beyond ticket updates)",
        "Advanced AI features beyond thread titling",
        "Customer-facing admin or moderation tools"
    ]
    
    for exclusion in exclusions:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": exclusion}]
            }
        })
    
    # Roll-out Plan
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "🚀 Roll-out Plan"}]
        }
    })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "Phase 1 Timeline (Q1 2026)"}]
        }
    })
    
    timeline = [
        ("Week 1-2: Design and Architecture", [
            "Finalize UI/UX designs",
            "Define API contracts and integration points",
            "Technical architecture review"
        ]),
        ("Week 3-6: Core Development", [
            "Build inbox UI and thread management",
            "Implement async messaging infrastructure",
            "Integrate with chatbot and ticketing system",
            "Develop AI thread titling feature"
        ]),
        ("Week 7-8: Testing and Refinement", [
            "Internal testing and bug fixes",
            "Integration testing with related systems",
            "Performance optimization"
        ]),
        ("Week 9-10: Beta Launch", [
            "Limited beta release to 5% of users",
            "Monitor metrics and gather feedback",
            "Iterate based on beta learnings"
        ]),
        ("Week 11-12: Full Launch", [
            "Gradual rollout to 100% of users",
            "Marketing and user education",
            "Monitor success metrics"
        ])
    ]
    
    for phase, tasks in timeline:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": phase, "bold": True}
                ]
            }
        })
        for task in tasks:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": task}]
                }
            })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": []}
        })
    
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": "Success Criteria for Launch"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "Before moving to full launch, we must achieve:"}]
        }
    })
    
    success_criteria = [
        "70% of beta users successfully send at least one message",
        "Average response time under 2 seconds for message delivery",
        "Zero critical bugs or data loss incidents",
        "Positive feedback from 80% of beta users",
        "Successful integration with all required systems"
    ]
    
    for criterion in success_criteria:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": criterion}]
            }
        })
    
    # Hypothesis
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": "Hypothesis"}]
        }
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "If we replace email with an in-app support inbox that supports persistent, multi-threaded conversations and surfaces ticket updates directly in the conversation, customers will have better visibility into their issues, leading to:"}]
        }
    })
    
    outcomes = [
        "Fewer repeat contacts (30% reduction)",
        "Lower effort to follow up on issues",
        "Improved customer satisfaction (15% increase in CSAT)",
        "Higher chatbot containment rates (25% increase)",
        "Reduced email support volume (60% reduction)",
        "Better perceived transparency and trust"
    ]
    
    for outcome in outcomes:
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": outcome}]
            }
        })
    
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": "This will be measured through the success metrics defined above, with data collection starting from beta launch."}]
        }
    })
    
    return blocks


async def search_for_my_space(notion_client):
    """Try to find 'My Space' page by searching user's pages."""
    # Notion API doesn't have a direct search, but we can try to get user's pages
    # For now, we'll need the user to provide the page ID
    return None


async def create_notion_page_with_parent(parent_page_id=None):
    """Create the PRD page in Notion under a parent page."""
    context = load_context_from_env()
    
    if not context.notion_api_key:
        print("❌ Notion API key not configured.")
        print("   Please set NOTION_API_KEY in your .env file")
        return None
    
    notion_client = NotionClient(context.notion_api_key)
    
    # Create blocks
    blocks = create_notion_blocks()
    
    print("Creating PRD page in Notion...")
    
    # Create page properties
    properties = {
        "title": {
            "title": [
                {"type": "text", "text": {"content": "PRD: In-App Customer Messaging Inbox"}}
            ]
        }
    }
    
    try:
        if parent_page_id:
            # Create as child of My Space
            page_data = await notion_client.create_page(
                parent_database_id=None,  # Not a database
                properties=properties,
                content_blocks=blocks
            )
            # Actually, create_page expects a database_id, but we need to create a page as child
            # Let's use the Notion API directly for this
            import httpx
            async with httpx.AsyncClient() as client:
                payload = {
                    "parent": {"page_id": parent_page_id},
                    "properties": properties
                }
                
                response = await client.post(
                    f"{notion_client.base_url}/pages",
                    headers=notion_client.headers,
                    json=payload
                )
                response.raise_for_status()
                page_data = response.json()
                page_id = page_data["id"]
                
                # Add content blocks
                if blocks:
                    await notion_client._add_blocks_to_page(page_id, blocks)
                
                print(f"\n✅ PRD page created successfully!")
                print(f"   Page ID: {page_id}")
                print(f"   View at: https://www.notion.so/{page_id.replace('-', '')}")
                return page_data
        else:
            # Try to create at workspace root
            print("⚠️  No parent page ID provided.")
            print("   Creating at workspace root...")
            
            import httpx
            async with httpx.AsyncClient() as client:
                # Get user to find workspace
                payload = {
                    "parent": {"type": "workspace", "workspace": True},
                    "properties": properties
                }
                
                response = await client.post(
                    f"{notion_client.base_url}/pages",
                    headers=notion_client.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    page_data = response.json()
                    page_id = page_data["id"]
                    
                    # Add content blocks
                    if blocks:
                        await notion_client._add_blocks_to_page(page_id, blocks)
                    
                    print(f"\n✅ PRD page created successfully!")
                    print(f"   Page ID: {page_id}")
                    print(f"   View at: https://www.notion.so/{page_id.replace('-', '')}")
                    print(f"\n   You can move this page to 'My Space' manually in Notion.")
                    return page_data
                else:
                    print(f"❌ Could not create at workspace root: {response.status_code}")
                    print(f"   Response: {response.text}")
                    print("\n   Please provide the 'My Space' page ID:")
                    print("   1. Open 'My Space' in Notion")
                    print("   2. Copy the page ID from the URL")
                    print("   3. Run: python3 create_notion_prd.py <PAGE_ID>")
                    return None
                
    except Exception as e:
        print(f"❌ Error creating page: {e}")
        import traceback
        traceback.print_exc()
        return None


async def create_notion_page():
    """Create the PRD page in Notion."""
    return await create_notion_page_with_parent()


async def find_my_space_page(notion_client):
    """Try to find My Space by checking if user has access to search."""
    # Notion API v1 doesn't support search, but we can try to help user find it
    print("\nTo find your 'My Space' page ID:")
    print("1. Open Notion and navigate to 'My Space'")
    print("2. Look at the URL - it will be like: https://www.notion.so/My-Space-abc123def456...")
    print("3. The page ID is the part after 'My-Space-' (remove dashes)")
    print("\nOr you can:")
    print("- Right-click on 'My Space' in the sidebar")
    print("- Select 'Copy link'")
    print("- The page ID is in the URL")
    return None


if __name__ == "__main__":
    import sys
    
    # Check if My Space page ID provided
    my_space_id = None
    if len(sys.argv) > 1:
        my_space_id = sys.argv[1]
        # Remove dashes if user included them
        my_space_id = my_space_id.replace('-', '')
        # Add dashes in the right places (32 char hex string)
        if len(my_space_id) == 32:
            my_space_id = f"{my_space_id[:8]}-{my_space_id[8:12]}-{my_space_id[12:16]}-{my_space_id[16:20]}-{my_space_id[20:]}"
    
    if my_space_id:
        print(f"Creating PRD page in 'My Space' (page ID: {my_space_id})...")
        asyncio.run(create_notion_page_with_parent(my_space_id))
    else:
        print("=" * 80)
        print("Creating PRD: In-App Customer Messaging Inbox in Notion")
        print("=" * 80)
        print("\nTo create the page in 'My Space':")
        print("  1. Get your 'My Space' page ID from the Notion URL")
        print("  2. Run: python3 create_notion_prd.py <MY_SPACE_PAGE_ID>")
        print("\nOr we'll try to create it at the workspace root...")
        print()
        
        # Try to create at workspace root
        result = asyncio.run(create_notion_page())
        
        if not result:
            print("\n" + "=" * 80)
            print("Alternative: Provide My Space Page ID")
            print("=" * 80)
            asyncio.run(find_my_space_page(None))

