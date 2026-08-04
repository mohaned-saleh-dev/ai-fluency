# Care roles — AiQ scenario review

**Meeting purpose:** validate two draft assessment scenarios with the people who actually do the work, and collect the raw material (real stories, real AI outputs) needed to finish them. This is not an evaluation — no one's answers are scored.

**Attending:** Customer Support Trainer · Content Specialist (Support) · Quality Advisor (QA)

---

## How to run the 30 minutes

| Time | What happens |
| --- | --- |
| 0–5 min | Frame it: we're building a 10-minute AI-fluency assessment for Care. Not a test of you. We need your work represented accurately. |
| 5–15 min | The real story + the real artifact (see questions below) |
| 15–25 min | Read the draft scenario aloud → "Does this happen to you? What's wrong with it?" |
| 25–30 min | The asks: documents, permission, pilot names |

> For QA: they have no written answers yet, so use their full slot for the baseline questions at the bottom of this page instead of scenario validation.

---

## Scenario 1 — Trainer

### "Go-live on Wednesday"

**The situation**
A new feature ships Friday and you're delivering the training to a cohort of agents on Wednesday. The request landed with a tight deadline and Training Design is still updating the deck, so you have the launch comms and the KB article. You're planning to use ChatGPT to turn the release notes into a session outline, a few knowledge checks, and a role-play.

**Why it matters**
These agents go live on the feature right after your session. If they leave without practical confidence — or with anything that doesn't match current operational reality — they give customers wrong information, escalations climb, and it traces back to the training.

**The twist** *(introduced mid-conversation, never upfront)*
The outline comes back clean and the quiz looks fine. But two answers describe the old refund window — the model blended the pasted release notes with its own assumptions, and the KB article was updated last week with a different SLA. An agent in the room is the one who notices.

**Team norms question**
If trainers across Care start turning release notes and SOPs into training material with AI, what should every trainer verify before it reaches a cohort — and what should never be pasted into the tool?

**Follow-up probes**

- What would you actually paste in — and what would you tell it about who's in the room?
- It looks solid at a glance. What would you check before you deliver it?
- Who hears that the material was out of date — you, Training Design, or the process owner?

---

## Scenario 2 — Content Specialist

### "Incident comms tonight"

**The situation**
A payment issue is hitting a segment of customers. You need a customer notification (push and in-app), a macro for agents working the queue, and an updated Help Center article — before the queue floods. You're planning to draft all three with ChatGPT from the incident summary in the Jira ticket.

**Why it matters**
This reaches customers at scale and every agent on the queue at once. A detail that shouldn't be public, a claim that isn't compliant, or a macro that contradicts the Help Center article becomes a bigger problem than the incident itself.

**The twist** *(introduced mid-conversation, never upfront)*
The draft is on-brand and reads well. But the customer push names a specific technical cause and a fix time Engineering hasn't confirmed — and the Arabic version promises something subtly different about compensation than the English one.

**Team norms question**
If content specialists across Care draft customer-facing comms with AI, what has to be checked before publish — and what still goes through Compliance and Legal no matter how tight the deadline is?

**Follow-up probes**

- What would you give the tool first — the ticket, the tone-of-voice rules, the approved terminology?
- It's on-brand and reads clean. What would you check before it's scheduled?
- Who signs this off when the deadline is tonight, and what do you do if they're not available?

---

## Questions for all three roles

1. **Walk me through the last time this actually went wrong.** What happened, who caught it, what did it cost? *(Needs a specific recent incident, not a general pattern.)*
2. **Show me a real AI output you didn't trust — or one you almost shipped.** Pull it up now; send it after.
3. **If AI handed you something confidently wrong tomorrow, what would the wrongness look like?**
4. **When the deadline is tonight, which control is the first to get skipped?**
5. **Think of your strongest person and your weakest. What does the strong one do that the weak one doesn't** — behaviourally, not personality?
6. **What should never be pasted into an AI tool in your work, and who decides that today?**
7. **Where does the handoff break — who owns the output once it leaves you?**

**Closing question for each person:** *Would you take a ten-minute assessment like this yourself, and what would make you distrust the result?*

---

## Open items to settle in the meeting

**Trainer — does the scenario match the real job?**
The draft assumes trainers build their own material under deadline pressure, but the questionnaire says instructional designers own material creation. Ask directly: *when the deadline is tight and Design hasn't finished the deck, do you build your own material, and do you use AI to do it?*

- If **yes** → the scenario ships as written.
- If **no** → switch to the delivery-side version: an agent asks a mid-session question the deck doesn't cover, the trainer reaches for ChatGPT live, and it confidently contradicts the current SOP.

**Content — two assumptions to confirm**

- That Engineering confirms fix times before they're published to customers.
- That Arabic and English versions can drift apart in meaning.

---

## What to collect before we leave

- [ ] Two or three real AI outputs that were wrong or nearly shipped (anonymised)
- [ ] The QA scorecard / rubric document
- [ ] The Care tone-of-voice SOP draft
- [ ] A sample KB article and a sample macro
- [ ] Explicit permission to base scenarios on anonymised real incidents
- [ ] Two or three pilot participant names per role

**Follow-up:** send each person the revised scenario within 24 hours and ask for a yes/no on whether it's realistic.

---

## QA — baseline questions (not yet answered)

1. What exactly do they review — tickets, calls, chats? Against what rubric?
2. How many do they get through in a day, and how are the ones they review chosen?
3. After they score something, what happens — coaching, a report, a performance flag?
4. How do they handle disagreement when an agent pushes back on a score?
5. What makes QA hard or contentious here?
6. Is any of the scoring or trend-spotting automated today?

Once these are answered, the QA scenario follows the same five-beat pattern as the two above.

---

## Reference — the five beats every scenario shares

| Beat | Purpose |
| --- | --- |
| A deliverable under deadline | Real time pressure, so answers reflect real behaviour |
| AI already in the loop | Not "would you use AI" but "you're about to — what now?" |
| Stakes with your name on it | Someone downstream acts on the output |
| A twist: clean, confident, wrong | Catchable only by going back to the source |
| Team norms close | One rule for everyone, one hard data boundary |
