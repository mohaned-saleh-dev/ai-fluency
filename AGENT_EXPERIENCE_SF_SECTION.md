## Agents Experience on Salesforce — In-App Messaging

### Overview

The In-App Message object on Salesforce enables agents to send and receive async messages to/from customers directly from the Case record. Agents interact with messages through the **App Messaging** tab on the Case page and the **"Send In-App Message"** quick action button.

---

### 1. Sending a New Message (Agent → Customer)

**Steps:**

1. Agent opens a Case record
2. Agent clicks the **"Send In-App Message"** button in the Case highlights panel (top of page, next to Edit/Delete)
3. A compact form appears with only the **Body** text field
4. Agent types the message and clicks **Save**
5. The message record is created and appears in the App Messaging tab

[Screenshot placeholder: Quick Action form with Body field]

**What the agent sees vs. what auto-populates:**

| Field | Agent Action | How It's Set |
|---|---|---|
| Body | **Agent types the message** | Manual input — only field the agent fills in |
| Case | Not visible on form | Auto-linked from the parent Case |
| Direction | Not visible on form | Auto-set to **Outbound** |
| Sender Type | Not visible on form | Auto-set to **Agent** |
| Sender Name | Not visible on form | Auto-set to agent's full name (via Flow) |
| Sent At | Not visible on form | Auto-set to current date/time (via Flow) |
| Delivery Status | Not visible on form | Auto-set to **Pending**, updated by backend system |

[Screenshot placeholder: App Message record detail showing all auto-populated fields]

---

### 2. Receiving a Message (Customer → Agent)

When a customer sends a message from the Tamara app:

1. The backend system creates an App Message record on the Case with Direction = **Inbound**
2. The Case status automatically changes to **Working**
3. The Case is reassigned to the Case owner per existing routing logic
4. The new message appears in the **App Messaging** tab on the Case

**What the agent sees:**

| Field | Value |
|---|---|
| Body | The customer's message |
| Direction | Inbound |
| Sender Type | Customer |
| Sender Name | Customer |
| Sent At | Timestamp of when the customer sent the message |
| Delivery Status | Delivered |

[Screenshot placeholder: App Messaging tab showing inbound + outbound messages]

---

### 3. Viewing the Conversation Thread

All messages (inbound and outbound) for a Case are displayed in the **App Messaging** tab on the Case record.

**Thread view columns:**

| Column | Description |
|---|---|
| Body | Message content (truncated preview) |
| Sender Name | Agent's name or "Customer" |
| Direction | Inbound (customer) or Outbound (agent) |
| Sent At | Date and time the message was sent |
| Delivery Status | Pending → Sent → Delivered or Failed |

Messages are sorted by **Sent At (ascending)** — oldest messages at the top, newest at the bottom, similar to a chat thread.

To read the full message, the agent clicks on the message row to open the full record.

[Screenshot placeholder: App Messaging tab with conversation thread]

---

### 4. Delivery Status Lifecycle

After an agent sends a message, the Delivery Status field tracks whether the customer received it:

| Status | Meaning | Action Required |
|---|---|---|
| **Pending** | Message just created, not yet sent to customer | None — wait for system to process |
| **Sent** | Message delivered to push notification service | None — customer should receive shortly |
| **Delivered** | Customer's device confirmed receipt | None — message received |
| **Failed** | Delivery failed after 3 retry attempts | Agent should follow up via alternative channel |

Delivery status is updated automatically by the backend system. Agents do not need to update this field manually.

---

### 5. Case Status Behavior

| Event | Case Status Change | Triggered By |
|---|---|---|
| Agent sends a message | No change | — |
| Customer sends a message | Status → **Working** | Salesforce Flow (automatic) |
| Agent resolves the case | Status → **Closed** | Agent manually closes |

---

### 6. Restrictions & Validation Rules

| Rule | Behavior | Error Message |
|---|---|---|
| **Agent cannot send messages on closed cases** | If an agent tries to create a new outbound message on a Case with Status = Closed, the save is blocked | *"This case is closed. You cannot send new messages on a closed case."* |
| **Customer messages on closed cases** | Handled by the frontend app — Salesforce does not block inbound messages | N/A |

---

### 7. Field Reference

**Object:** App Message (`App_Message__c`)
**Relationship:** Master-Detail to Case

