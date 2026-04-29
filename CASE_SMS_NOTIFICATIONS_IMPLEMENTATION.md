# Customer Care — Case SMS Notifications

## Overview

Automated SMS notifications for Customer Care cases on Salesforce. Customers receive an SMS when their case is opened (confirming receipt and setting expectations) and when it is resolved (confirming resolution). The SMS is sent via a backend webhook that reuses the existing notification service — **no backend changes are required**.

**Scope:**
- Record Type: **Customer Care** only
- Account Type: **Person Account** only
- Country: **KSA** only
- Languages: **Arabic** and **English** (determined by `Case_Language__c`)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        SALESFORCE                           │
│                                                             │
│  Case Created / Updated                                     │
│       │                                                     │
│       ▼                                                     │
│  Record-Triggered Flow (After Save → Async Path)            │
│       │                                                     │
│       ├─ Evaluate trigger conditions                        │
│       │   (origin, record type, account type, country, etc) │
│       ├─ Determine language (AR / EN)                       │
│       ├─ Construct SMS text                                 │
│       ▼                                                     │
│  Apex Invocable Action: CaseSMSNotification                 │
│       │                                                     │
│       ▼  @future(callout=true)                              │
│  HTTP POST to backend webhook ──────────────────────────────┼──┐
│       │                                                     │  │
│       ▼                                                     │  │
│  Update Case: Set tracking field(s)                         │  │
│   • Care_Opening_SMS_Sent__c = true  (Flows 1 & 2)         │  │
│   • Care_Closing_SMS_Sent__c = true  (Flow 3)              │  │
│                                                             │  │
└─────────────────────────────────────────────────────────────┘  │
                                                                 │
                                                                 ▼
                                              ┌──────────────────────────────┐
                                              │       BACKEND SERVICE        │
                                              │                              │
                                              │  POST /agent/salesforce/     │
                                              │       send-sms               │
                                              │                              │
                                              │  • Resolves phone number     │
                                              │    from account/customer     │
                                              │  • Sends SMS via existing    │
                                              │    notification service      │
                                              └──────────────────────────────┘
```

---

## Backend Webhook

A dedicated endpoint was created for Salesforce-initiated SMS notifications. It plugs into the existing notification service that was previously used by Zendesk.

### Endpoint

| Property | Value |
|----------|-------|
| **URL (Staging)** | `https://api-staging.tamara.co/agent/salesforce/send-sms` |
| **URL (Production)** | `https://api.tamara.co/agent/salesforce/send-sms` *(to be confirmed)* |
| **Method** | `POST` |
| **Content-Type** | `application/json` |
| **Authentication** | `Bearer` token (system-level JWT, role: `ROLE_SYSTEM_SALESFORCE`) |

### Request Payload

```json
{
  "case_id": "500XXXXXXXXXXXXXXX",
  "customer_id": "001XXXXXXXXXXXXXXX",
  "text": "We've received your complaint 00012345. It's under review and should be resolved within 10 working days."
}
```

| Field | Type | Description | Salesforce Source |
|-------|------|-------------|-----------------|
| `case_id` | String | Salesforce Case record ID (18-char) | `{!$Record.Id}` |
| `customer_id` | String | Salesforce Account ID linked to the Case | `{!$Record.AccountId}` |
| `text` | String | Full SMS body, pre-constructed by the Flow based on language | Built in Flow using `Case_Language__c` and `CaseNumber` |

### Response

| Status | Meaning |
|--------|---------|
| `200` | SMS queued successfully |
| `4xx` | Client error (invalid payload, auth failure) |
| `5xx` | Server error |

### What the Backend Does

1. Receives the payload from Salesforce
2. Looks up the customer/account using `customer_id` (Salesforce Account ID)
3. Resolves the phone number associated with the account
4. Dispatches the SMS via the existing notification service
5. Returns success/failure

> The backend handles phone number resolution — Salesforce does not need to query or send the phone number.

---

## SMS Content

Determined by the `Case_Language__c` field on the Case record. The Case Number is dynamically inserted.

