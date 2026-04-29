#!/usr/bin/env python3
"""
Generate an FAQ guide from Slack helpdesk conversations using Gemini.
Processes conversations in batches, identifies Q&A pairs, validates with
Salesforce knowledge, and produces a Notion-compatible toggle-header document.
"""

import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

sys.stdout.reconfigure(line_buffering=True)
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
INPUT_FILE = "slack_extract_care-salesforce-helpdesk_20260327.json"
BATCH_SIZE = 40

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)


def load_conversations():
    """Load and format conversations with threads."""
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    conversations = []
    for msg in data["messages"]:
        replies = msg.get("thread_replies", [])
        if not replies:
            if "?" in msg.get("text", "") or any(
                kw in msg.get("text", "").lower()
                for kw in ["how", "can i", "cannot", "can't", "issue", "help",
                           "problem", "unable", "error", "stuck", "what do"]
            ):
                conversations.append({
                    "question_by": msg.get("user_name", msg["user"]),
                    "question": msg.get("text", ""),
                    "replies": [],
                })
            continue

        conversations.append({
            "question_by": msg.get("user_name", msg["user"]),
            "question": msg.get("text", ""),
            "replies": [
                {
                    "from": r.get("user_name", r["user"]),
                    "text": r.get("text", ""),
                }
                for r in replies
            ],
        })

    return conversations


def format_batch_for_prompt(batch, batch_num, total_batches):
    """Format a batch of conversations into a prompt-ready string."""
    lines = []
    for i, conv in enumerate(batch, 1):
        lines.append(f"--- Conversation {i} ---")
        lines.append(f"QUESTION by {conv['question_by']}: {conv['question']}")
        if conv["replies"]:
            for r in conv["replies"]:
                lines.append(f"  REPLY by {r['from']}: {r['text']}")
        else:
            lines.append("  (No replies)")
        lines.append("")
    return "\n".join(lines)


EXTRACTION_PROMPT = """\
You are an expert at analyzing helpdesk conversations for a Salesforce Service Cloud
system used by customer care agents at a company called Tamara (a buy-now-pay-later
fintech company). The company recently migrated to Salesforce from a previous system.

Below are {count} helpdesk conversations from a Slack channel where agents ask
questions about how to use Salesforce. Admins and team leads typically answer in
the thread replies.

YOUR TASK:
1. Read every conversation carefully.
2. Extract question-answer pairs where:
   - The question is about how to use Salesforce (system usage, navigation, processes)
   - An answer was provided in the replies (by admins, team leads, or knowledgeable colleagues)
3. SKIP conversations that are:
   - Bug reports with no resolution
   - Conversations where the answer was unclear or incomplete
   - Off-topic or purely social messages
   - Specific to a single case/customer (not generalizable)
4. For each valid Q&A pair, output JSON with these fields:
   - "question_raw": The original question as asked
   - "topic": One of: "Case Management", "Email & Communication", "Chat & Messaging",
     "Phone & Calls", "Login & Access", "System Navigation", "Workflows & Processes",
     "Customer Information", "Reporting & Queues", "Other"
   - "question_rewritten": Rewrite as a clear FAQ question from agent perspective
     (e.g., "How do I...?", "What should I do when...?")
   - "answer_raw": The answer as given in the thread
   - "answer_validated": A validated, corrected, step-by-step answer using your deep
     Salesforce Service Cloud knowledge. Fix any inaccuracies. Make it detailed and
     beginner-friendly. Use numbered steps where appropriate.
   - "confidence": "high" if answer was clearly given and correct, "medium" if you
     had to supplement significantly, "low" if mostly your own knowledge

Output ONLY a JSON array of objects. No markdown, no commentary.
If no valid Q&A pairs exist in this batch, output an empty array: []

CONVERSATIONS:
{conversations}
"""

UNANSWERED_PROMPT = """\
You are a Salesforce Service Cloud expert helping care agents at Tamara
(a buy-now-pay-later fintech company) who recently migrated to Salesforce.

Below are helpdesk questions from agents that were NOT answered in the Slack channel.
Using your deep Salesforce knowledge, provide answers to the ones you CAN answer
confidently. Skip any that are too specific to Tamara's custom setup to answer generically.

For each question you can answer, output JSON with:
- "question_raw": The original question
- "topic": One of: "Case Management", "Email & Communication", "Chat & Messaging",
  "Phone & Calls", "Login & Access", "System Navigation", "Workflows & Processes",
  "Customer Information", "Reporting & Queues", "Other"
- "question_rewritten": Clear FAQ question from agent perspective
- "answer_validated": Detailed, step-by-step answer using Salesforce best practices
- "confidence": "medium" or "low"

Output ONLY a JSON array. No markdown, no commentary.

UNANSWERED QUESTIONS:
{questions}
"""


