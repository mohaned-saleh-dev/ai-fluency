# Epic: In-App Chat Survey Integration

## Overview

Build in-app survey functionality that automatically triggers after chat interactions (both chatbot and agent-assisted) to collect customer feedback (CSAT, ASAT, and Issue Resolution) directly within the Tamara mobile app. This epic focuses on the frontend implementation of the survey UI/UX, survey triggering logic, and integration with the existing In-App Survey SDK (CSSV-2032, CSSV-2033) and UFME infrastructure (CSSV-1847).

This epic enables real-time feedback collection immediately after chat interactions, replacing the need for separate email or SMS surveys and providing instant visibility into customer satisfaction and issue resolution rates.

**Key Context:**
- Builds on In-App Survey SDK foundation (Flutter SDK, Backend API)
- Integrates with UFME centralized survey data infrastructure
- Aligns with Customer Self-Serve squad Q1 2026 priorities
- Supports unified feedback management across all channels

---

## Problem Statement

Currently, post-chat surveys are either:
- Not collected at all (missed feedback opportunity)
- Collected via email/SMS (delayed, low response rates, channel fragmentation)
- Collected in separate systems (no unified view with other feedback)

This creates:
- **Low survey response rates** - Email/SMS surveys have <30% response rate
- **Delayed feedback** - Customers receive surveys hours/days after interaction
- **Fragmented data** - Chat surveys stored separately from in-app surveys
- **Poor attribution** - Cannot easily link survey to specific chat interaction
- **Missed opportunities** - No real-time feedback for immediate issue resolution

---

## Solution

Implement an in-app survey experience that:
1. **Automatically triggers** after chat interactions end (chatbot or agent-assisted)
2. **Displays as bottom sheet** overlay with non-intrusive UX
3. **Collects CSAT/ASAT + Issue Resolution** in a single, streamlined flow
4. **Submits in real-time** via In-App Survey SDK to UFME infrastructure
5. **Links to chat interaction** via interaction_id for proper attribution

**User Experience Flow:**
1. Customer completes chat interaction (chatbot resolves OR agent ends session)
2. Survey bottom sheet slides up from bottom of screen
3. Customer sees: "Was your issue resolved?" (Yes/No buttons)
4. Based on response, customer sees: "How was your experience?" (Bad/Average/Great)
5. Customer taps "Send feedback" button
6. Survey submits via SDK → UFME → Central Survey Data Store
7. Confirmation appears: "Feedback submitted" with checkmark
8. Survey dismisses, customer returns to app

---

## Scope

### In-Scope

**Frontend Implementation:**
- Survey bottom sheet UI component (Flutter)
- Survey trigger logic (detect chat end events)
- Survey state management (in_progress, completed, skipped, expired)
- Integration with In-App Survey SDK (CSSV-2032)
- Survey question rendering (Issue Resolution + CSAT/ASAT)
- Response collection and validation
- Error handling and retry logic
- AR/EN localization support
- Accessibility compliance (WCAG 2.1 AA)

**Integration Points:**
- Chat Service integration (detect chat end events)
- In-App Survey SDK API (POST survey responses)
- UFME infrastructure (survey data normalization)
- Interaction linking (chat interaction_id → survey)

**Survey Logic:**
- Trigger after chatbot interactions (when chatbot resolves or escalates)
- Trigger after agent-assisted chat (when agent ends session)
- Suppression rules (no duplicate surveys within 24h for same interaction)
- TTL handling (survey expires after 1 hour if not completed)
- Skip handling (customer dismisses survey)

**Data Flow:**
- Survey submission → In-App Survey SDK → Survey API → UFME Central Store
- Real-time data availability for dashboards
- Proper attribution to chat interaction

### Out-of-Scope

- Survey question configuration UI (handled by backend/admin)
- Multi-question surveys (Phase 2)
- Survey retry logic (handled by UFME Retry Engine - CSSV-2091)
- Survey analytics/dashboards (handled by UFME Dashboards - CSSV-2096)
- Email/SMS survey fallback (handled by UFME Retry Engine)
- Survey A/B testing infrastructure (separate epic)
- Survey personalization/customization (Phase 2)

---

## Key Deliverables

1. **Survey Bottom Sheet Component**
   - Flutter widget with slide-up animation
   - Responsive design (iOS, Android)
   - Dismissible with swipe-down or X button
   - Non-blocking (customer can continue using app)

2. **Survey Trigger Service**
   - Listen for chat end events
   - Check suppression rules (24h window, interaction_id)
   - Determine survey type (CSAT for chatbot, ASAT for agent)
   - Initialize survey with interaction context

3. **Survey Question Flow**
   - Issue Resolution question (Yes/No)
   - CSAT/ASAT question (Bad/Average/Great) - conditional on resolution
   - Visual feedback for selections
   - "Send feedback" button (enabled after both questions answered)