### Opening SMS (Case Created / Transferred)

**English:**

```
We've received your complaint {CaseNumber}. It's under review and should be resolved within 10 working days.
```

**Arabic:**

```
تم استلام شكواك رقم {CaseNumber}. هي الآن قيد المراجعة، ونعمل على حلها خلال مدة أقصاها 10 أيام عمل. نشكر تفهمك.
```

### Closing SMS (Case Solved)

**English:**

```
Your complaint {CaseNumber} is resolved. Please reach out for further support.
```

**Arabic:**

```
تم حل شكواك رقم {CaseNumber}. لا تتردد في التواصل معنا للحصول على مزيد من الدعم.
```

> In the Salesforce Flow, `{CaseNumber}` is replaced with `{!$Record.CaseNumber}` (the visible case number, e.g. `00012345`).

---

## Trigger Conditions

### Opening SMS — Trigger Matrix

The opening SMS fires under **two mutually exclusive scenarios** depending on case origin:

| # | Scenario | Trigger Event | Case Origin | Additional Condition |
|---|----------|--------------|-------------|---------------------|
| **1** | Email / API case created | Case is **CREATED** | `Email` or `Web` | — |
| **2** | Live case transferred | Case is **UPDATED** | `Chat` or `Phone` | `OwnerId` is changed (case transferred to a different queue or user) |

Both scenarios share these **common conditions**:

| Condition | Field | Operator | Value |
|-----------|-------|----------|-------|
| Record Type | `RecordType.DeveloperName` | Equals | `Customer_Care` |
| Account Type | `Account.IsPersonAccount` | Equals | `True` |
| Country | `Account.Country_of_Registration__c` | Equals | `KSA` |
| Language | `Case_Language__c` | Equals | `AR` or `EN` |

**Actions:**
1. Send webhook (Apex invocable action)
2. Set `Care_Opening_SMS_Sent__c` = `True` on the Case

### Closing SMS — Trigger Conditions

| Condition | Field | Operator | Value |
|-----------|-------|----------|-------|
| Event | — | — | Case is **UPDATED** |
| Status | `Status` | Equals | `Solved` |
| Opening SMS was sent | `Care_Opening_SMS_Sent__c` | Equals | `True` |
| Closing SMS not yet sent | `Care_Closing_SMS_Sent__c` | Equals | `False` |

> The closing SMS is **only sent for cases where the opening SMS was previously sent**, and **only once per case** (the `Care_Closing_SMS_Sent__c` field prevents duplicates even if the case is reopened and re-solved).

**Actions:**
1. Send webhook (Apex invocable action)
2. Set `Care_Closing_SMS_Sent__c` = `True` on the Case

### Complete Condition Detail

#### Flow 1 — Opening SMS: Email & API Cases (On Create)

```
TRIGGER:   Case is CREATED

ALL of the following must be true:
  1. Case Origin           = "Email"  OR  "Web"
  2. Record Type           = Customer Care
  3. Account Type          = Person Account  (Account.IsPersonAccount = true)
  4. Account Country       = KSA             (Account.Country_of_Registration__c = "KSA")
  5. Case Language         = "AR"  OR  "EN"
  6. Status               ≠ "Solved"         (skip if created already solved)

ACTIONS:
  → Determine language (AR or EN)
  → Construct SMS text
  → Send webhook via Apex action
  → Update Case: Care_Opening_SMS_Sent__c = true
```

#### Flow 2 — Opening SMS: Live Cases (On Owner Change)

```
TRIGGER:   Case is UPDATED

ALL of the following must be true:
  1. Case Origin             = "Chat"  OR  "Phone"
  2. Record Type             = Customer Care
  3. Account Type            = Person Account  (Account.IsPersonAccount = true)
  4. Account Country         = KSA             (Account.Country_of_Registration__c = "KSA")
  5. Case Language           = "AR"  OR  "EN"
  6. OwnerId                 IS CHANGED        (owner changed to different queue/user)
  7. Care_Opening_SMS_Sent__c = false           (not already sent)

ACTIONS:
  → Determine language (AR or EN)
  → Construct SMS text
  → Send webhook via Apex action
  → Update Case: Care_Opening_SMS_Sent__c = true
```

