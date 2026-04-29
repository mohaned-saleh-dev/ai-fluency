# Backend Ticket: In-App Message Delivery Status Webhook

---

## Summary

**Title:** Implement Salesforce webhook for In-App Message delivery status updates

**Type:** Story

**Priority:** High

**Epic:** In-App Customer Messaging

**Labels:** backend, salesforce-integration, in-app-messaging

---

## User Story

**As a** customer care agent using Salesforce,
**I want** the delivery status of each in-app message I send to automatically update in real time (from Pending → Sent → Delivered or Failed),
**So that** I can confirm whether the customer received my message and take action if delivery failed.

---

## Description

### Context

We have created a custom Salesforce object called **App Message** (`App_Message__c`) that stores async messages between agents and customers. When an agent creates a new App Message record on a Case, the `Delivery_Status__c` field defaults to `Pending`. The backend needs to:

1. **Detect** when a new outbound App Message is created in Salesforce
2. **Deliver** the message to the customer's mobile app
3. **Update** the Delivery Status field on the Salesforce record based on the delivery result

### Salesforce Object Details

**Object:** `App_Message__c`

| Field Label | API Name | Data Type | Description |
|---|---|---|---|
| App Message Reference | `Name` | Auto Number (AP-{00000000}) | Unique record identifier |
| Body | `Body__c` | Long Text Area (32768) | The message content |
| Case | `Case__c` | Master-Detail (Case) | Parent case reference |
| Direction | `Direction__c` | Picklist | `Outbound` (agent→customer) or `Inbound` (customer→agent) |
| Sender Type | `Sender_Type__c` | Picklist | `Agent`, `Customer`, or `System` |
| Sender Name | `Sender_Name__c` | Text (255) | Full name of the sender |
| Sent At | `Sent_At__c` | Date/Time | Timestamp when the message was created |
| Delivery Status | `Delivery_Status__c` | Picklist | `Pending`, `Sent`, `Delivered`, `Failed` |
| Public | `Public__c` | Checkbox | Whether the message is public |

**Salesforce Environment:**
- Sandbox: `tamarauat.sandbox`
- Instance: `java-flow-9753`

---

## What Needs to Be Implemented

### 1. Salesforce Outbound Webhook (SF → Backend)

Set up a mechanism to detect new outbound App Message records in Salesforce and send them to the backend. Options:

**Option A — Salesforce Flow + Platform Event (Recommended):**
- Create a Record-Triggered Flow on `App_Message__c` (After Save, when Direction = Outbound)
- The Flow publishes a Platform Event containing the message payload
- Backend subscribes to the Platform Event via CometD/gRPC

**Option B — Salesforce Apex Trigger + HTTP Callout:**
- After Insert trigger on `App_Message__c`
- Fires an async HTTP POST to the backend webhook endpoint
- Endpoint: `POST /webhook/sf/in-app-message`

**Webhook Payload (regardless of approach):**

```json
{
  "event": "app_message.created",
  "data": {
    "record_id": "a]1XXXXXXXXXXXXXXX",
    "record_name": "AP-00000010",
    "case_id": "500XXXXXXXXXXXXXXX",
    "case_number": "00002456",
    "direction": "Outbound",
    "sender_type": "Agent",
    "sender_name": "Ahmed Al-Rashid",
    "body": "Your refund has been processed and should reflect in 3-5 business days.",
    "sent_at": "2026-03-25T11:30:00.000Z",
    "delivery_status": "Pending"
  }
}
```

### 2. Message Delivery to Customer App (Backend → App)

Once the backend receives the webhook:

