# Case SMS Notification — Salesforce Setup Guide

**What:** Two Record-Triggered Flows that send SMS notifications via the deployed `CaseSMSNotification` Apex class.  
**Environment:** Sandbox (TamaraUAT)  
**Pre-requisites already done:** Remote Site Setting + Apex class (`CaseSMSNotification`) + test class deployed.

---

## SMS Logic Summary

| SMS | When it fires | Sends once? |
|-----|--------------|-------------|
| **Case Opened** | Status changes FROM `New` TO anything other than `Closed` | Yes — only on the first transition out of `New` |
| **Case Closed** | Status changes TO `Closed` | Once per close (fires again if case reopens then re-closes) |

---

## FLOW 1: CaseSMS — Case Opened Notification

### 1.1 — Navigate to Flow Builder

1. Go to **Salesforce Setup** (gear icon → Setup)
2. In the **Quick Find** box (left sidebar), type `Flows`
3. Click **Flows** under Process Automation
4. Click the **New Flow** button
5. Select **Record-Triggered Flow**
6. Click **Create**

### 1.2 — Configure the Start Element

The "Configure Start" panel opens on the right side.

**Select Object:**
1. Click the **Object** search box
2. Type `Case`
3. Select **Case** from the dropdown

**Configure Trigger:**
1. Select **A record is updated**

**Set Entry Conditions:**
1. Set **Condition Requirements** to **All Conditions Are Met (AND)**
2. Add **Condition 1:**
   - Click the **Field** box → type `Status` → select **Status**
   - Operator: **Does Not Equal**
   - Value: click the **Value** box → type `New` → select **New**
3. Click **+ Add Condition**
4. Add **Condition 2:**
   - Field: **Status**
   - Operator: **Does Not Equal**
   - Value: **Closed**

**Optimize Flow:**
1. Under "Optimize the Flow for", select **Actions and Related Records**

**When to Run:**
1. Make sure **After the record is saved** is selected (it should be the default since you chose "Actions and Related Records")

Click **Done**.

### 1.3 — Add the "Run Asynchronously" Path

After clicking Done, you'll see the flow canvas with a **Start** element and an **End** element.

1. Click the **+** icon on the connector line between Start and End
2. In the menu that appears, look for **"Run Asynchronously"** (it may show as a path option or a scheduled path)
3. Click it to add the async path

> **Why async?** The Apex class makes an HTTP callout, which requires an asynchronous context.

All the following elements go on this **async path**.

### 1.4 — Add a Decision: "Was Previous Status New?"

On the async path, click the **+** icon → select **Decision**.

**Configure the Decision:**
1. **Label:** `Was Previous Status New`
2. **API Name:** `Was_Previous_Status_New` (auto-fills)

**First Outcome (rename from "Outcome 1"):**
1. **Label:** `Yes_Was_New`
2. Under **Condition Requirements:** All Conditions Are Met
3. **Resource:** click the search box → type `Prior` → select `{!$Record__Prior.Status}`
4. **Operator:** **Equals**
5. **Value:** type `New` → select **New**

**Default Outcome:**
1. Click on the **Default Outcome** at the bottom
2. Rename the label to `No_Skip`

Click **Done**.

### 1.5 — Add a Decision: "Check Language"

On the **Yes_Was_New** path (the one coming out of the first outcome), click **+** → **Decision**.

1. **Label:** `Check Language`
2. **API Name:** `Check_Language`

**First Outcome:**
1. **Label:** `Arabic`
2. **Resource:** `{!$Record.Case_Language__c}`
3. **Operator:** **Equals**
4. **Value:** `AR`

**Default Outcome:**
1. Rename to `English`

Click **Done**.

### 1.6 — Create a Text Variable for SMS Text

Before adding the assignments, you need a variable to store the SMS message.

1. In the **Toolbox** panel on the left side of Flow Builder, click **New Resource**
2. **Resource Type:** Variable
3. **API Name:** `SMSText`
4. **Data Type:** Text
5. Leave "Available for Input" and "Available for Output" unchecked
6. Click **Done**

### 1.7 — Add Assignment: Set Arabic SMS Text

On the **Arabic** path, click **+** → **Assignment**.

1. **Label:** `Set SMS Text Arabic`
2. **API Name:** `Set_SMS_Text_Arabic`
3. In the assignment rows:
   - **Variable:** click the search box → find and select `{!SMSText}`
   - **Operator:** **Equals**
   - **Value:** paste this exactly:

```
تم استلام طلبك (رقم الحالة #{!$Record.CaseNumber}) وهو قيد المراجعة من قبل فريقنا. سنقوم بتحديثك في أقرب وقت ممكن.
```

Click **Done**.

### 1.8 — Add Assignment: Set English SMS Text

On the **English** path (default outcome), click **+** → **Assignment**.

1. **Label:** `Set SMS Text English`
2. **API Name:** `Set_SMS_Text_English`
3. Assignment row:
   - **Variable:** `{!SMSText}`
   - **Operator:** **Equals**
   - **Value:** paste this exactly:

```
Your request (Case #{!$Record.CaseNumber}) has been received and is being reviewed by our team. We'll update you as soon as possible.
```

Click **Done**.

### 1.9 — Add Action: Send SMS

After both the Arabic and English assignment paths, they should merge back together. On the merged path (or after each assignment if they haven't auto-merged), click **+** → **Action**.

1. In the action search box, type `Send Case SMS`
2. Select **Send Case SMS Notification** (this is the Apex invocable method you deployed)
3. **Label:** `Send SMS`
4. **API Name:** `Send_SMS`

**Set the input values:**

| Input Parameter | Value |
|----------------|-------|
| **Case ID** | `{!$Record.Id}` |
| **Customer ID** | `{!$Record.AccountId}` |
| **SMS Text** | `{!SMSText}` |

To set each value: click on the input field → search/select the appropriate resource from the picker.

Click **Done**.

### 1.10 — Save and Activate

1. Click **Save** (top-right)
2. **Flow Label:** `CaseSMS - Case Opened Notification`
3. **Flow API Name:** `CaseSMS_Case_Opened_Notification` (auto-fills)
4. **Description (optional):** `Sends SMS when a case status first changes from New to a non-Closed status`
5. Click **Save**
6. Click **Activate** (top-right)
7. Confirm activation

### Flow 1 Visual Summary

```
START (Case updated, Status ≠ New AND Status ≠ Closed)
  │
  └─ [Run Asynchronously]
       │
       ▼
     Decision: Was $Record__Prior.Status = "New"?
       ├─ YES ──▶ Decision: Case_Language__c = "AR"?
       │            ├─ Arabic ──▶ Set SMSText = Arabic message
       │            └─ English ─▶ Set SMSText = English message
       │                              │
       │                              ▼
       │                    Action: Send Case SMS Notification
       │                      • Case ID = $Record.Id
       │                      • Customer ID = $Record.AccountId
       │                      • SMS Text = {!SMSText}
       │
       └─ NO ───▶ (End — do nothing)
```

---

## FLOW 2: CaseSMS — Case Closed Notification

### 2.1 — Navigate to Flow Builder

1. Go back to **Setup → Quick Find → Flows**
2. Click **New Flow**
3. Select **Record-Triggered Flow**
4. Click **Create**

### 2.2 — Configure the Start Element

**Select Object:**
1. Search and select **Case**

**Configure Trigger:**
1. Select **A record is updated**

**Set Entry Conditions:**
1. **Condition Requirements:** All Conditions Are Met (AND)
2. **Condition 1:**
   - Field: **Status**
   - Operator: **Equals**
   - Value: **Closed**

**Optimize Flow:**
1. Select **Actions and Related Records**

Click **Done**.

### 2.3 — Add the "Run Asynchronously" Path

Same as Flow 1 Step 1.3 — click **+** → **Run Asynchronously**.

### 2.4 — Add a Decision: "Was Previously Not Closed?"

On the async path, click **+** → **Decision**.

1. **Label:** `Was Previously Not Closed`
2. **API Name:** `Was_Previously_Not_Closed`

**First Outcome:**
1. **Label:** `Yes_Status_Changed`
2. **Resource:** `{!$Record__Prior.Status}`
3. **Operator:** **Does Not Equal**
4. **Value:** `Closed`

**Default Outcome:**
1. Rename to `No_Skip`

Click **Done**.

### 2.5 — Add a Decision: "Check Language"

On the **Yes_Status_Changed** path, click **+** → **Decision**.

1. **Label:** `Check Language`
2. **API Name:** `Check_Language`

**First Outcome:**
1. **Label:** `Arabic`
2. **Resource:** `{!$Record.Case_Language__c}`
3. **Operator:** **Equals**
4. **Value:** `AR`

**Default Outcome:**
1. Rename to `English`

Click **Done**.

### 2.6 — Create a Text Variable

Same as Flow 1 Step 1.6:
1. **Toolbox → New Resource → Variable**
2. API Name: `SMSText`
3. Data Type: Text
4. Click **Done**

### 2.7 — Add Assignment: Set Arabic SMS Text

On the **Arabic** path, click **+** → **Assignment**.

1. **Label:** `Set SMS Text Arabic`
2. **API Name:** `Set_SMS_Text_Arabic`
3. Assignment row:
   - **Variable:** `{!SMSText}`
   - **Operator:** **Equals**
   - **Value:**

```
تم حل طلبك (رقم الحالة #{!$Record.CaseNumber}). شكراً لتواصلك مع تمارا.
```

Click **Done**.

### 2.8 — Add Assignment: Set English SMS Text

On the **English** path, click **+** → **Assignment**.

1. **Label:** `Set SMS Text English`
2. **API Name:** `Set_SMS_Text_English`
3. Assignment row:
   - **Variable:** `{!SMSText}`
   - **Operator:** **Equals**
   - **Value:**

```
Your request (Case #{!$Record.CaseNumber}) has been resolved. Thank you for contacting Tamara.
```

Click **Done**.

### 2.9 — Add Action: Send SMS

After both paths merge, click **+** → **Action**.

1. Search for `Send Case SMS`
2. Select **Send Case SMS Notification**
3. **Label:** `Send SMS`
4. **API Name:** `Send_SMS`

**Input values:**

| Input Parameter | Value |
|----------------|-------|
| **Case ID** | `{!$Record.Id}` |
| **Customer ID** | `{!$Record.AccountId}` |
| **SMS Text** | `{!SMSText}` |

Click **Done**.

### 2.10 — Save and Activate

1. Click **Save**
2. **Flow Label:** `CaseSMS - Case Closed Notification`
3. **Flow API Name:** `CaseSMS_Case_Closed_Notification`
4. **Description (optional):** `Sends SMS when a case status changes to Closed`
5. Click **Save**
6. Click **Activate**

### Flow 2 Visual Summary

```
START (Case updated, Status = Closed)
  │
  └─ [Run Asynchronously]
       │
       ▼
     Decision: Was $Record__Prior.Status ≠ "Closed"?
       ├─ YES ──▶ Decision: Case_Language__c = "AR"?
       │            ├─ Arabic ──▶ Set SMSText = Arabic message
       │            └─ English ─▶ Set SMSText = English message
       │                              │
       │                              ▼
       │                    Action: Send Case SMS Notification
       │                      • Case ID = $Record.Id
       │                      • Customer ID = $Record.AccountId
       │                      • SMS Text = {!SMSText}
       │
       └─ NO ───▶ (End — do nothing)
```

---

## TESTING

### Test 1 — Case Opened SMS
1. Create a Case (status = `New`)
2. Change status to `Working` (or any non-Closed status)
3. **Expected:** SMS sent with "case received" message
4. Change status again (e.g. to `Pending Customer`)
5. **Expected:** No second SMS (prior status is no longer `New`)

### Test 2 — Case Closed SMS
1. Using the same case, change status to `Closed`
2. **Expected:** SMS sent with "case resolved" message

### Test 3 — Immediate Resolution
1. Create a new Case (status = `New`)
2. Change status directly to `Closed`
3. **Expected:** NO "case opened" SMS (Closed is filtered out by Flow 1)
4. **Expected:** YES "case closed" SMS (Flow 2 triggers)

### Where to Check
- **Backend logs** for `POST /agent/salesforce/send-sms` requests
- **Salesforce Debug Logs:** Setup → Debug Logs → add the Automated Process user to see callout details

---

## REFERENCE

| Item | Value |
|------|-------|
| **Apex Class** | `CaseSMSNotification` (already deployed) |
| **Endpoint** | `POST https://api-staging.tamara.co/agent/salesforce/send-sms` |
| **Payload** | `{ "case_id": "<Record.Id>", "customer_id": "<Record.AccountId>", "text": "<SMS body>" }` |
| **Remote Site Setting** | `Tamara_Backend_SMS` (already created) |
| **Flow 1** | `CaseSMS - Case Opened Notification` |
| **Flow 2** | `CaseSMS - Case Closed Notification` |