| Field | API Name | Type | Editable by Agent | Auto-Populated |
|---|---|---|---|---|
| App Message Reference | `Name` | Auto Number | No | Yes (system) |
| Body | `Body__c` | Long Text Area (32768) | **Yes** | No |
| Case | `Case__c` | Master-Detail (Case) | No | Yes (from parent Case) |
| Direction | `Direction__c` | Picklist | No | Yes (Outbound for agent, Inbound for customer) |
| Sender Type | `Sender_Type__c` | Picklist | No | Yes (Agent / Customer / System) |
| Sender Name | `Sender_Name__c` | Text (255) | No | Yes (agent's full name or "Customer") |
| Sent At | `Sent_At__c` | Date/Time | No | Yes (current timestamp) |
| Delivery Status | `Delivery_Status__c` | Picklist | No | Yes (Pending → Sent → Delivered / Failed) |
| Public | `Public__c` | Checkbox | Yes | No |

---

### 8. Automation Summary

| Automation | Type | Trigger | What It Does |
|---|---|---|---|
| `InAppMsg - Auto Populate on Create` | Record-Triggered Flow (Before Save) | Any new App Message | Sets Sender Name to agent's full name, Sent At to current timestamp |
| `InAppMsg - Inbound Notify and Status Update` | Record-Triggered Flow (After Save) | New App Message with Direction = Inbound | Changes parent Case status to Working |
| `Block_Agent_Messages_On_Closed_Cases` | Validation Rule | Agent creates outbound message on closed Case | Blocks the save with error message |

---

### 9. End-to-End Automations (Salesforce + Backend)

This section describes automations that must work together for in-app messaging—not only the App Message object, but Case lifecycle, ownership, notifications, and idle closure.

#### 9.1 Customer replies while Case is “awaiting customer” (e.g. Pending Customer)

**Desired behavior**

- When the customer sends an in-app message, the backend creates an **App Message** with **Direction = Inbound** on the Case.
- Salesforce should set Case **Status** to **Working** (already covered by `InAppMsg - Inbound Notify and Status Update` when Direction = Inbound).
- **All existing org automations that run when a Case moves to Working** should then run as they do today—for example:
  - Reassignment or ownership rules tied to **Working**
  - Queue routing, milestone resets, or SLA timers if those are status-driven
  - Any other Flows/Process Builder/Triggers that subscribe to Case status or Case updates

**Implementation note for PM / developers**

- Treat **“Inbound App Message created” → “Case set to Working”** as the **single Salesforce-side hook** that must align with your existing “Case → Working” automation stack.
- **Document and test** each existing automation against this path (especially ownership and assignment), so nothing is skipped when the status change comes from messaging instead of from the agent UI.

#### 9.2 Agent sends a message to the customer (Outbound)

**Desired behavior**

- Agent uses **Send In-App Message**; record is created with **Direction = Outbound**.
- **Customer-facing push** (and in-app thread update) is **not** owned by Salesforce UI alone: the **backend** should detect the new outbound record (or receive an outbound event), then call the **notification service** to deliver a push to the customer’s device and update the app thread.
- **Delivery Status** on `App_Message__c` should progress **Pending → Sent → Delivered / Failed** via **backend → Salesforce API** (see backend integration ticket).

**Salesforce vs backend**

| Layer | Responsibility |
|---|---|
| Salesforce | Create App Message, auto-populate agent fields, enforce validation rules |
| Backend | Outbound detection, push to customer, update Delivery Status on the message record |

#### 9.3 Case idle / “awaiting customer” beyond X days → auto-close

**Desired behavior**

- If a Case stays in a **“waiting on customer”** type status beyond **X** days with no customer activity, the Case should **auto-close** (or move to the next status your policy defines), per existing Care operations rules.

**Current state (per stakeholder input)**

- This automation is **believed to already exist** in the org (e.g. scheduled Flow, time-based workflow, or similar).
- **Action:** **Regression test** this path after in-app messaging goes live: create/update Cases through the new channels and confirm auto-close still fires and uses the correct **X** and status values.

**Test ideas**

- Case in “awaiting customer” status → customer sends in-app message → Case becomes **Working** → idle timer should reset or cancel per existing design.
- Case in “awaiting customer” status → **no** customer message for **X** days → Case auto-closes as today.

#### 9.4 Automation matrix (ideal production state)

| Trigger | System | Automation | Outcome |
|---|---|---|---|
| New Inbound App Message | Salesforce Flow | `InAppMsg - Inbound Notify and Status Update` | Case Status → **Working** |
| Case Status → Working | Salesforce (existing) | Flows / PB / Apex as configured today | Ownership, routing, SLAs, etc. |
| New Outbound App Message | Backend | Webhook / polling / platform event consumer | Push notification to customer; optional app thread sync |
| Outbound delivery outcome | Backend | REST PATCH to App Message | **Delivery Status** updated |
| Case awaiting customer > X days | Salesforce (existing) | Scheduled / time-based automation | Auto-close or status change — **verify in QA** |

---

### 10. Open items for Salesforce PM + developers

| Item | Owner | Notes |
|---|---|---|
| Map all automations that run when Case → **Working** | SF team | Ensure Inbound App Message path triggers the same stack as manual status changes |
| Outbound → push / notification service | Backend | Contract: event payload, retries, Delivery Status updates |
| Idle auto-close after X days | SF team | Confirm existing automation; add test cases with messaging |
| Status picklist API values | SF team | Align “Pending Customer” / “Awaiting customer” naming with formulas and Flow entry criteria |
