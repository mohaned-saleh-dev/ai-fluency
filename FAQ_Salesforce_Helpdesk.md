# Salesforce Service Cloud — Agent FAQ Guide

*For Care Agents at Tamara | Last updated: March 27, 2026*

---

# Case Management

<details>
<summary><strong>How do I create a new case for an outbound call if one doesn't already exist?</strong></summary>

When you make an outbound call, Salesforce will automatically prompt you to link the voice call to an existing open case for that customer or partner. If no open cases exist, the system will automatically create a new case and link it to the voice call.

**You do not need to manually create a case.** The system handles it for you as part of the outbound call flow.

If a new case was not created, it usually means the customer already has an open case — the system linked your call to that existing case instead.

</details>

<details>
<summary><strong>How do I transfer a case to another team (e.g., Partner Team, Tech Team, Finance)?</strong></summary>

To transfer a case:

1. Open the case you want to transfer.
2. Make sure the case status is set to **"Working"**. If it is not, change the status to "Working" first — the transfer option will not appear otherwise.
3. Look for the **"Case Transfer"** button or component on the **right-hand side** of the case page.
4. Click "Case Transfer."
5. From the list of available teams/queues, select the team you want to transfer to (e.g., "PC L1 Email & Chat" for Partner Care, "CC KSA Tech Support" for Tech, etc.).
6. Confirm the transfer.

**Important:**
- If the case originated from a live chat, you **must end the chat session first** before transferring the case.
- If you are on a phone call, **disconnect the call first** before transferring.
- Always complete all notes and details on the case **before** you transfer, because you will not be able to edit the case after transfer.

</details>

<details>
<summary><strong>Why can't I edit a case, update its status, or send emails on it?</strong></summary>

This happens because you are **not the case owner**. In Salesforce, only the assigned case owner can edit a case, change its status, or send emails from it.

Common reasons you're not the owner:
- The case is still sitting in a **queue** and hasn't been assigned to you yet.
- You **escalated or transferred** the case before saving your changes, which moved ownership away from you.
- Another agent was assigned the case.

**To resolve:**
- If the case is in a queue, set your Omni-Channel status to "Online" and cases will be auto-assigned to you.
- If you need to edit a case that belongs to someone else, ask your team lead or an admin to reassign it to you.

</details>

<details>
<summary><strong>Why do I get the error "Oops...you don't have the necessary privileges to edit this record"?</strong></summary>

This error means you are **not the owner** of the case. Salesforce restricts editing permissions to the assigned case owner only.

**Common causes:**
- The case was transferred to another team or agent.
- The case is owned by a queue, not by you individually.
- You escalated the case, which transferred ownership.

**To fix:** Contact your team lead or admin to have the case reassigned to you if needed.

</details>

<details>
<summary><strong>Why do I get the error "Claim the case from queue before editing"?</strong></summary>

This error appears when you try to edit a case that is still owned by a **queue** rather than assigned to you personally. You must claim (be assigned) the case before you can work on it.

**To fix:**
1. Set your Omni-Channel status to **"Online."**
2. Cases from the queue will be **automatically assigned** to you by the system.
3. Once you are the assigned owner, you can edit the case, update its status, and close it.

**Note:** You cannot manually self-assign cases from a queue.

</details>

<details>
<summary><strong>How do I verify if a case has been successfully transferred to another team?</strong></summary>

After transferring a case, check these two things:

1. **Case Owner field:** The "Case Owner" field on the case record should now show the name of the **team or queue** you transferred it to, instead of your name.
2. **Case Events tab:** Navigate to the "Case Events" or "Case History" section on the case page. This logs all changes, including transfers and ownership updates, giving you a clear audit trail.

</details>

<details>
<summary><strong>Why is the "Case Transfer" option not appearing on a case?</strong></summary>

The "Case Transfer" button only appears when the case status is set to **"Working."**

**To fix:**
1. Open the case.
2. Change the case status to **"Working."**
3. Save the case.
4. The "Case Transfer" option should now appear on the right side of the case page.

Other statuses like "New," "Pending," or "Closed" typically hide the transfer functionality.

</details>

<details>
<summary><strong>How should I handle cases created from auto-reply emails or spam?</strong></summary>

For any case that comes from an auto-reply email or is clearly not related to Tamara's business:

1. **Close the case** immediately.
2. Select **"Spam"** as the Issue Type.