#### Flow 3 — Closing SMS: All Eligible Cases (On Solve)

```
TRIGGER:   Case is UPDATED

ALL of the following must be true:
  1. Status                   = "Solved"
  2. Care_Opening_SMS_Sent__c  = true            (opening SMS was sent)
  3. Care_Closing_SMS_Sent__c  = false            (closing SMS not yet sent)

ACTIONS:
  → Determine language (AR or EN)
  → Construct SMS text
  → Send webhook via Apex action
  → Update Case: Care_Closing_SMS_Sent__c = true
```

### Edge Cases

| Scenario | Opening SMS | Closing SMS | Why |
|----------|------------|-------------|-----|
| Email case created → worked → solved | Sent on creation | Sent on solve | Standard flow |
| Email case created already in Solved status | **Not sent** | **Not sent** | Status guard blocks opening; tracking fields not set |
| Phone case resolved by L1 during the call (no transfer) | **Not sent** | **Not sent** | Owner never changed; `Care_Opening_SMS_Sent__c` remains false, so closing SMS is blocked |
| Phone case transferred L1 → L2 → solved | Sent on first transfer | Sent on solve | Tracking field set on first transfer; closing checks it |
| Phone case transferred L1 → L2 → L3 (multiple transfers) | Sent once (first transfer only) | — | `Care_Opening_SMS_Sent__c` prevents duplicate opening SMS |
| Case solved → reopened → solved again | — | **Sent once only** | `Care_Closing_SMS_Sent__c = true` after first solve prevents second closing SMS |
| Non-Customer Care case | Not sent | Not sent | Record Type filter blocks it |
| Business Account (not Person Account) | Not sent | Not sent | Account Type filter blocks it |
| Account country ≠ KSA | Not sent | Not sent | Country filter blocks it |

---

## Salesforce Components

### 1. Custom Fields (Case Object)

Two hidden tracking checkboxes on the Case object. Neither should be visible to agents.

**Field A — Care Opening SMS Sent**

| Property | Value |
|----------|-------|
| **Object** | Case |
| **Field Label** | `Care Opening SMS Sent` |
| **API Name** | `Care_Opening_SMS_Sent__c` |
| **Type** | Checkbox |
| **Default Value** | `false` (Unchecked) |
| **Page Layouts** | **Do NOT add to any page layout** |
| **Field-Level Security** | Read-only for all profiles except System Administrator |
| **Description** | Tracks whether the opening SMS notification was sent. Set to true by Flows 1 and 2. Used as a prerequisite for the closing SMS. |

**Field B — Care Closing SMS Sent**

| Property | Value |
|----------|-------|
| **Object** | Case |
| **Field Label** | `Care Closing SMS Sent` |
| **API Name** | `Care_Closing_SMS_Sent__c` |
| **Type** | Checkbox |
| **Default Value** | `false` (Unchecked) |
| **Page Layouts** | **Do NOT add to any page layout** |
| **Field-Level Security** | Read-only for all profiles except System Administrator |
| **Description** | Tracks whether the closing SMS notification was sent. Set to true by Flow 3. Prevents duplicate closing SMS if a case is reopened and re-solved. |

### 2. Remote Site Setting

Allows Salesforce to make outbound HTTP calls to the backend. Already created on staging.

**Staging:**

