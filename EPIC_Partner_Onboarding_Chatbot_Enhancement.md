# Epic: Partner Onboarding Chatbot Enhancement

## Epic Summary

**Epic Title:** Enable Partner AI Chatbot for Pre-Onboarding Partners

**Epic Key:** [To be assigned]

**Initiative:** Partner AI Chatbot Expansion

**Squad:** Partner Care AI

---

## Description

### Overview

Extend the Partner AI Chatbot to handle pre-onboarding partners, enabling them to interact with the AI chatbot instead of being directly routed to human agents. This enhancement will expand the chatbot's knowledge base with content from docs.tamara.co and Partner Onboarding SOPs, implement intelligent partner classification based on Salesforce configuration, and modify handover flows to route onboarding partner escalations to the correct Salesforce queue.

### Background

Currently, the Partner AI Chatbot serves two distinct user personas:
- **Live Partners (Existing Merchants):** Interact with the AI chatbot for self-service support
- **Pre-Onboarding Partners (New Merchants):** Immediately routed to the Partner Onboarding team without chatbot interaction

This approach results in:
- High agent workload for simple, repetitive informational queries
- Long wait times for onboarding partners who have quick questions
- Missed opportunity for automation of common onboarding FAQs
- Inconsistent experience between partner personas

### Goals

1. **Enable Self-Service for Onboarding Partners:** Allow pre-onboarding partners to get answers to common questions without waiting for an agent
2. **Expand Knowledge Base:** Add docs.tamara.co technical documentation and Partner Onboarding SOPs to the bot's knowledge
3. **Intelligent Routing:** Accurately classify partners as onboarding vs. live based on Salesforce configuration
4. **Correct Handover Queues:** Route onboarding partner escalations to the Onboarding team (not Partner Care) on Salesforce

### Success Criteria

| Metric | Target |
|--------|--------|
| Deflection Rate (Onboarding Partners) | ≥ 50% |
| First Response Time | < 5 seconds |
| Onboarding Partner BSAT | ≥ 65% |
| Agent Workload Reduction | -20% |
| Routing Accuracy | ≥ 98% |

---

## Scope

### In-Scope

- ✅ Knowledge base expansion with docs.tamara.co content
- ✅ Knowledge base expansion with Partner Onboarding SOPs
- ✅ Orchestrator modification for partner classification
- ✅ Onboarding-specific intent recognition enhancement
- ✅ Handover routing to Onboarding team on Salesforce
- ✅ Salesforce integration for partner status lookup
- ✅ Session-level partner status caching
- ✅ Onboarding-specific chatbot instructions and behavior

### Out-of-Scope

- ❌ Write operations (application submission, document upload via bot)
- ❌ Real-time application status API integration (Phase 2)
- ❌ Onboarding workflow automation
- ❌ Changes to the live partner chatbot flow
- ❌ New channels (only existing Partner Portal and Support Website)

---

## User Stories

This epic contains the following user stories:

| Story ID | Title | Points | Priority |
|----------|-------|--------|----------|
| US-001 | Ingest docs.tamara.co content into Knowledge Base | 5 | High |
| US-002 | Ingest Partner Onboarding SOPs into Knowledge Base | 5 | High |
| US-003 | Implement Partner Status Detection from Salesforce | 5 | High |
| US-004 | Modify Orchestrator for Onboarding Partner Flow | 8 | High |
| US-005 | Add Onboarding-Specific Intents to NLU | 5 | High |
| US-006 | Implement Knowledge Retrieval Priority for Onboarding | 3 | Medium |
| US-007 | Update Handover Logic for Onboarding Queue Routing | 5 | High |
| US-008 | Create Onboarding-Specific Chatbot Instructions | 3 | Medium |
| US-009 | Implement Partner Status Caching | 3 | Medium |
| US-010 | Add Onboarding Partner Analytics & Reporting | 3 | Low |
| US-011 | UAT and Pilot Rollout for Onboarding Partners | 5 | High |