Do not leave these cases open or process them further. Using the "Spam" issue type consistently helps with accurate reporting.

</details>

<details>
<summary><strong>What should I do if a case I transferred to another team bounces back to me?</strong></summary>

This is a known issue that can happen, especially with Tech Team transfers. Follow these steps:

1. **Ensure the correct order:** Always disconnect the call or end the chat **first**, then transfer the case. Transferring while still on a call can cause the case to bounce back.
2. **Transfer after wrap-up:** Complete all case notes and wrap-up actions before initiating the transfer.
3. If the issue persists, post the **case number** and the **team you want it transferred to** in the Slack helpdesk channel. An admin will manually handle it.

</details>

<details>
<summary><strong>Can I edit a case comment after it has been submitted?</strong></summary>

**No.** In Salesforce, case comments **cannot be edited** once they are submitted. This is by design to maintain an accurate audit trail.

If you need to correct or add information, simply **add a new case comment** with the updated details. Do not attempt to edit previous entries.

</details>

<details>
<summary><strong>Why am I not receiving new cases even though I'm online?</strong></summary>

The most common reason is that you have reached your **maximum limit of assigned cases** (typically 100 pending tickets). The system will not assign new cases until your count is reduced.

**To fix:**
1. Go to your assigned cases list in Salesforce.
2. Filter for cases with a "Pending" status (e.g., "Pending on Partner," "Pending Customer").
3. **Close** any pending cases that no longer require your active follow-up.
4. Closing these cases frees up your capacity, and the system will start assigning new cases to you again.

**Important:** Closing a Salesforce case does **not** affect the dispute status in the CS Panel. The two systems are not linked for this purpose, so you can safely close SF cases without impacting disputes.

</details>

<details>
<summary><strong>What should I do if I have a pending case that I can't close but it's blocking new assignments?</strong></summary>

If a case is pending (e.g., waiting for a partner or customer response) and you cannot close it yet, but it is preventing you from getting new work:

1. Change the case status to **"Transferred to Tech"** (or another appropriate paused status). This puts the case in a "paused" state.
2. The system will now **route new cases** to you since the paused case no longer counts toward your active workload.
3. To return to the paused case later, use your case **views** at the top of the Salesforce page (e.g., "My Cases," "Cases Transferred to Tech").

</details>

<details>
<summary><strong>What is the correct case status to use when waiting for a customer's response?</strong></summary>

Set the case status to **"Closed."**

If the customer replies within **3 days**, the system will **automatically reopen** the case so you can continue working on it. You do not need to keep the case open while waiting.

</details>

<details>
<summary><strong>Why can't I merge two cases in Salesforce?</strong></summary>

The case merge feature is **currently not functional** in Salesforce. The admin team is working to enable it, but it is not available yet.

**Workaround:** If you have duplicate cases, close one of them with the status **"Merged"** and add the **other case's number** in a case comment. This links them for reference.

</details>

<details>
<summary><strong>Why can't I edit a case after I've escalated or transferred it?</strong></summary>

By design, agents **cannot edit cases after escalation or transfer**. This is intentional — the workflow requires you to complete **all actions and notes** before transferring.

**Always do this before transferring:**
1. Fill in all required case fields.
2. Add all relevant case comments and notes.
3. Attach any necessary files.
4. **Then** transfer or escalate.

</details>

<details>
<summary><strong>What should I do if a chat case is incorrectly assigned to another agent but I'm the one working on it?</strong></summary>

If you are actively handling a chat but the case shows another agent as the owner:

1. Contact your **team lead or admin** via the Slack helpdesk channel.
2. Provide the **case number** and explain that you are the one working on it.
3. The admin can **manually change the case owner** to your name, which will give you full edit access.

</details>

<details>
<summary><strong>Why are cases from abandoned calls not editable?</strong></summary>

Cases created for **abandoned calls** (calls where the customer disconnected before an agent answered) are **automatically closed** by the system. Once auto-closed, these cases become non-editable. You cannot transfer, update, or save changes on them. This is expected behavior.

</details>

<details>
<summary><strong>How do I add a note to a case if the option isn't working?</strong></summary>

If you are unable to add a note to a Salesforce case, **refresh the page** (press F5 or Ctrl+R). This resolves most temporary interface glitches. If the issue persists, try a hard refresh (Ctrl+Shift+R on Windows, Cmd+Shift+R on Mac).

</details>

---

# Login, Access & Troubleshooting