```
URL:            https://api-staging.tamara.co
Full Endpoint:  https://api-staging.tamara.co/agent/salesforce/send-sms
Method:         POST
Authorization:  Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhY2NvdW50SWQiOiJzYWxlc2ZvcmNlIiwidHlwZSI6InN5c3RlbSIsInNhbHQiOiIiLCJyb2xlcyI6WyJST0xFX1NZU1RFTV9TQUxFU0ZPUkNFIl0sImlhdCI6MTc3NTIxNjE4MiwiaXNzIjoiVGFtYXJhIn0.ae2G2ci-Sngc53WvOPw4w5Lety2iBk859zfzeiFJXr_Li9eJWSo_MYbCS57fSmc0aKtkejHNcPB1RA9nw02MnXWFWdYjOg-k7SUoof3wmnt-FUDyBJb-Cm2Q5xBiP-D_3NM_IVUX2KjnRdW8vaNjflHNwfIRP2L-4vrRw64GlgYCN-q4ne-lqOjFKc7reruBk0NSdiRNOEg8WeYRLisUWG9ZA0kq-fpkEMAefRHzn5KyMck7ZtdxKxczcRdCHGtIumHbYq5-2-rswAK9PmnWe57kCbRcoznxKdnhax9p_xO80_DczxB_aHhx-5oLY9whHv5pcuMITydJhf6P7L4k-w
```

**Full curl example (staging):**

```bash
curl -X POST https://api-staging.tamara.co/agent/salesforce/send-sms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhY2NvdW50SWQiOiJzYWxlc2ZvcmNlIiwidHlwZSI6InN5c3RlbSIsInNhbHQiOiIiLCJyb2xlcyI6WyJST0xFX1NZU1RFTV9TQUxFU0ZPUkNFIl0sImlhdCI6MTc3NTIxNjE4MiwiaXNzIjoiVGFtYXJhIn0.ae2G2ci-Sngc53WvOPw4w5Lety2iBk859zfzeiFJXr_Li9eJWSo_MYbCS57fSmc0aKtkejHNcPB1RA9nw02MnXWFWdYjOg-k7SUoof3wmnt-FUDyBJb-Cm2Q5xBiP-D_3NM_IVUX2KjnRdW8vaNjflHNwfIRP2L-4vrRw64GlgYCN-q4ne-lqOjFKc7reruBk0NSdiRNOEg8WeYRLisUWG9ZA0kq-fpkEMAefRHzn5KyMck7ZtdxKxczcRdCHGtIumHbYq5-2-rswAK9PmnWe57kCbRcoznxKdnhax9p_xO80_DczxB_aHhx-5oLY9whHv5pcuMITydJhf6P7L4k-w" \
  -d '{
    "case_id": "500XXXXXXXXXXXXXXX",
    "customer_id": "001XXXXXXXXXXXXXXX",
    "text": "SMS message text here"
  }'
```

**Production:** Endpoint URL and Bearer token to be provided before production deployment.

### 3. Apex Class: CaseSMSNotification

A lightweight Apex class that performs the HTTP callout to the backend webhook. Exposed as an Invocable Action callable from Flows.

| Property | Value |
|----------|-------|
| **Class Name** | `CaseSMSNotification` |
| **Test Class** | `CaseSMSNotificationTest` |
| **Invocable Action Label** | `Send Case SMS Notification` |
| **Status (Staging)** | Already deployed |
| **Status (Production)** | Pending deployment |

**Invocable Inputs:**

| Input | Type | Description | Flow Value |
|-------|------|-------------|------------|
| `caseId` | String | Salesforce Case record ID | `{!$Record.Id}` |
| `customerId` | String | Account ID from the Case | `{!$Record.AccountId}` |
| `smsText` | String | The full SMS message body | `{!SMSText}` (Flow variable) |

**How it works:**

1. Flow calls the `@InvocableMethod` `sendSMS`
2. `sendSMS` delegates to `sendSMSAsync` (annotated with `@future(callout=true)`)
3. `sendSMSAsync` makes the HTTP POST to the backend endpoint with the Bearer token
4. Endpoint URL and auth token are configured as constants in the class

> **Production:** The `ENDPOINT` and `AUTH_TOKEN` constants in the class must be updated to production values before deploying to production.

### 4. Record-Triggered Flows

