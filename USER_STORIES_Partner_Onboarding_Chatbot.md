# User Stories: Partner Onboarding Chatbot Enhancement

**Epic:** Enable Partner AI Chatbot for Pre-Onboarding Partners

---

## Table of Contents

1. [US-001: Ingest docs.tamara.co Content](#us-001-ingest-docstamaraco-content-into-knowledge-base)
2. [US-002: Ingest Partner Onboarding SOPs](#us-002-ingest-partner-onboarding-sops-into-knowledge-base)
3. [US-003: Partner Status Detection from Salesforce](#us-003-implement-partner-status-detection-from-salesforce)
4. [US-004: Orchestrator Modification for Onboarding Flow](#us-004-modify-orchestrator-for-onboarding-partner-flow)
5. [US-005: Onboarding-Specific Intents](#us-005-add-onboarding-specific-intents-to-nlu)
6. [US-006: Knowledge Retrieval Priority](#us-006-implement-knowledge-retrieval-priority-for-onboarding)
7. [US-007: Handover Queue Routing](#us-007-update-handover-logic-for-onboarding-queue-routing)
8. [US-008: Onboarding Chatbot Instructions](#us-008-create-onboarding-specific-chatbot-instructions)
9. [US-009: Partner Status Caching](#us-009-implement-partner-status-caching)
10. [US-010: Analytics & Reporting](#us-010-add-onboarding-partner-analytics--reporting)
11. [US-011: UAT and Pilot Rollout](#us-011-uat-and-pilot-rollout-for-onboarding-partners)

---

## US-001: Ingest docs.tamara.co Content into Knowledge Base

### Story

**As a** Pre-onboarding Partner  
**I want** the chatbot to have access to technical documentation from docs.tamara.co  
**So that** I can get answers to my integration and API-related questions without waiting for an agent

### Description

Implement a content ingestion pipeline to scrape, parse, and store content from docs.tamara.co into the MongoDB knowledge base. This includes API documentation, integration guides, webhook configuration, plugin setup guides, and sandbox testing documentation.

### Priority

🔴 **High**

### Story Points

**5**

### Acceptance Criteria

- [ ] Content scraper successfully extracts content from all sections of docs.tamara.co
- [ ] Extracted content is properly chunked (max 1000 tokens per chunk)
- [ ] Vector embeddings are generated for all content chunks
- [ ] Content is stored in MongoDB with proper schema (source, category, tags, language, etc.)
- [ ] At least 95% of docs.tamara.co pages are indexed
- [ ] Code snippets in documentation are preserved and formatted correctly
- [ ] Both English and Arabic content (where available) is indexed
- [ ] Deduplication logic prevents duplicate content

### Technical Details

**Source URLs to scrape:**
- `docs.tamara.co/getting-started/*`
- `docs.tamara.co/api/*`
- `docs.tamara.co/integrations/*`
- `docs.tamara.co/webhooks/*`
- `docs.tamara.co/plugins/*`
- `docs.tamara.co/testing/*`
- `docs.tamara.co/faq/*`

**MongoDB Schema:**
```javascript
{
  "_id": ObjectId,
  "source": "docs.tamara.co",
  "category": String, // "api", "integration", "webhook", "plugin", "testing", "faq"
  "title": String,
  "content": String,
  "url": String,
  "tags": [String],
  "language": "en" | "ar",
  "last_updated": Date,
  "embedding": [Float],
  "metadata": {
    "applicable_platforms": [String],
    "complexity": String
  }
}
```

### Definition of Done

- [ ] Code reviewed and approved
- [ ] Unit tests written and passing
- [ ] Integration test with retrieval confirmed
- [ ] Documentation updated
- [ ] Content coverage verified (≥ 95%)

---

## US-002: Ingest Partner Onboarding SOPs into Knowledge Base

### Story

**As a** Pre-onboarding Partner  
**I want** the chatbot to have access to Partner Onboarding SOPs  
**So that** I can get accurate answers about the onboarding process, document requirements, and timelines

### Description

Create and ingest Partner Onboarding Standard Operating Procedures (SOPs) into the MongoDB knowledge base. This includes application process documentation, document requirements by country and entity type, common rejection reasons, and onboarding FAQs.

### Priority

🔴 **High**

### Story Points

**5**

### Acceptance Criteria

- [ ] All Partner Onboarding SOPs are documented in structured format
- [ ] SOPs cover all onboarding stages: Application, Documents, Integration, Approval
- [ ] Country-specific requirements (KSA, UAE, Kuwait, Egypt, Bahrain) are documented
- [ ] Entity type requirements (Sole Proprietor, LLC, Corporation) are documented
- [ ] Common rejection reasons and resolution steps are included
- [ ] Content is chunked and embedded for semantic search
- [ ] SOPs are tagged with applicable onboarding stages for filtering
- [ ] Both English and Arabic versions are available

### Content Categories

| Category | Description |
|----------|-------------|
| Application Process | Steps, timeline, requirements overview |
| Document Requirements | CR, VAT, bank details, identity documents |
| Country-Specific | KSA, UAE, Kuwait, Egypt, Bahrain requirements |
| Entity Types | Sole proprietor, LLC, corporation differences |
| Rejection Reasons | Common reasons and how to resolve |
| Timeline FAQs | Expected durations for each stage |

### SOP Document Format

```markdown
# SOP: [Topic Name]

## Overview
[Brief description]

## Applicable To
- Countries: [List]
- Entity Types: [List]
- Onboarding Stage: [Stage]

## Requirements
[Detailed requirements]

## Common Questions
Q: [Question]
A: [Answer]

## Escalation Triggers
[When to escalate]
```

### Definition of Done

- [ ] All SOP content documented
- [ ] Content ingested into MongoDB
- [ ] Embeddings generated
- [ ] Retrieval tested with sample queries
- [ ] Partner Onboarding team sign-off on content accuracy

---

## US-003: Implement Partner Status Detection from Salesforce

### Story

**As a** Chatbot System  
**I want** to detect whether a partner is in onboarding or live status  
**So that** I can route them to the appropriate chatbot flow

### Description

Implement Salesforce API integration to lookup partner account status at the beginning of each chat session. Use the Salesforce Account object fields to determine if the partner is onboarding or live.

### Priority

🔴 **High**

### Story Points

**5**

### Acceptance Criteria

- [ ] API call to Salesforce retrieves Account_Status__c field
- [ ] API call retrieves Onboarding_Stage__c field
- [ ] API call retrieves Go_Live_Date__c field
- [ ] API call retrieves Merchant_ID__c field
- [ ] Classification logic correctly identifies "onboarding" vs "live" partners
- [ ] Fallback behavior handles Salesforce API failures gracefully
- [ ] Response time for status lookup is < 500ms (P95)
- [ ] Partners not found in Salesforce are handled appropriately

### Classification Logic

```python
def classify_partner(sf_account):
    # Primary: Account Status
    if sf_account.Account_Status__c == "Onboarding":
        return "onboarding"
    
    # Secondary: Onboarding Stage
    if sf_account.Onboarding_Stage__c != "Live":
        return "onboarding"
    
    # Tertiary: Go Live Date
    if sf_account.Go_Live_Date__c is None:
        return "onboarding"
    
    return "live"
```

### Salesforce Fields

| Field | Object | Description |
|-------|--------|-------------|
| `Account_Status__c` | Account | Onboarding, Live, Churned, Suspended |
| `Onboarding_Stage__c` | Account | Application Submitted, Documents Pending, Integration Setup, Approval Pending, Live |
| `Go_Live_Date__c` | Account | Date or null |
| `Merchant_ID__c` | Account | String or null |

### Fallback Behavior

| Scenario | Action |
|----------|--------|
| Salesforce API timeout | Default to "live" flow |
| Partner not found | Treat as non-authenticated |
| Ambiguous status | Default to "onboarding" flow |

### Definition of Done

- [ ] Salesforce API integration implemented
- [ ] Classification logic tested with all scenarios
- [ ] Fallback behavior tested
- [ ] Performance verified (< 500ms P95)
- [ ] Error handling and logging implemented

---

## US-004: Modify Orchestrator for Onboarding Partner Flow

### Story

**As a** Pre-onboarding Partner  
**I want** the chatbot to recognize that I'm in the onboarding process  
**So that** I receive relevant responses and guidance specific to my stage

### Description

Modify the orchestrator to handle onboarding partners differently from live partners. When a partner is classified as "onboarding," the orchestrator should load onboarding-specific instructions, prioritize onboarding knowledge sources, and adjust handover behavior.

### Priority

🔴 **High**

### Story Points

**8**

### Acceptance Criteria

- [ ] Orchestrator calls partner status detection at session initialization
- [ ] Partner classification result is stored in session context
- [ ] Onboarding partners receive onboarding-specific greeting
- [ ] Knowledge retrieval prioritizes docs.tamara.co and SOPs for onboarding partners
- [ ] Handover triggers are adjusted for onboarding context
- [ ] Session context includes `partner_type: "onboarding"` or `"live"`
- [ ] Onboarding stage is available in context for personalization
- [ ] Live partner flow remains unchanged

### Session Context Schema

```javascript
{
  "session_id": String,
  "partner_id": String,
  "partner_type": "onboarding" | "live",
  "onboarding_stage": String, // Only for onboarding partners
  "account_status": String,
  "knowledge_priority": ["docs.tamara.co", "sops", "support.tamara.co"],
  "handover_queue": "Partner Onboarding Support" | "Partner Care"
}
```

### Flow Changes

| Step | Current Behavior | New Behavior |
|------|------------------|--------------|
| Session Init | Load default instructions | Call partner status API, load appropriate instructions |
| Greeting | Generic greeting | Personalized greeting based on partner type |
| Knowledge Search | Search all sources equally | Prioritize sources based on partner type |
| Handover | Route to Partner Care | Route based on partner type |

### Definition of Done

- [ ] Orchestrator modified to call partner status detection
- [ ] Session context updated with partner classification
- [ ] Onboarding flow routing tested
- [ ] Live partner flow unaffected (regression tested)
- [ ] Performance impact validated

---

## US-005: Add Onboarding-Specific Intents to NLU

### Story

**As a** Pre-onboarding Partner  
**I want** the chatbot to understand my onboarding-related questions  
**So that** I can get accurate and relevant answers

### Description

Add new intents to the NLU model that are specific to the onboarding journey. These intents should cover application status, document requirements, timeline questions, integration setup, and rejection-related queries.

### Priority

🔴 **High**

### Story Points

**5**

### Acceptance Criteria

- [ ] All new intents are added to the intent classifier
- [ ] Training data includes at least 50 examples per intent (EN and AR)
- [ ] Intent recognition accuracy ≥ 90% on test set
- [ ] Intents properly map to knowledge retrieval categories
- [ ] No regression on existing partner intent recognition

### New Intents

| Intent | Sample Queries (EN) | Sample Queries (AR) |
|--------|---------------------|---------------------|
| `onboarding.application_status` | "What's the status of my application?" | "وش وضع طلب الانضمام؟" |
| `onboarding.document_requirements` | "What documents do I need?" | "وش المستندات المطلوبة؟" |
| `onboarding.timeline` | "How long does onboarding take?" | "كم تاخذ عملية التسجيل؟" |
| `onboarding.rejection_reason` | "Why was my application rejected?" | "ليش انرفض طلبي؟" |
| `onboarding.resubmission` | "How do I resubmit my application?" | "كيف أقدم طلب جديد؟" |
| `integration.api_setup` | "How do I set up the API?" | "كيف أربط الـ API؟" |
| `integration.sandbox` | "How do I test in sandbox?" | "كيف أجرب في Sandbox؟" |
| `integration.go_live` | "How do I go live?" | "كيف أحوّل للإنتاج؟" |
| `integration.plugin_setup` | "How do I install the Shopify plugin?" | "كيف أركّب إضافة شوبيفاي؟" |
| `integration.webhook` | "How do I configure webhooks?" | "كيف أضبط الـ Webhooks؟" |

### Definition of Done

- [ ] Intents added to model
- [ ] Training data collected and validated
- [ ] Model retrained and evaluated
- [ ] Accuracy metrics meet threshold
- [ ] Deployed to staging for testing

---

## US-006: Implement Knowledge Retrieval Priority for Onboarding

### Story

**As a** Chatbot System  
**I want** to prioritize knowledge sources based on partner type and query category  
**So that** onboarding partners receive the most relevant answers from appropriate sources

### Description

Implement knowledge retrieval logic that prioritizes different knowledge sources based on whether the partner is onboarding or live, and based on the detected intent/query category.

### Priority

🟡 **Medium**

### Story Points

**3**

### Acceptance Criteria

- [ ] Onboarding partners' queries search docs.tamara.co first for technical questions
- [ ] Onboarding partners' queries search SOPs first for process questions
- [ ] Query category detection determines source priority
- [ ] Retrieval results are re-ranked based on source priority
- [ ] Fallback to all sources if priority source has no results
- [ ] Live partners maintain current retrieval behavior

### Priority Matrix

| Partner Type | Query Category | Priority 1 | Priority 2 | Priority 3 |
|--------------|----------------|------------|------------|------------|
| Onboarding | Technical/API | docs.tamara.co | SOPs | support.tamara.co |
| Onboarding | Process/Requirements | SOPs | support.tamara.co | docs.tamara.co |
| Onboarding | General FAQ | support.tamara.co | SOPs | docs.tamara.co |
| Live | Any | support.tamara.co | (existing behavior) | |

### Implementation

```python
def get_knowledge_priority(partner_type, query_category):
    if partner_type == "onboarding":
        if query_category in ["api", "integration", "webhook", "plugin"]:
            return ["docs.tamara.co", "partner_onboarding_sops", "support.tamara.co"]
        elif query_category in ["application", "documents", "timeline"]:
            return ["partner_onboarding_sops", "support.tamara.co", "docs.tamara.co"]
    return ["support.tamara.co"]  # Default for live partners
```

### Definition of Done

- [ ] Priority logic implemented
- [ ] Query category detection working
- [ ] Retrieval re-ranking implemented
- [ ] Tested with sample queries
- [ ] No regression on live partner queries

---

## US-007: Update Handover Logic for Onboarding Queue Routing

### Story

**As a** Pre-onboarding Partner  
**I want** to be transferred to the Onboarding Support team when I need human assistance  
**So that** I speak with agents who specialize in onboarding issues

### Description

Modify the handover logic to route onboarding partners to the Partner Onboarding Support queue on Salesforce instead of the Partner Care queue. Ensure the handover payload includes all necessary context for the receiving agent.

### Priority

🔴 **High**

### Story Points

**5**

### Acceptance Criteria

- [ ] Onboarding partners are routed to "Partner Onboarding Support" queue
- [ ] Live partners continue to be routed to "Partner Care" queue
- [ ] Handover payload includes partner_type and onboarding_stage
- [ ] Conversation summary and intent are passed to agents
- [ ] Salesforce case is created with correct queue assignment
- [ ] Handover success rate ≥ 99%
- [ ] Correct queue routing 100% of the time

### Queue Mapping

| Partner Type | Salesforce Queue | Queue ID |
|--------------|------------------|----------|
| Onboarding | Partner Onboarding Support | `[QUEUE_ID_ONBOARDING]` |
| Live | Partner Care | `[QUEUE_ID_PARTNER_CARE]` |

### Handover Payload

```json
{
  "handover_type": "agent_transfer",
  "partner_info": {
    "partner_id": "string",
    "account_status": "onboarding",
    "onboarding_stage": "documents_pending",
    "company_name": "string",
    "country": "KSA"
  },
  "conversation_summary": {
    "intent": "onboarding.document_requirements",
    "query_summary": "Partner asking about required documents for KSA LLC",
    "bot_attempts": 2,
    "handover_reason": "complex_query_unresolved"
  },
  "routing": {
    "queue": "Partner Onboarding Support",
    "queue_id": "[QUEUE_ID]",
    "priority": "normal"
  },
  "context": {
    "language": "en",
    "sentiment": "neutral",
    "channel": "partner_portal",
    "chat_history": [...]
  }
}
```

### Handover Triggers for Onboarding Partners

| Trigger | Description |
|---------|-------------|
| Application rejection dispute | Partner disputes rejection decision |
| Sensitive document issues | ID verification, ownership documents |
| Contract/legal queries | Contract terms, legal obligations |
| Complex integration (2+ attempts) | Technical issue not resolved |
| Country activation request | New country onboarding |
| Explicit agent request | Partner asks for human |
| Negative sentiment | Frustration detected |

### Definition of Done

- [ ] Queue routing logic implemented
- [ ] Handover payload updated
- [ ] Salesforce queue IDs configured
- [ ] End-to-end handover tested
- [ ] 100% routing accuracy verified

---

## US-008: Create Onboarding-Specific Chatbot Instructions

### Story

**As a** Pre-onboarding Partner  
**I want** the chatbot to communicate in a way that acknowledges my onboarding journey  
**So that** I feel understood and receive relevant guidance

### Description

Create onboarding-specific system instructions for the chatbot that define the tone, behavior, and response patterns when interacting with pre-onboarding partners.

### Priority

🟡 **Medium**

### Story Points

**3**

### Acceptance Criteria

- [ ] Onboarding-specific instructions are documented
- [ ] Instructions include appropriate greeting templates
- [ ] Instructions define knowledge priority and retrieval behavior
- [ ] Instructions define handover triggers and messages
- [ ] Instructions are loaded when partner is classified as onboarding
- [ ] Tone is supportive and guidance-oriented
- [ ] Both English and Arabic instructions are available

### Instruction Template

```yaml
partner_type: onboarding
persona: |
  You are Tamara's Partner Onboarding Assistant. Your role is to help 
  merchants who are in the process of joining Tamara. Be supportive, 
  clear, and proactive in guiding them through the onboarding journey.

behavior:
  greeting: |
    Welcome to Tamara! I see you're in the process of becoming a 
    Tamara partner. I'm here to help you with any questions about 
    your application, required documents, or integration setup.
  
  tone: supportive, clear, proactive, patient
  
  priorities:
    - Help partners understand next steps
    - Provide clear documentation guidance
    - Offer technical integration support
    - Set realistic timeline expectations
  
  knowledge_sources:
    primary: ["docs.tamara.co", "partner_onboarding_sops"]
    secondary: ["support.tamara.co"]

handover:
  triggers:
    - rejection_dispute
    - sensitive_documents
    - contract_legal
    - complex_integration_unresolved
    - explicit_agent_request
    - negative_sentiment
  
  queue: "Partner Onboarding Support"
  
  message_en: |
    I'll connect you with our Partner Onboarding team who can help 
    you further. Please hold while I transfer you – they'll have 
    all the context from our conversation.
  
  message_ar: |
    بوصلك بفريق دعم التسجيل اللي يقدر يساعدك أكثر في هالموضوع.
    انتظر شوي وأنا أحولك – راح يكون عندهم كل تفاصيل محادثتنا.
```

### Definition of Done

- [ ] Instructions documented
- [ ] English and Arabic versions complete
- [ ] Instructions integrated with orchestrator
- [ ] Response quality validated
- [ ] Partner Onboarding team review and approval

---

## US-009: Implement Partner Status Caching

### Story

**As a** Chatbot System  
**I want** to cache partner status information  
**So that** I don't need to call Salesforce for every message in a session

### Description

Implement caching layer for partner status information to reduce Salesforce API calls and improve response times. Cache should be invalidated appropriately when status might have changed.

### Priority

🟡 **Medium**

### Story Points

**3**

### Acceptance Criteria

- [ ] Partner status is cached after initial lookup
- [ ] Cache TTL is configurable (default: 24 hours for status, 1 hour for stage)
- [ ] Cache is stored in session context for current session
- [ ] Cache is invalidated on handover (status might change)
- [ ] Cache key includes partner_id
- [ ] Cache hit rate ≥ 90% within sessions
- [ ] Fallback to Salesforce lookup if cache miss

### Caching Strategy

| Field | TTL | Invalidation Trigger |
|-------|-----|----------------------|
| `partner_status` | 24 hours | Session end, explicit refresh |
| `onboarding_stage` | 1 hour | Handover, session end |
| `merchant_id` | 24 hours | Session end |

### Implementation

```python
class PartnerStatusCache:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_status(self, partner_id):
        cache_key = f"partner_status:{partner_id}"
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
    
    def set_status(self, partner_id, status_data, ttl=86400):
        cache_key = f"partner_status:{partner_id}"
        self.redis.setex(cache_key, ttl, json.dumps(status_data))
    
    def invalidate(self, partner_id):
        cache_key = f"partner_status:{partner_id}"
        self.redis.delete(cache_key)
```

### Definition of Done

- [ ] Cache implementation complete
- [ ] TTL configuration working
- [ ] Invalidation logic tested
- [ ] Performance improvement measured
- [ ] No stale data issues

---

## US-010: Add Onboarding Partner Analytics & Reporting

### Story

**As a** Bot Admin  
**I want** to track analytics specific to onboarding partner interactions  
**So that** I can measure the success of the onboarding chatbot experience

### Description

Add analytics tracking and reporting for onboarding partner chatbot interactions. This includes deflection rate, intent distribution, handover reasons, and satisfaction scores.

### Priority

🟢 **Low**

### Story Points

**3**

### Acceptance Criteria

- [ ] Onboarding partner sessions are tagged in analytics
- [ ] Deflection rate is trackable for onboarding partners
- [ ] Intent distribution report shows onboarding-specific intents
- [ ] Handover reasons are captured and reportable
- [ ] BSAT scores are segmented by partner type
- [ ] Dashboard includes onboarding partner metrics
- [ ] Data is exportable for analysis

### Metrics to Track

| Metric | Description | Dashboard |
|--------|-------------|-----------|
| Onboarding Deflection Rate | % of queries resolved without handoff | Main |
| Onboarding BSAT | Bot satisfaction for onboarding partners | Main |
| Top Onboarding Intents | Most common onboarding queries | Intent |
| Handover Reasons | Why onboarding partners were transferred | Handover |
| Resolution by Knowledge Source | Which source answered the query | Knowledge |
| Response Time | Average first response time | Performance |

### Events to Log

```javascript
// Session start event
{
  "event": "session_started",
  "partner_type": "onboarding",
  "onboarding_stage": "documents_pending",
  "channel": "partner_portal"
}

// Query event
{
  "event": "query_received",
  "partner_type": "onboarding",
  "intent": "onboarding.document_requirements",
  "knowledge_source": "partner_onboarding_sops"
}

// Handover event
{
  "event": "handover_initiated",
  "partner_type": "onboarding",
  "reason": "complex_query_unresolved",
  "queue": "Partner Onboarding Support"
}

// Survey event
{
  "event": "pbsat_submitted",
  "partner_type": "onboarding",
  "score": 4,
  "resolved": true
}
```

### Definition of Done

- [ ] Analytics events defined and implemented
- [ ] Dashboard updated with onboarding metrics
- [ ] Reports accessible to stakeholders
- [ ] Data validation complete

---

## US-011: UAT and Pilot Rollout for Onboarding Partners

### Story

**As a** Product Owner  
**I want** to conduct UAT and pilot rollout of the onboarding chatbot  
**So that** we can validate the experience before full rollout

### Description

Conduct User Acceptance Testing (UAT) with internal stakeholders and Partner Onboarding team, followed by a pilot rollout to a subset of onboarding partners.

### Priority

🔴 **High**

### Story Points

**5**

### Acceptance Criteria

- [ ] UAT test cases cover all onboarding scenarios
- [ ] Partner Onboarding team validates response accuracy
- [ ] Integration testing with Salesforce handover complete
- [ ] Pilot rollout to 10% of onboarding partners
- [ ] Feedback collection mechanism in place
- [ ] Success criteria defined and measured
- [ ] Go/No-Go decision criteria established
- [ ] Rollback plan documented

### UAT Test Scenarios

| # | Scenario | Expected Outcome |
|---|----------|------------------|
| 1 | Onboarding partner asks about document requirements | Relevant SOP content retrieved |
| 2 | Onboarding partner asks about API setup | docs.tamara.co content retrieved |
| 3 | Onboarding partner asks why application rejected | Handover triggered to Onboarding team |
| 4 | Onboarding partner requests agent | Handover to Onboarding Support queue |
| 5 | Live partner asks settlement question | Normal Partner Care flow (no change) |
| 6 | Partner classification is accurate | Correct flow based on Salesforce data |
| 7 | Handover includes correct queue and context | Salesforce case created correctly |

### Pilot Rollout Plan

| Stage | % of Users | Duration | Success Criteria |
|-------|------------|----------|------------------|
| UAT | Internal | 1 week | All test cases pass |
| Pilot | 10% | 2 weeks | Deflection ≥ 40%, BSAT ≥ 60%, No critical bugs |
| Beta | 30% | 1 week | Deflection ≥ 45%, BSAT ≥ 62% |
| GA | 100% | Ongoing | Deflection ≥ 50%, BSAT ≥ 65% |

### Go/No-Go Criteria

**Go:**
- Zero critical bugs
- Deflection rate ≥ 40% in pilot
- BSAT ≥ 60% in pilot
- Handover routing 100% accurate
- No negative feedback patterns

**No-Go:**
- Critical bugs identified
- Deflection rate < 30%
- BSAT < 50%
- Handover routing errors
- Significant negative feedback

### Definition of Done

- [ ] UAT completed with all scenarios passing
- [ ] Partner Onboarding team sign-off
- [ ] Pilot rollout complete
- [ ] Success metrics met
- [ ] GA rollout approved

---

## Summary

| Story | Points | Priority | Status |
|-------|--------|----------|--------|
| US-001: Ingest docs.tamara.co | 5 | High | To Do |
| US-002: Ingest Partner Onboarding SOPs | 5 | High | To Do |
| US-003: Partner Status Detection | 5 | High | To Do |
| US-004: Orchestrator Modification | 8 | High | To Do |
| US-005: Onboarding Intents | 5 | High | To Do |
| US-006: Knowledge Retrieval Priority | 3 | Medium | To Do |
| US-007: Handover Queue Routing | 5 | High | To Do |
| US-008: Onboarding Instructions | 3 | Medium | To Do |
| US-009: Partner Status Caching | 3 | Medium | To Do |
| US-010: Analytics & Reporting | 3 | Low | To Do |
| US-011: UAT and Pilot Rollout | 5 | High | To Do |

**Total Story Points:** 50

---

## Sprint Planning Recommendation

### Sprint 1 (Weeks 1-2): Knowledge Foundation
- US-001: Ingest docs.tamara.co content (5 pts)
- US-002: Ingest Partner Onboarding SOPs (5 pts)

**Sprint Total:** 10 pts

### Sprint 2 (Weeks 3-4): Core Logic
- US-003: Partner Status Detection (5 pts)
- US-004: Orchestrator Modification (8 pts)
- US-005: Onboarding Intents (5 pts)

**Sprint Total:** 18 pts

### Sprint 3 (Weeks 5-6): Integration & Polish
- US-006: Knowledge Retrieval Priority (3 pts)
- US-007: Handover Queue Routing (5 pts)
- US-008: Onboarding Instructions (3 pts)
- US-009: Partner Status Caching (3 pts)

**Sprint Total:** 14 pts

### Sprint 4 (Weeks 7-8): Launch
- US-010: Analytics & Reporting (3 pts)
- US-011: UAT and Pilot Rollout (5 pts)

**Sprint Total:** 8 pts

---

*Created: February 26, 2026*