1. Look up the customer associated with the Case (via Case Contact or Account)
2. Store the message in the backend message store (for the customer's chat thread)
3. Send a **push notification** to the customer's device:
   - **Title:** `New message from Tamara Support`
   - **Body:** Truncated message preview (first 100 chars)
   - **Deep link:** Opens the specific case/conversation thread in the app
4. Update delivery status based on result

### 3. Delivery Status Callback (Backend → SF)

After attempting delivery, update the `Delivery_Status__c` field on the original App Message record in Salesforce.

**API Call:**

```
PATCH /services/data/vXX.0/sobjects/App_Message__c/{record_id}
Content-Type: application/json
Authorization: Bearer {sf_access_token}

{
  "Delivery_Status__c": "Sent"
}
```

**Status Transition Logic:**

| Scenario | Set Status To | When |
|---|---|---|
| Message successfully sent to push notification service | `Sent` | Immediately after push API returns success |
| Customer's device confirms receipt (delivery receipt) | `Delivered` | When delivery receipt callback is received from push provider |
| Push notification service returns error | `Failed` | Immediately after push API returns failure |
| Push retry exhausted (3 attempts) | `Failed` | After final retry fails |

**Retry Logic:**
- On initial failure, retry up to **3 times** with exponential backoff (5s, 15s, 45s)
- After 3 failed attempts, set status to `Failed`
- Log the failure reason for debugging

### 4. Inbound Message Sync (App → SF)

When a customer sends a reply from the app:

1. Backend receives the message via `POST /cases/{case_id}/messages`
2. Backend creates a new `App_Message__c` record in Salesforce via API:

```
POST /services/data/vXX.0/sobjects/App_Message__c/
Content-Type: application/json
Authorization: Bearer {sf_access_token}

{
  "Case__c": "{sf_case_id}",
  "Body__c": "Customer's reply message text",
  "Direction__c": "Inbound",
  "Sender_Type__c": "Customer",
  "Sender_Name__c": "Customer",
  "Sent_At__c": "2026-03-25T12:00:00.000Z",
  "Delivery_Status__c": "Delivered"
}
```

**Note:** A separate Salesforce Flow (`InAppMsg - Inbound Notify and Status Update`) will be configured to handle:
- Changing the Case status to `Working` when an inbound message is created
- Sending a bell notification to the Case owner (agent)

These are Salesforce-side automations and do not need to be implemented by the backend.

---

## Acceptance Criteria

### AC1: Outbound Message Detection
- [ ] When an agent creates a new App Message with Direction = "Outbound" in Salesforce, the backend is notified within **5 seconds**
- [ ] The webhook/event payload includes all required fields: record_id, case_id, case_number, direction, sender_type, sender_name, body, sent_at

### AC2: Message Delivery to Customer
- [ ] The message is stored in the backend message store and associated with the correct customer and case thread
- [ ] A push notification is sent to the customer's registered device(s)
- [ ] Push notification contains the message preview and deep links to the correct conversation thread in the app
- [ ] If the customer has multiple devices, notification is sent to all registered devices

### AC3: Delivery Status Updates
- [ ] `Delivery_Status__c` is updated to `Sent` when the push notification service accepts the message
- [ ] `Delivery_Status__c` is updated to `Delivered` when a delivery receipt is received (if supported by push provider)
- [ ] `Delivery_Status__c` is updated to `Failed` after 3 failed delivery attempts
- [ ] Status updates are reflected in Salesforce within **10 seconds** of the status change

### AC4: Retry Logic
- [ ] Failed deliveries are retried up to 3 times with exponential backoff (5s, 15s, 45s)
- [ ] Each retry attempt is logged with timestamp and failure reason
- [ ] After final failure, the message is marked as `Failed` and no further retries are attempted

### AC5: Inbound Message Sync
- [ ] When a customer sends a message from the app, a new `App_Message__c` record is created in Salesforce within **5 seconds**
- [ ] The record is created with Direction = "Inbound", Sender_Type = "Customer", Sender_Name = "Customer"
- [ ] The record is correctly linked to the parent Case via `Case__c`
- [ ] The `Sent_At__c` timestamp matches the time the customer sent the message (not the time it was synced)
- [ ] The `Delivery_Status__c` is set to "Delivered" on creation (since SF received it)

### AC6: Error Handling
- [ ] If the Salesforce API is unreachable when updating delivery status, the update is queued and retried
- [ ] If the Salesforce API is unreachable when creating an inbound message, the message is queued and retried
- [ ] All API errors are logged with sufficient detail for debugging (request payload, response code, error message)
- [ ] No duplicate App Message records are created (idempotency check using a unique message ID)

### AC7: Security
- [ ] Salesforce API authentication uses OAuth 2.0 with a Connected App
- [ ] Webhook endpoint (if using Option B) validates the request origin (IP whitelist or signature verification)
- [ ] Message content is transmitted over HTTPS only
- [ ] No customer PII is logged in plain text

---

## Technical Notes

- **Salesforce API Version:** Use the latest stable API version (v60.0+)
- **Authentication:** Use OAuth 2.0 JWT Bearer Flow for server-to-server Salesforce API calls
- **Rate Limits:** Salesforce API has per-org rate limits. Batch updates where possible. Consider using Composite API for bulk operations.
- **Idempotency:** Use the App Message `Name` field (e.g., AP-00000010) as an idempotency key to prevent duplicate processing
- **Monitoring:** Set up alerts for: delivery failure rate > 5%, webhook processing latency > 10s, Salesforce API auth failures

---

## Dependencies

| Dependency | Owner | Status |
|---|---|---|
| App Message object created in Salesforce | Salesforce Admin (Mohaned) | Done |
| Salesforce Connected App for API auth | Salesforce Admin | To be created |
| Push notification infrastructure | Mobile team | Existing |
| Customer ↔ Case mapping in backend | Backend | Existing |
| Chat SDK integration for message display | Mobile team | In progress (separate PRD) |

---

## Out of Scope

- Salesforce-side automation (Flows for notifications, status changes) — handled by Salesforce Admin
- Agent UI/UX on Salesforce — handled by Salesforce Admin
- Customer-facing app UI — handled by Mobile team (separate PRD)
- Rich media attachments (images, files) — Phase 2
- Read receipts from customer — Phase 2