| # | Flow Label | API Name | Trigger | Purpose |
|---|-----------|----------|---------|---------|
| 1 | `CaseSMS - Opening Email/API` | `CaseSMS_Opening_Email_API` | Case **created** | Opening SMS for Email & API cases |
| 2 | `CaseSMS - Opening Live Transfer` | `CaseSMS_Opening_Live_Transfer` | Case **updated** (owner changed) | Opening SMS for Chat & Phone cases on transfer |
| 3 | `CaseSMS - Closing` | `CaseSMS_Closing` | Case **updated** (status → Solved) | Closing SMS for all eligible cases |

---

## Flow Specifications

### Flow 1: CaseSMS — Opening Email/API

**Type:** Record-Triggered Flow

**Start Configuration:**

| Setting | Value |
|---------|-------|
| Object | `Case` |
| Trigger | **A record is created** |
| Condition Logic | **Custom Condition Logic:** `(1 OR 2) AND 3 AND 4 AND 5 AND (6 OR 7)` |
| Condition 1 | `Origin` **Equals** `Email` |
| Condition 2 | `Origin` **Equals** `Web` |
| Condition 3 | `RecordType.DeveloperName` **Equals** `Customer_Care` |
| Condition 4 | `Account.IsPersonAccount` **Equals** `True` |
| Condition 5 | `Account.Country_of_Registration__c` **Equals** `KSA` |
| Condition 6 | `Case_Language__c` **Equals** `AR` |
| Condition 7 | `Case_Language__c` **Equals** `EN` |
| Optimize for | **Actions and Related Records** |
| When to run | **After the record is saved** |

> **Note on cross-object conditions (4, 5):** If cross-object field references are not available in entry conditions in your org, move conditions 4 and 5 into the flow body as a Get Records + Decision element instead.

**Flow Canvas (Async Path):**

```
Start (Case created — filtered by origin, record type, account, country, language)
  │
  └─ Run Asynchronously
       │
       ▼
     Decision: Check Language
       │
       ├─ Arabic (Case_Language__c = "AR")
       │    │
       │    └─ Assignment: Set SMSText
       │         Value: "تم استلام شكواك رقم {!$Record.CaseNumber}. هي الآن
       │                 قيد المراجعة، ونعمل على حلها خلال مدة أقصاها 10
       │                 أيام عمل. نشكر تفهمك."
       │
       └─ English (default)
            │
            └─ Assignment: Set SMSText
                 Value: "We've received your complaint {!$Record.CaseNumber}.
                         It's under review and should be resolved within 10
                         working days."
                   │
                   ▼
             Action: Send Case SMS Notification
               • Case ID      = {!$Record.Id}
               • Customer ID  = {!$Record.AccountId}
               • SMS Text     = {!SMSText}
                   │
                   ▼
             Update Records: Mark Opening SMS Sent
               • Record: Current Case
               • Field:  Care_Opening_SMS_Sent__c = true
                   │
                   ▼
                 End
```

---

### Flow 2: CaseSMS — Opening Live Transfer

**Type:** Record-Triggered Flow

**Start Configuration:**

| Setting | Value |
|---------|-------|
| Object | `Case` |
| Trigger | **A record is updated** |
| Condition Logic | **Custom Condition Logic:** `(1 OR 2) AND 3 AND 4 AND 5 AND (6 OR 7) AND 8 AND 9` |
| Condition 1 | `Origin` **Equals** `Chat` |
| Condition 2 | `Origin` **Equals** `Phone` |
| Condition 3 | `RecordType.DeveloperName` **Equals** `Customer_Care` |
| Condition 4 | `Account.IsPersonAccount` **Equals** `True` |
| Condition 5 | `Account.Country_of_Registration__c` **Equals** `KSA` |
| Condition 6 | `Case_Language__c` **Equals** `AR` |
| Condition 7 | `Case_Language__c` **Equals** `EN` |
| Condition 8 | `OwnerId` **Is Changed** `True` |
| Condition 9 | `Care_Opening_SMS_Sent__c` **Equals** `False` |
| Optimize for | **Actions and Related Records** |
| When to run | **After the record is saved** |

**Flow Canvas (Async Path):**