<details>
<summary><strong>How do I log in to Salesforce Service Cloud?</strong></summary>

You must log in to Salesforce through **JumpCloud** (your company's Identity Provider):

1. Open your **JumpCloud** application.
2. Find and click the **Salesforce Service Cloud** app.
3. JumpCloud will authenticate you and redirect you to Salesforce.

**Do not** try to log in directly at salesforce.com or login.salesforce.com — always go through JumpCloud.

</details>

<details>
<summary><strong>What should I do if I can't log in to Salesforce?</strong></summary>

Follow these troubleshooting steps in order:

1. **Clear your browser's cache and cookies** — Go to your browser settings, find "Clear browsing data," and clear cached images/files and cookies.
2. **Close your browser completely** — Close all tabs and windows, not just the Salesforce tab.
3. **Close JumpCloud** — If you have JumpCloud open in another tab or window, close it too.
4. **Reopen your browser** — Start fresh.
5. **Log in through JumpCloud** — Open JumpCloud and click the Salesforce app to log in.

If none of these work, report the issue in the **IT Helpdesk Slack channel** with a screenshot of any error messages.

</details>

<details>
<summary><strong>What should I do if I keep getting logged out of Salesforce randomly?</strong></summary>

Random logouts are almost always caused by having **multiple Salesforce tabs open** in your browser.

**Fix:**
- Make sure you only have **one Salesforce tab** open at all times.
- Opening multiple Salesforce tabs can disrupt your session and switch your status to offline.

If it still happens with one tab, clear your browser cache, close the browser entirely, and log back in through JumpCloud.

</details>

<details>
<summary><strong>How do I perform a hard refresh in Salesforce?</strong></summary>

A hard refresh forces your browser to reload everything from scratch, bypassing any cached data:

- **Windows / Linux:** Press **Ctrl + Shift + R**
- **Mac:** Press **Cmd + Shift + R**

This is the go-to fix for most display glitches, missing buttons, or UI issues in Salesforce.

</details>

<details>
<summary><strong>What are the general troubleshooting steps for any Salesforce issue?</strong></summary>

For almost any Salesforce problem (display issues, errors, missing features, connectivity problems), try these steps in order:

1. **Hard refresh** — Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac).
2. **Clear browser cache and cookies** — Go to browser settings and clear all browsing data.
3. **Close all Salesforce and JumpCloud tabs** — Make sure everything is shut down.
4. **Close and reopen your browser** — Not just the tabs, the entire browser application.
5. **Log back in through JumpCloud** — Always use JumpCloud as your entry point.
6. **Check browser permissions** — Make sure pop-ups and microphone access are allowed for the Salesforce domain.

If the issue continues after all of these, report it to the **IT Helpdesk Slack channel** with details and screenshots.

</details>

<details>
<summary><strong>How do I enable microphone and pop-up permissions for Salesforce?</strong></summary>

Many Salesforce features (especially phone/calls) require your browser to allow microphone access and pop-ups:

1. Open Google Chrome (recommended browser).
2. Navigate to your Salesforce page.
3. Click the **padlock icon** (or tune icon) in the address bar, to the left of the URL.
4. In the dropdown, find:
   - **Microphone** — Set to **"Allow"**
   - **Pop-ups and redirects** — Set to **"Allow"**
5. **Refresh the page** after changing these settings.

**Tip:** If calls or Omni-Channel are not working, try toggling these permissions off and then back on, then do a hard refresh. This resets the connection.

</details>

<details>
<summary><strong>How do I request Salesforce Care access if I only have Commercial Salesforce?</strong></summary>

If you can see Salesforce Commercial but not Salesforce Service Cloud (Care):

1. **Raise a ticket with IT** — Submit a formal request specifying that you need "Salesforce Care" (Service Cloud) access.
2. **Mention JumpCloud** — Tell IT that this access needs to be added to your JumpCloud profile.
3. **Specify queues** — If you need access to specific queues (e.g., TNS queues for AE and SA), include that in the request.
4. After IT confirms the change, **log out and log back in** for the new access to take effect.

</details>

<details>
<summary><strong>How can Team Leads get phone access for making outbound calls?</strong></summary>

Team Leads and SMEs who need Salesforce phone access (Genesys integration) must:

1. **Get Genesys access first** — Raise a ticket with IT requesting a Genesys user account.
2. **Request SF phone access** — Once Genesys access is confirmed, have your manager or admin request "Care SF phone access" from the Salesforce admin team.
3. The admin will enable phone features on your Salesforce profile.
4. After access is granted, **log out and log back in**, then check that your microphone and pop-ups are allowed.