**Total Story Points:** 50

---

## Technical Approach

### Components Affected

1. **Bot Knowledge MongoDB**
   - Add new collection/documents for docs.tamara.co content
   - Add new collection/documents for Partner Onboarding SOPs
   - Update schema to include `partner_stage` field for filtering

2. **Orchestrator Service**
   - Add partner status detection at session initialization
   - Implement classification logic (onboarding vs. live)
   - Load onboarding-specific instructions when applicable
   - Modify handover queue selection logic

3. **NLU/Intent Classification**
   - Add new onboarding-specific intents
   - Enhance existing intents with onboarding context

4. **Knowledge Retrieval**
   - Implement source priority logic for onboarding partners
   - Add docs.tamara.co as searchable knowledge source

5. **Salesforce Integration**
   - Add API call to lookup partner account status
   - Update handover payload with correct queue routing

### Architecture Changes

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Chat Session Start                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 Partner Status Lookup (Salesforce)                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │ Account_Status  │    │ Onboarding_Stage│    │  Go_Live_Date   │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Partner Classification                           │
│         ┌────────────────────┬────────────────────┐                │
│         │   IF Onboarding    │     IF Live        │                │
│         └────────────────────┴────────────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
                     │                        │
                     ▼                        ▼
┌────────────────────────────┐  ┌────────────────────────────────────┐
│  Onboarding Chatbot Flow   │  │     Standard Chatbot Flow          │
│  ├─ Onboarding Instructions│  │     (No changes)                   │
│  ├─ Priority: docs.tamara  │  │                                    │
│  ├─ Priority: SOPs         │  │                                    │
│  └─ Handover → Onboarding  │  │                                    │
└────────────────────────────┘  └────────────────────────────────────┘
```

---

## Dependencies

| Dependency | Owner | Required By |
|------------|-------|-------------|
| Salesforce Account fields (Account_Status__c, Onboarding_Stage__c) | Salesforce Admin | Before development |
| Access to docs.tamara.co for content scraping | DevEx Team | Before US-001 |
| Partner Onboarding SOPs documentation | Partner Onboarding Team | Before US-002 |
| Orchestrator deployment access | AI Team | Before US-004 |
| Salesforce Onboarding queue creation | Salesforce Admin | Before US-007 |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Incorrect partner classification leads to wrong routing | High | Comprehensive testing, fallback to safer flow |
| Knowledge gaps in docs.tamara.co | Medium | Content audit before launch, feedback loop |
| Outdated SOP content | Medium | Regular review process, version control |
| Salesforce API latency | Low | Caching, async lookup, timeout fallback |

---

## Acceptance Criteria

- [ ] Pre-onboarding partners interact with the chatbot (not direct handoff)
- [ ] docs.tamara.co content is searchable and retrievable by the bot
- [ ] Partner Onboarding SOPs are ingested into the knowledge base
- [ ] Partner classification (onboarding vs. live) is accurate ≥ 98%
- [ ] Onboarding partner handovers route to Onboarding team on Salesforce
- [ ] Deflection rate for onboarding partners ≥ 50% within 30 days
- [ ] BSAT score for onboarding partners ≥ 65%

---

## Timeline

| Phase | Duration | Dates |
|-------|----------|-------|
| Knowledge Base Enhancement | 2 weeks | Week 1-2 |
| Orchestrator & NLU Updates | 2 weeks | Week 3-4 |
| Handover Integration | 1 week | Week 5 |
| Testing & Pilot | 2 weeks | Week 6-7 |
| GA Rollout | 1 week | Week 8 |

**Total Duration:** 8 weeks

---

## Related Links

- [PRD: Partner Onboarding Chatbot Enhancement](link)
- [Partner AI Chatbot Original PRD](link)
- [Salesforce Integration Documentation](link)
- [docs.tamara.co](https://docs.tamara.co)

---

## Labels

`partner-care` `ai-chatbot` `onboarding` `knowledge-base` `salesforce`

---

*Created: February 26, 2026*