```
Start (Case updated — live origin, owner changed, SMS not yet sent)
  │
  └─ Run Asynchronously
       │
       ▼
     Decision: Check Language
       │
       ├─ Arabic (Case_Language__c = "AR")
       │    │
       │    └─ Assignment: Set SMSText
       │         Value: "تم استلام شكواك رقم {!$Record.CaseNumber}. هي الآن
       │                 قيد المراجعة، ونعمل على حلها خلال مدة أقصاها 10
       │                 أيام عمل. نشكر تفهمك."
       │
       └─ English (default)
            │
            └─ Assignment: Set SMSText
                 Value: "We've received your complaint {!$Record.CaseNumber}.
                         It's under review and should be resolved within 10
                         working days."
                   │
                   ▼
             Action: Send Case SMS Notification
               • Case ID      = {!$Record.Id}
               • Customer ID  = {!$Record.AccountId}
               • SMS Text     = {!SMSText}
                   │
                   ▼
             Update Records: Mark Opening SMS Sent
               • Record: Current Case
               • Field:  Care_Opening_SMS_Sent__c = true
                   │
                   ▼
                 End
```

---

### Flow 3: CaseSMS — Closing

**Type:** Record-Triggered Flow

**Start Configuration:**

| Setting | Value |
|---------|-------|
| Object | `Case` |
| Trigger | **A record is updated** |
| Condition Logic | **All Conditions Are Met (AND)** |
| Condition 1 | `Status` **Equals** `Solved` |
| Condition 2 | `Care_Opening_SMS_Sent__c` **Equals** `True` |
| Condition 3 | `Care_Closing_SMS_Sent__c` **Equals** `False` |
| Optimize for | **Actions and Related Records** |
| When to run | **After the record is saved** |

**Flow Canvas (Async Path):**

```
Start (Case updated — status = Solved, opening SMS sent, closing SMS not yet sent)
  │
  └─ Run Asynchronously
       │
       ▼
     Decision: Check Language
       │
       ├─ Arabic (Case_Language__c = "AR")
       │    │
       │    └─ Assignment: Set SMSText
       │         Value: "تم حل شكواك رقم {!$Record.CaseNumber}. لا تتردد
       │                 في التواصل معنا للحصول على مزيد من الدعم."
       │
       └─ English (default)
            │
            └─ Assignment: Set SMSText
                 Value: "Your complaint {!$Record.CaseNumber} is resolved.
                         Please reach out for further support."
                   │
                   ▼
             Action: Send Case SMS Notification
               • Case ID      = {!$Record.Id}
               • Customer ID  = {!$Record.AccountId}
               • SMS Text     = {!SMSText}
                   │
                   ▼
             Update Records: Mark Closing SMS Sent
               • Record: Current Case
               • Field:  Care_Closing_SMS_Sent__c = true
                   │
                   ▼
                 End
```

---

## Webhook Payloads — Exact Format

All payloads are sent to the same endpoint:

```
POST https://api-staging.tamara.co/agent/salesforce/send-sms
Content-Type: application/json
Authorization: Bearer <token>
```

### Opening SMS — English

```json
{
  "case_id": "{!$Record.Id}",
  "customer_id": "{!$Record.AccountId}",
  "text": "We've received your complaint {!$Record.CaseNumber}. It's under review and should be resolved within 10 working days."
}
```

### Opening SMS — Arabic

```json
{
  "case_id": "{!$Record.Id}",
  "customer_id": "{!$Record.AccountId}",
  "text": "تم استلام شكواك رقم {!$Record.CaseNumber}. هي الآن قيد المراجعة، ونعمل على حلها خلال مدة أقصاها 10 أيام عمل. نشكر تفهمك."
}
```

### Closing SMS — English

```json
{
  "case_id": "{!$Record.Id}",
  "customer_id": "{!$Record.AccountId}",
  "text": "Your complaint {!$Record.CaseNumber} is resolved. Please reach out for further support."
}
```

### Closing SMS — Arabic