</details>

<details>
<summary><strong>What should I do if I can't change my Omni-Channel status?</strong></summary>

If you are unable to select a status (like "Online" or "Task") in the Omni-Channel widget:

1. **Hard refresh** the page — Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac).
2. **Clear your browser cache** and cookies.
3. **Log out** of Salesforce completely.
4. **Close the browser** and reopen it.
5. **Log back in** through JumpCloud.

If the issue still persists, ask your admin to check your user configuration.

</details>

<details>
<summary><strong>What should I do if I can't view cases assigned to another team?</strong></summary>

If you get an access error when trying to view cases belonging to another team (e.g., Partner Care), it means your role does not have visibility into that team's cases.

**To fix:**
1. Contact your team lead or a Salesforce admin.
2. Explain which team's cases you need to view and why.
3. The admin can grant you the necessary access.
4. After access is granted, **log out and log back in** for the change to take effect.

</details>

<details>
<summary><strong>What should I do if I can't edit cases, add comments, or access files in Salesforce?</strong></summary>

If the Salesforce interface is not responding properly (cannot edit, add comments, or open files):

1. **Clear your browser cache and cookies.**
2. **Close the browser completely.**
3. **Restart your computer** (if clearing cache alone didn't help).
4. **Reopen the browser and log back in.**

This resolves most interface glitches caused by corrupted cached data.

</details>

---

# Phone & Calls

<details>
<summary><strong>What Omni-Channel status should I select to receive inbound calls?</strong></summary>

To receive inbound phone calls, you **must** set your Omni-Channel status to **"Online."**

**Do NOT** select "Outbound & Transfer Calls" if you want to receive inbound calls. That status is specifically for:
- Making outbound calls
- Receiving calls transferred from other agents

If you are on "Outbound & Transfer Calls," no new inbound calls will be routed to you.

</details>

<details>
<summary><strong>What should I do if I'm online but not receiving any calls?</strong></summary>

Follow these troubleshooting steps in order:

1. **Check your Omni-Channel status** — Make sure it is set to "Online" (not "Outbound & Transfer Calls" or any other status).
2. **Toggle your status** — Switch to "Offline," wait 10 seconds, then switch back to "Online."
3. **Check browser permissions:**
   - Microphone must be **allowed** for Salesforce.
   - Pop-ups must be **allowed** for Salesforce.
   - Try toggling both off and back on again, then hard refresh.
4. **Hard refresh** — Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac).
5. **Check Genesys** — Make sure the Genesys pop-up window is open and you are logged in.
6. **Close any extra Salesforce tabs** — Only keep one Salesforce tab open.
7. **Clear cache and restart browser** — If nothing else works, clear everything and start fresh.

</details>

<details>
<summary><strong>What should I do if I can't make outbound calls?</strong></summary>

If you are unable to make outbound calls:

1. **Hard refresh** the page — Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac).
2. **Check your microphone** — Ensure your mic is connected and browser permissions allow microphone access.
3. **Allow pop-ups** — The Genesys softphone often uses a pop-up window.
4. **Verify Genesys login** — Make sure you are logged into the Genesys pop-up that appears.
5. **Clear cache and restart** — If the above steps don't work, clear your browser cache, close and reopen the browser, and log back in.

</details>

<details>
<summary><strong>How do I transfer a customer to a survey after a phone call?</strong></summary>

The method depends on the call type:

**For callback calls (outbound):**
1. After finishing the conversation, locate the **"VC" (Voice Call)** component on the case page — it is usually highlighted in green.
2. Click on the VC component.
3. Find the **"Transfer to Survey"** option on the right side.
4. Click it. The customer will be transferred to the survey, and the call will close automatically.

**For outbound calls (manual dial):**
1. Before dialing, go to **Phone Wrap-up & Outbound** in Salesforce.
2. In the "Search Queues" field, select **"CC - Phone - Outbound"** queue.
3. Dial the customer's number on behalf of this queue.
4. When the call ends, the survey transfer buttons will appear correctly.
5. If you dialed without selecting a queue first, use the **"Blind Transfer"** button and select the survey queue.

**For inbound calls:**
- Close the call from the **Omni-Channel** widget. The system handles post-call surveys automatically.