4. **SDK Integration**
   - Call In-App Survey SDK submit method
   - Pass survey data (survey_type, response_value, interaction_id, customer_id)
   - Handle submission success/failure
   - Show confirmation UI

5. **Error Handling**
   - Network failure retry logic
   - Offline queue for survey responses
   - Error state UI (retry button)
   - Graceful degradation

6. **Localization**
   - AR/EN text support
   - RTL layout for Arabic
   - Locale-aware date/time formatting

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Survey Response Rate** | ≥ 50% | % of chat interactions with completed survey |
| **Survey Submission Latency** | < 500ms p99 | Time from "Send feedback" to API response |
| **Survey Display Rate** | ≥ 95% | % of eligible chats where survey is shown |
| **Survey Completion Rate** | ≥ 60% | % of displayed surveys that are completed (not skipped) |
| **Data Attribution Accuracy** | ≥ 99.9% | % of surveys correctly linked to chat interaction_id |
| **Zero Data Loss** | 100% | All completed surveys successfully submitted to UFME |

---

## Technical Approach

**Architecture:**
- Flutter widget for survey UI (reusable component)
- Event listener service for chat end detection
- Survey state machine (in_progress → completed/skipped/expired)
- Integration with In-App Survey SDK (CSSV-2032)
- API calls to Survey API endpoint (from CSSV-2033)

**Data Model:**
```dart
SurveyData {
  survey_id: UUID
  customer_id: String
  interaction_id: UUID (from chat)
  interaction_channel: "chat"
  interaction_type: "automated" | "live"
  survey_channel: "in-app"
  survey_event: "chat_ended"
  survey_type: "CSAT" | "ASAT"
  question_id: "issue_resolution" | "satisfaction"
  response_value: "Yes" | "No" | "Bad" | "Average" | "Great"
  submitted_at: Timestamp
  status: "in_progress" | "completed" | "skipped" | "expired"
}
```

**Integration Points:**
1. **Chat Service** → Listen for `chat_ended` events
2. **In-App Survey SDK** → Call `submitSurvey(surveyData)`
3. **UFME Infrastructure** → Survey data flows to Central Store
4. **Suppression Service** → Check for existing surveys (24h window)

**Error Handling:**
- Network failures → Queue survey locally, retry on reconnect
- API errors → Show error message, allow retry
- Timeout → Mark as expired, allow retry via UFME Retry Engine

---

## Dependencies

**Required:**
- In-App Survey SDK Flutter Implementation (CSSV-2032) - Must be complete
- In-App Survey SDK Backend API (CSSV-2033) - Must be complete
- UFME Central Survey Data Store (CSSV-2089) - Must be operational
- Chat Service events (chat_ended event) - Must be available

**Nice to Have:**
- UFME Suppression Engine (CSSV-2091) - For duplicate prevention
- UFME Retry Engine (CSSV-2091) - For expired survey retry

---

## Design Specifications

**Visual Design:**
- Bottom sheet slides up from bottom (non-modal, dismissible)
- Purple headset icon at top
- Two-question flow:
  1. "Was your issue resolved?" - Yes (green) / No (gray) buttons
  2. "How was your experience?" - Bad (red) / Average (yellow) / Great (green) buttons
- "Send feedback" button (purple, full width, bottom)
- "X" close button (top right)
- "< Continue chat" header link (if applicable)

**Interaction Design:**
- Survey appears 2-3 seconds after chat ends
- Customer can dismiss by swiping down or tapping X
- Selected buttons show visual feedback (darker background, icon)
- "Send feedback" enabled only after both questions answered
- Confirmation shows green checkmark + "Feedback submitted"
- Survey auto-dismisses after 3 seconds or on tap

**Accessibility:**
- Screen reader support (announce questions and options)
- Keyboard navigation support
- High contrast mode support
- Focus indicators for all interactive elements

---

## Risk Considerations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Survey appears too frequently | High | Suppression rules (24h window, interaction_id check) |
| Low response rate | Medium | Non-intrusive UX, clear value proposition, quick flow |
| Network failures during submission | Medium | Offline queue, retry logic, error handling |
| Chat end event not detected | High | Fallback trigger mechanism, event logging |
| Survey blocks app usage | Low | Non-modal bottom sheet, dismissible, non-blocking |

---

## Open Questions

1. Should survey appear immediately after chat or with a delay?
2. Should we show different questions for chatbot vs agent-assisted chats?
3. What happens if customer closes app before submitting survey?
4. Should we support survey customization per chat type?
5. How do we handle surveys for multiple chat interactions in same session?

---

## Related Work

- **CSSV-2032**: In-App Survey SDK (Flutter) - Foundation SDK
- **CSSV-2033**: In-App Survey SDK (Backend API) - API endpoints
- **CSSV-2029**: In-App Survey SDK Initiative - Parent initiative
- **CSSV-1847**: UFME Initiative - Data infrastructure
- **CSSV-2092**: UFME In-App Survey Integration - Related epic