```json
{
  "case_id": "{!$Record.Id}",
  "customer_id": "{!$Record.AccountId}",
  "text": "تم حل شكواك رقم {!$Record.CaseNumber}. لا تتردد في التواصل معنا للحصول على مزيد من الدعم."
}
```

---

## Apex Class — Source Code

### CaseSMSNotification.cls

```java
public class CaseSMSNotification {

    private static final String ENDPOINT = 'https://api-staging.tamara.co/agent/salesforce/send-sms';
    private static final String AUTH_TOKEN = '<BEARER_TOKEN>';

    @InvocableMethod(label='Send Case SMS Notification'
                     description='Sends SMS notification via Tamara backend API'
                     category='Case')
    public static void sendSMS(List<SMSRequest> requests) {
        for (SMSRequest req : requests) {
            sendSMSAsync(req.caseId, req.customerId, req.smsText);
        }
    }

    @future(callout=true)
    private static void sendSMSAsync(String caseId, String customerId, String smsText) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(ENDPOINT);
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setHeader('Authorization', 'Bearer ' + AUTH_TOKEN);

        String body = JSON.serialize(new Map<String, String>{
            'case_id' => caseId,
            'customer_id' => customerId,
            'text' => smsText
        });
        req.setBody(body);

        try {
            Http http = new Http();
            HttpResponse res = http.send(req);
            if (res.getStatusCode() >= 400) {
                System.debug(LoggingLevel.ERROR,
                    'CaseSMSNotification failed: ' + res.getStatusCode()
                    + ' ' + res.getBody());
            }
        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR,
                'CaseSMSNotification exception: ' + e.getMessage());
        }
    }

    public class SMSRequest {
        @InvocableVariable(required=true label='Case ID'
                          description='Salesforce Case record ID')
        public String caseId;

        @InvocableVariable(required=true label='Customer ID'
                          description='Account ID from the Case')
        public String customerId;

        @InvocableVariable(required=true label='SMS Text'
                          description='The SMS message body')
        public String smsText;
    }
}
```

### CaseSMSNotificationTest.cls

```java
@isTest
private class CaseSMSNotificationTest {

    @isTest
    static void testSendSMS() {
        Test.setMock(HttpCalloutMock.class, new MockSMSResponse());

        Account acc = new Account(Name = 'Test Account');
        insert acc;

        Case c = new Case(
            Subject = 'Test Case',
            Status = 'New',
            AccountId = acc.Id
        );
        insert c;

        CaseSMSNotification.SMSRequest req = new CaseSMSNotification.SMSRequest();
        req.caseId = c.Id;
        req.customerId = acc.Id;
        req.smsText = 'Test SMS message';

        Test.startTest();
        CaseSMSNotification.sendSMS(
            new List<CaseSMSNotification.SMSRequest>{ req }
        );
        Test.stopTest();
    }

    private class MockSMSResponse implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"success": true}');
            return res;
        }
    }
}
```

---

## Deployment Checklist

### Staging (Sandbox — TamaraUAT)

- [x] Remote Site Setting: `Tamara_Backend_SMS` → `https://api-staging.tamara.co`
- [x] Apex Class: `CaseSMSNotification` deployed
- [x] Apex Test Class: `CaseSMSNotificationTest` deployed
- [ ] Custom Field: `Care_Opening_SMS_Sent__c` on Case (checkbox, default false, hidden from layouts)
- [ ] Custom Field: `Care_Closing_SMS_Sent__c` on Case (checkbox, default false, hidden from layouts)
- [ ] Flow 1: `CaseSMS - Opening Email/API` — created and activated
- [ ] Flow 2: `CaseSMS - Opening Live Transfer` — created and activated
- [ ] Flow 3: `CaseSMS - Closing` — created and activated
- [ ] End-to-end testing (see Testing section)

### Production