**Note:** If the customer hangs up before you transfer to the survey, the survey will not be sent. This is normal behavior.

</details>

<details>
<summary><strong>Why did my call disconnect when I opened another case from the CS Panel?</strong></summary>

Clicking a case link in the CS Panel opens a **new Salesforce browser tab**. Having multiple Salesforce tabs open breaks your Omni-Channel connection and can drop your active call.

**To avoid this:**
1. **Do not click** the case link directly in the CS Panel.
2. Instead, **copy the case number** from the CS Panel.
3. Go to your **existing Salesforce tab** and paste the case number into the global search bar.
4. This keeps your Omni-Channel session active in a single tab.

*A system update is being implemented to replace the clickable link with a copy icon to prevent this issue.*

</details>

<details>
<summary><strong>Why wasn't a new case created when I made an outbound call?</strong></summary>

Salesforce tries to avoid creating duplicate cases. A new case will **not** be created if:

- The customer or merchant **already has an open case** linked to their phone number.
- The system found a match and linked your call to the **existing open case** instead.

**What to do:** Log your call details as a **case comment** on the existing case rather than expecting a new case.

</details>

<details>
<summary><strong>What should I do if Genesys says "Cannot communicate with Genesys Cloud"?</strong></summary>

This error is usually caused by browser or connection issues:

1. **Clear your browser cache and cookies.**
2. **Hard refresh** the Salesforce page — Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac).
3. **Check microphone permissions** — Click the padlock in the address bar and ensure microphone is set to "Allow."
4. **Check pop-ups** — Ensure pop-ups are allowed for Salesforce.
5. **Log out and log back in** — Close browser, reopen, and log in through JumpCloud.

</details>

<details>
<summary><strong>How do I make an outbound call without receiving incoming calls at the same time?</strong></summary>

If you are making a manual outbound call and want to prevent new inbound calls or callbacks from being routed to you:

1. **Before dialing**, change your Omni-Channel status to **"Outbound & Transfer Calls."**
2. Make your outbound call.
3. When you are done and ready to receive inbound calls again, switch your status back to **"Online."**

If your status is "Online" while making an outbound call, the system will continue routing new calls to you — this is expected behavior.

</details>

<details>
<summary><strong>How do I end a call if the standard "End Call" button isn't working?</strong></summary>

If you cannot end a call from the usual interface:

1. Navigate to the **"Phone Callback"** tab in Salesforce.
2. Try to end the call from there.
3. If that also doesn't work, try a hard refresh (Ctrl+Shift+R) — but note this may drop the call.

</details>

<details>
<summary><strong>Why are cases not being created when I answer calls from the Genesys tab?</strong></summary>

If you have the **Genesys tab open separately** in your browser and answer calls from there instead of from within Salesforce, cases will **not** be automatically created.

**Fix:**
1. **Close the Genesys tab** — Do not open Genesys in a separate browser tab.
2. **Only keep Salesforce open** — The Genesys integration works within Salesforce; you do not need a separate Genesys tab.
3. **Refresh your Salesforce tab** after closing Genesys.

Calls answered within Salesforce will automatically trigger case creation.

</details>

---

# Chat & Messaging

<details>
<summary><strong>Why did my chat session end automatically while I was working on it?</strong></summary>

Chat sessions are subject to an **inactivity timeout**. If you do not send any messages to the customer within the timeout period (approximately 4 minutes 30 seconds), the system will automatically end your participation in the chat.

**What happens next:**
- If another agent is available, the chat will be transferred to them.
- If no agents are available, the chat will be routed back to the chatbot.

**How to prevent this:**
- Always respond to the customer promptly — aim for responses within 2 minutes.
- If you need more time to research, send a quick message like "Please allow me a moment to look into this" to keep the session active.

</details>

<details>
<summary><strong>What should I do if I can't reply to a chat?</strong></summary>

If you suddenly cannot type or send a reply in a chat session, check the following:

1. **Customer ended the chat** — Look at the left side of the chat interface. If it says **"Ended by type: end user"**, the customer has left the conversation. You cannot reply after this.
2. **Interface glitch** — If the customer is still active but you can't type, **refresh the page** (F5 or Ctrl+R). This often fixes temporary display issues.

</details>

<details>
<summary><strong>How do I transfer a chat case to another team?</strong></summary>

**Important:** You must end the chat session **before** transferring the case.