def extract_qa_pairs(conversations):
    """Process conversations in batches through Gemini to extract Q&A pairs."""
    all_pairs = []
    batches = [
        conversations[i : i + BATCH_SIZE]
        for i in range(0, len(conversations), BATCH_SIZE)
    ]
    total = len(batches)

    print(f"Processing {len(conversations)} conversations in {total} batches...")

    for batch_num, batch in enumerate(batches, 1):
        print(f"  Batch {batch_num}/{total} ({len(batch)} conversations)...")
        conv_text = format_batch_for_prompt(batch, batch_num, total)
        prompt = EXTRACTION_PROMPT.format(count=len(batch), conversations=conv_text)

        for attempt in range(3):
            try:
                response = model.generate_content(prompt)
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1]
                    if text.endswith("```"):
                        text = text[: text.rfind("```")]
                pairs = json.loads(text)
                all_pairs.extend(pairs)
                print(f"    -> Extracted {len(pairs)} Q&A pairs")
                break
            except json.JSONDecodeError as e:
                print(f"    Retry {attempt + 1}: JSON parse error - {e}")
                if attempt == 2:
                    print(f"    Skipping batch {batch_num} after 3 failures")
            except Exception as e:
                print(f"    Retry {attempt + 1}: {e}")
                time.sleep(5)

        time.sleep(2)

    return all_pairs


def handle_unanswered(conversations):
    """Use Gemini's Salesforce knowledge to answer unanswered questions."""
    unanswered = [
        c for c in conversations
        if not c["replies"]
        and len(c["question"].strip()) > 10
    ]

    if not unanswered:
        return []

    print(f"\nProcessing {len(unanswered)} unanswered questions...")
    questions_text = "\n".join(
        f"{i}. {q['question']}" for i, q in enumerate(unanswered, 1)
    )
    prompt = UNANSWERED_PROMPT.format(questions=questions_text)

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[: text.rfind("```")]
        pairs = json.loads(text)
        print(f"  -> Answered {len(pairs)} previously unanswered questions")
        return pairs
    except Exception as e:
        print(f"  Error processing unanswered questions: {e}")
        return []


def deduplicate_and_organize(all_pairs):
    """Deduplicate similar questions and organize by category."""
    prompt = f"""\
You are organizing an FAQ guide. Below are {len(all_pairs)} Q&A pairs extracted from
a Salesforce helpdesk channel. Many are duplicates or very similar.

YOUR TASK:
1. Group similar questions together and keep the BEST version of each.
2. If the same answer applies to multiple question phrasings, keep each question
   variation as a SEPARATE FAQ entry (but with the same/similar answer).
3. Organize into exactly these categories (drop any that have 0 entries):
   - "Case Management" (handling cases, statuses, assignments, claims, escalations)
   - "Email & Communication" (sending emails, templates, email issues)
   - "Chat & Messaging" (Omni-Channel chat, live chat, messaging)
   - "Phone & Calls" (call handling, phone channel, CTI)
   - "Login & Access" (login issues, JumpCloud SSO, permissions, queues)
   - "System Navigation" (finding things in SF, UI questions, dashboards)
   - "Workflows & Processes" (refunds, payments, partner issues, SOPs)
   - "Customer Information" (looking up customers, account details, orders)
4. Target 40-55 total FAQ entries.
5. Every answer must be detailed, step-by-step, dumbed-down, and beginner-friendly.
   Use numbered steps. Assume the agent knows nothing about Salesforce.
6. Validate all answers against Salesforce Service Cloud best practices.
   Fix any inaccuracies.

Output a JSON object with this structure:
{{
  "categories": [
    {{
      "name": "Category Name",
      "faqs": [
        {{
          "question": "How do I ...?",
          "answer": "Step-by-step answer..."
        }}
      ]
    }}
  ]
}}

Output ONLY the JSON. No markdown, no commentary.

Q&A PAIRS:
{json.dumps(all_pairs, indent=2)}
"""

    print("\nOrganizing and deduplicating into final FAQ structure...")

    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[: text.rfind("```")]
            result = json.loads(text)
            total_faqs = sum(len(c["faqs"]) for c in result["categories"])
            print(f"  -> Organized into {len(result['categories'])} categories, {total_faqs} FAQs")
            return result
        except json.JSONDecodeError as e:
            print(f"  Retry {attempt + 1}: JSON parse error - {e}")
        except Exception as e:
            print(f"  Retry {attempt + 1}: {e}")
            time.sleep(5)

    return None