- [ ] Remote Site Setting: `Tamara_Backend_SMS` → `https://api.tamara.co`
- [ ] Update `ENDPOINT` constant in Apex class to production URL
- [ ] Update `AUTH_TOKEN` constant in Apex class to production Bearer token
- [ ] Deploy Apex class + test class
- [ ] Create `Care_Opening_SMS_Sent__c` field on Case (hidden from layouts)
- [ ] Create `Care_Closing_SMS_Sent__c` field on Case (hidden from layouts)
- [ ] Deploy all 3 Flows
- [ ] Activate all 3 Flows
- [ ] Smoke test with a real case

---

## Testing Plan

### Test 1 — Email Case (Happy Path)

1. Create a Case with Origin = `Email`, Record Type = `Customer Care`, Account = Person Account in KSA, Language = `EN`
2. **Expected:** Opening SMS sent immediately on creation. `Care_Opening_SMS_Sent__c` = true.
3. Update the case status to `Solved`
4. **Expected:** Closing SMS sent. `Care_Closing_SMS_Sent__c` = true.

### Test 2 — Phone Case Transferred

1. Create a Case with Origin = `Phone`, Record Type = `Customer Care`, Account = Person Account in KSA, Language = `AR`
2. **Expected:** No SMS on creation (live case, no transfer yet)
3. Change the Case Owner to a different queue or user (simulating L1 transfer)
4. **Expected:** Opening SMS sent (Arabic). `Care_Opening_SMS_Sent__c` = true.
5. Update status to `Solved`
6. **Expected:** Closing SMS sent (Arabic). `Care_Closing_SMS_Sent__c` = true.

### Test 3 — Phone Case Resolved by L1 (No Transfer)

1. Create a Case with Origin = `Phone`, same account conditions
2. Solve the case directly without changing owner
3. **Expected:** No opening SMS, no closing SMS (opening SMS was never sent)

### Test 4 — Non-Eligible Cases (Negative Tests)

1. Create a case with Record Type ≠ Customer Care → **No SMS**
2. Create a case with Account Type = Business Account → **No SMS**
3. Create a case with Account Country ≠ KSA → **No SMS**

### Test 5 — Multiple Transfers (No Duplicate Opening SMS)

1. Create a Phone case, transfer owner (L1 → L2) → Opening SMS sent
2. Transfer owner again (L2 → L3) → **No second opening SMS** (`Care_Opening_SMS_Sent__c` already true)

### Test 6 — Re-Solve (No Duplicate Closing SMS)

1. Create an Email case → Opening SMS sent
2. Solve the case → Closing SMS sent
3. Reopen the case (change status away from Solved)
4. Solve the case again → **No second closing SMS** (`Care_Closing_SMS_Sent__c` already true)

### Monitoring

- **Backend logs:** Check for incoming `POST /agent/salesforce/send-sms` requests
- **Salesforce Debug Logs:** Setup → Debug Logs → monitor the Automated Process user for callout details and errors

---

## Items to Confirm

| # | Item | Action |
|---|------|--------|
| 1 | **Case Origin picklist values** | Confirm exact values: `Email`, `Web`, `Chat`, `Phone` — may differ in your org (e.g., `Live Chat`, `Messaging`, `API`) |
| 2 | **Record Type developer name** | Confirm `Customer_Care` is the correct `DeveloperName` for the Customer Care record type |
| 3 | **Account fields** | Confirm `IsPersonAccount` is the correct field for Person Account check. Confirm API name for Country of Registration (`Country_of_Registration__c` or other) |
| 4 | **Case_Language__c** | Confirm field exists on Case and picklist values are `AR` and `EN` |
| 5 | **"Solved" status value** | Confirm the exact picklist value is `Solved` (not `Resolved` or `Closed`) |
| 6 | **Production endpoint** | Confirm production URL: `https://api.tamara.co/agent/salesforce/send-sms` |
| 7 | **Production auth token** | Obtain production Bearer token with `ROLE_SYSTEM_SALESFORCE` |
| 8 | **Cross-object entry conditions** | Verify that `Account.IsPersonAccount` and `Account.Country_of_Registration__c` can be used in Flow entry conditions. If not, move them to Decision elements inside the flow. |