1. Complete your conversation with the customer.
2. Click the **"End Chat"** button to formally close the chat session.
3. Navigate to the associated **Case record**.
4. Change the case status to **"Working"** (if it isn't already).
5. Use the **"Case Transfer"** button on the right side of the case page.
6. Select the target team/queue.
7. Confirm the transfer.

If you try to transfer while the chat is still active, some team options may not appear in the transfer list.

</details>

<details>
<summary><strong>Why do chats get stuck in "Waiting" status?</strong></summary>

Chats can get stuck in "Waiting" if there is a **connection issue** at the moment an agent tries to accept the chat.

**What happens:**
- The system will wait for the timeout period and then **reassign** the chat to another available agent.
- A case will **only be created** once the chat is successfully picked up by an agent.

**What to do:** If you see a stuck chat, do not worry — the system will handle the reassignment automatically. No manual action is needed.

</details>

<details>
<summary><strong>Is it normal to receive chats and emails at the same time?</strong></summary>

**Yes**, this is by design. Salesforce Omni-Channel is configured to route multiple work items to you simultaneously based on your capacity settings.

**Current capacity:**
- Up to **3 chats** at the same time
- Plus **1 email** at the same time

So you can have up to 4 work items at once. This is the expected workload.

</details>

<details>
<summary><strong>Why am I getting assigned new chats immediately after ending a previous one?</strong></summary>

Ending a chat session and changing the case status are **two separate actions** in Salesforce:

- **Ending the chat** makes you available for new chats in the Omni-Channel queue.
- **Updating the case status** (e.g., to "Closed") handles the case record.

So when you end a chat, the system immediately considers you available and may route a new chat to you — even if you haven't finished updating the previous case.

**Tip:** If you need time to wrap up, change your Omni-Channel status to **"Task"** or **"Offline"** before ending the chat. Finish your case notes, then switch back to "Online" when ready.

</details>

<details>
<summary><strong>How do I see all escalation options when transferring a chat case?</strong></summary>

The full list of escalation options (all Lines of Business teams) will **only appear after you end the chat session**. While the chat is still active, the transfer options are limited.

**Steps:**
1. Finish the customer conversation.
2. Click **"End Chat"** to close the chat session.
3. Go to the case record.
4. Now click **"Case Transfer"** — all team options should be visible.

</details>

<details>
<summary><strong>Are customer chat surveys currently active in Salesforce?</strong></summary>

**No**, customer chat surveys are **not live yet** in Salesforce Service Cloud. Customers will not receive a survey after a chat interaction, even if the closing message mentions one. This feature is still being set up.

</details>

---

# Email & Communication

<details>
<summary><strong>Which email address should I use to reply to customers from Salesforce?</strong></summary>

Always use the official **Tamara team email address** for your Line of Business (LOB):

- **Customer Care agents:** Use `Customer.care@tamara.co`
- **Partner Care agents:** Use `Partner.care@tamara.co`

**Never** use your personal corporate email address (e.g., yourname@tamara.co) to respond to customers. All customer communication must go through the official team email addresses.

</details>

<details>
<summary><strong>Why am I getting an error when trying to send an email from Salesforce?</strong></summary>

The most common causes are:

1. **Wrong sender email** — You may be trying to send from your personal email instead of the official Tamara email. Always use the team email (e.g., `Customer.care@tamara.co`).
2. **Email not verified** — Your agent email address may not be verified in Salesforce. Contact your admin to check and verify your email configuration.
3. **You're not the case owner** — You can only send emails from cases where you are the assigned owner.

</details>

<details>
<summary><strong>After resolving a dispute, do I need to send a manual email to the customer?</strong></summary>

**No.** When a dispute is resolved, Salesforce automatically sends a resolution email to the customer. The automated email is sufficient — you do **not** need to send an additional manual email.

</details>

<details>
<summary><strong>Can I send an email to a customer or merchant if there is no existing case?</strong></summary>

**No**, in the current Salesforce setup, you cannot send an email without an existing case. The system requires an active case to facilitate email communication.

**Workaround:** If you need to contact a merchant proactively and no case exists, make an **outbound phone call** — this will automatically create a new case. You can then use that case to send emails.

</details>

<details>
<summary><strong>What should I do if I'm online in the email queue but not receiving any emails?</strong></summary>

Follow these steps:

1. **Toggle your Omni-Channel status** — Switch from "Online" to "Offline," wait 10-15 seconds, then switch back to "Online."
2. **Log out and log back in** — Close your browser, reopen it, and log in through JumpCloud.
3. **Verify queue assignment** — Ask your team lead or admin to confirm you are correctly assigned to the email queue.

This sequence refreshes your connection to the queue and usually resolves the issue.

</details>

<details>
<summary><strong>What is the correct process for internal email escalations to the Care team?</strong></summary>

When a Tamara internal employee needs to escalate a customer or partner email to the Care team:

1. **Forward** the entire email thread to: **`care.escalations@tamara.co`**
2. **Do not** CC this address into an ongoing thread — always forward.

Forwarding creates a clean new case in Salesforce, clearly marked as an internal escalation. This prevents agents from confusing the internal sender with the customer.

</details>

---

# Workflows & Processes

<details>
<summary><strong>How do "Pending" and "Closed" statuses work differently from Zendesk?</strong></summary>

There are key differences between Salesforce and Zendesk statuses:

1. **Pending cases stay with the agent** — Unlike Zendesk, when you set a case to "Pending" (e.g., "Pending on Partner"), the case stays assigned to you. It does **not** go back to the queue. *(The team is working to change this behavior to match Zendesk.)*

2. **"Closed" is not terminal** — In Salesforce, "Closed" is equivalent to "Solved" in Zendesk. A closed case **can be reopened** if the customer replies within 3 days.

3. **Closing a case does not affect disputes** — Closing a Salesforce case does **not** impact the dispute status in the CS Panel. The systems are not linked for this, so you can safely close cases.

</details>

<details>
<summary><strong>Do changes I make to a dispute ticket in Salesforce automatically update CS Hub?</strong></summary>

**No.** There is no live two-way integration between Salesforce and CS Hub for dispute data. If you change the "Issue Type" on a dispute ticket in Salesforce, it will **not** update the claim reason in CS Hub.

If the claim reason needs to be corrected in CS Hub, you must do it **manually** by going directly into CS Hub and updating it there.

</details>

<details>
<summary><strong>What Omni-Channel status should I use for short breaks?</strong></summary>

The "Away" status is **not currently implemented** in Salesforce. For short breaks (e.g., 5-minute breaks):

- Use the **"Task"** status in Omni-Channel.

This will pause new work routing to you while you are on break. Switch back to "Online" when you return.

</details>

<details>
<summary><strong>Is "Nida Masoud" a real person or an automated system?</strong></summary>

**"Nida Masoud" is a system user / automation.** Any follow-up messages or reminders sent under this name are generated automatically by the system, not by a human agent. You do **not** need to manually follow up on tickets where "Nida" has already sent a reminder.

</details>

<details>
<summary><strong>How many cases can I work on at the same time?</strong></summary>

The standard workload capacity is **3 active cases** (in "Working" status) at the same time. You should not receive more than 3 unless they are reopened cases returning to you.

If you are only receiving 1 case at a time when you should receive more, ask your admin to check your capacity settings.

</details>

<details>
<summary><strong>When is the correct time to escalate a case to another team?</strong></summary>

Always escalate **after wrap-up**:

1. **Finish the call or chat** with the customer first.
2. **Complete all case notes** and fill in all required fields.
3. **Disconnect the call** or **end the chat session**.
4. **Then** transfer or escalate the case.

Escalating while still on a call or with an active chat can cause the case to bounce back to you or lose the transfer.

</details>

<details>
<summary><strong>Why can't I save a case as "Pending Customer" if it was previously closed?</strong></summary>

Salesforce does not allow you to change a case status from **"Closed" to "Pending Customer."** The case must be in an active status (like "New" or "Working") for you to set it to "Pending Customer."

If a closed case needs to go back to pending, it would first need to be reopened (typically triggered by a customer reply within the 3-day window).

</details>

<details>
<summary><strong>If a case escalation failed due to a system issue, do I need to re-escalate?</strong></summary>

**Yes.** The system will not automatically re-escalate cases that failed due to a system issue. You must manually go back to the affected cases and initiate the escalation again once the issue has been resolved.

</details>

<details>
<summary><strong>How do I escalate a merchant email case to the Onboarding team if "Onboarding" isn't in the transfer list?</strong></summary>

The "Onboarding" option is not directly available for Customer Care agents. Instead:

1. Transfer the case to the **Partner Care (PC)** queue.
2. Partner Care will then route it to the Product Onboarding (PO) team.

This is the correct escalation path for merchant-related onboarding issues.

</details>

---