def generate_notion_markdown(faq_data):
    """Generate Notion-compatible markdown with toggle headers."""
    lines = []
    lines.append("# Salesforce Helpdesk FAQ Guide")
    lines.append("")
    lines.append("> **For Care Agents** | Generated from real helpdesk questions")
    lines.append(f"> Last updated: {datetime.now().strftime('%B %d, %Y')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for cat in faq_data["categories"]:
        lines.append(f"## {cat['name']}")
        lines.append("")

        for faq in cat["faqs"]:
            question = faq["question"].strip()
            answer = faq["answer"].strip()
            lines.append(f"<details>")
            lines.append(f"<summary><strong>{question}</strong></summary>")
            lines.append("")
            lines.append(answer)
            lines.append("")
            lines.append("</details>")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_notion_toggle_markdown(faq_data):
    """Generate Notion-native toggle format (using callout-style for import)."""
    lines = []
    lines.append("# Salesforce Helpdesk FAQ Guide")
    lines.append("")
    lines.append("*For Care Agents — Generated from real helpdesk questions*")
    lines.append(f"*Last updated: {datetime.now().strftime('%B %d, %Y')}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    for cat in faq_data["categories"]:
        lines.append(f"# {cat['name']}")
        lines.append("")

        for faq in cat["faqs"]:
            question = faq["question"].strip()
            answer = faq["answer"].strip()
            # Notion toggle heading format
            lines.append(f"- **{question}**")
            # Indent answer under the toggle
            for answer_line in answer.split("\n"):
                lines.append(f"    {answer_line}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 80)
    print("Salesforce FAQ Generator")
    print("=" * 80)

    conversations = load_conversations()
    print(f"Loaded {len(conversations)} conversations")
    with_replies = [c for c in conversations if c["replies"]]
    without_replies = [c for c in conversations if not c["replies"]]
    print(f"  With replies: {len(with_replies)}")
    print(f"  Without replies (questions only): {len(without_replies)}")

    # Step 1: Extract Q&A pairs from answered conversations
    print("\n--- Step 1: Extracting Q&A pairs ---")
    qa_pairs = extract_qa_pairs(with_replies)
    print(f"\nTotal Q&A pairs extracted: {len(qa_pairs)}")

    # Step 2: Handle unanswered questions with Salesforce knowledge
    print("\n--- Step 2: Answering unanswered questions ---")
    unanswered_pairs = handle_unanswered(conversations)
    qa_pairs.extend(unanswered_pairs)
    print(f"Total Q&A pairs (including newly answered): {len(qa_pairs)}")

    # Save raw pairs for debugging
    with open("faq_raw_pairs.json", "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
    print("Raw pairs saved to faq_raw_pairs.json")

    # Step 3: Deduplicate, organize, and validate
    print("\n--- Step 3: Organizing final FAQ ---")
    faq_data = deduplicate_and_organize(qa_pairs)

    if not faq_data:
        print("Failed to organize FAQs. Check faq_raw_pairs.json for raw data.")
        return

    # Save structured FAQ
    with open("faq_structured.json", "w", encoding="utf-8") as f:
        json.dump(faq_data, f, indent=2, ensure_ascii=False)
    print("Structured FAQ saved to faq_structured.json")

    # Step 4: Generate Notion-compatible output
    print("\n--- Step 4: Generating Notion-compatible output ---")

    # HTML toggle version (for Notion paste)
    html_md = generate_notion_markdown(faq_data)
    with open("FAQ_Salesforce_Helpdesk.md", "w", encoding="utf-8") as f:
        f.write(html_md)
    print("Notion-compatible FAQ saved to FAQ_Salesforce_Helpdesk.md")

    # Notion toggle version
    toggle_md = generate_notion_toggle_markdown(faq_data)
    with open("FAQ_Salesforce_Helpdesk_Toggle.md", "w", encoding="utf-8") as f:
        f.write(toggle_md)
    print("Toggle-format FAQ saved to FAQ_Salesforce_Helpdesk_Toggle.md")

    # Summary
    total_faqs = sum(len(c["faqs"]) for c in faq_data["categories"])
    print("\n" + "=" * 80)
    print("DONE!")
    print(f"  Categories: {len(faq_data['categories'])}")
    for cat in faq_data["categories"]:
        print(f"    - {cat['name']}: {len(cat['faqs'])} FAQs")
    print(f"  Total FAQs: {total_faqs}")
    print(f"  Output files:")
    print(f"    - FAQ_Salesforce_Helpdesk.md (HTML toggle format)")
    print(f"    - FAQ_Salesforce_Helpdesk_Toggle.md (Notion toggle format)")
    print(f"    - faq_structured.json (structured data)")
    print(f"    - faq_raw_pairs.json (raw extracted pairs)")
    print("=" * 80)


if __name__ == "__main__":
    main()
