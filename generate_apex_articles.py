#!/usr/bin/env python3
"""Generate Apex code batches for creating Knowledge articles from the FAQ markdown."""

import re
import json
import html


def parse_faq_markdown(filepath):
    """Parse FAQ markdown to extract category, question, and answer."""
    with open(filepath, 'r') as f:
        content = f.read()

    articles = []
    current_category = ""

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('# ') and not line.startswith('# Salesforce Service Cloud'):
            current_category = line[2:].strip()
            i += 1
            continue

        if line == '<details>':
            i += 1
            summary_line = lines[i].strip() if i < len(lines) else ""
            match = re.search(r'<summary><strong>(.*?)</strong></summary>', summary_line)
            if match:
                question = match.group(1)
            else:
                question = summary_line
                i += 1
                continue

            i += 1
            answer_lines = []
            while i < len(lines) and lines[i].strip() != '</details>':
                answer_lines.append(lines[i])
                i += 1

            answer = '\n'.join(answer_lines).strip()
            if answer.startswith('\n'):
                answer = answer.lstrip('\n')

            articles.append({
                'category': current_category,
                'question': question,
                'answer': answer
            })

        i += 1

    return articles


def make_url_name(question, index):
    """Generate a URL-friendly name from the question."""
    url = question.lower()
    url = re.sub(r'[^a-z0-9\s-]', '', url)
    url = re.sub(r'\s+', '-', url)
    url = url[:80]
    url = url.rstrip('-')
    return f"faq-{index:03d}-{url}"


def escape_apex_string(s):
    """Escape a string for use in Apex single-quoted strings."""
    s = s.replace('\\', '\\\\')
    s = s.replace("'", "\\'")
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '')
    return s


def markdown_to_html(md):
    """Convert basic markdown to HTML for the Knowledge article body."""
    lines = md.split('\n')
    html_lines = []
    in_list = False
    list_type = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None
            html_lines.append('')
            continue

        ol_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        ul_match = re.match(r'^[-*]\s+(.*)', stripped)

        if ol_match:
            if not in_list or list_type != 'ol':
                if in_list:
                    html_lines.append(f'</{list_type}>')
                html_lines.append('<ol>')
                in_list = True
                list_type = 'ol'
            item_text = ol_match.group(2)
            item_text = convert_inline_md(item_text)
            html_lines.append(f'<li>{item_text}</li>')
        elif ul_match:
            if not in_list or list_type != 'ul':
                if in_list:
                    html_lines.append(f'</{list_type}>')
                html_lines.append('<ul>')
                in_list = True
                list_type = 'ul'
            item_text = ul_match.group(1)
            item_text = convert_inline_md(item_text)
            html_lines.append(f'<li>{item_text}</li>')
        else:
            if in_list:
                html_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None
            converted = convert_inline_md(stripped)
            html_lines.append(f'<p>{converted}</p>')

    if in_list:
        html_lines.append(f'</{list_type}>')

    return '\n'.join(html_lines)


def convert_inline_md(text):
    """Convert inline markdown (bold, code, links) to HTML."""
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    return text


def generate_apex_batches(articles, batch_size=10):
    """Generate Apex code batches for article creation."""
    batches = []

    for batch_start in range(0, len(articles), batch_size):
        batch_articles = articles[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1

        apex_lines = [f'// Batch {batch_num}: Articles {batch_start + 1}-{batch_start + len(batch_articles)}']
        apex_lines.append('List<Knowledge__kav> articles = new List<Knowledge__kav>();')
        apex_lines.append('')

        for idx, art in enumerate(batch_articles):
            global_idx = batch_start + idx + 1
            url_name = make_url_name(art['question'], global_idx)
            answer_html = markdown_to_html(art['answer'])
            category_tag = f"[{art['category']}] "

            q_escaped = escape_apex_string(art['question'])
            summary_escaped = escape_apex_string(f"{category_tag}{art['question']}")
            answer_escaped = escape_apex_string(answer_html)
            url_escaped = escape_apex_string(url_name)

            if len(summary_escaped) > 255:
                summary_escaped = summary_escaped[:252] + '...'
            if len(q_escaped) > 255:
                q_escaped = q_escaped[:252] + '...'

            apex_lines.append(f'Knowledge__kav a{idx} = new Knowledge__kav();')
            apex_lines.append(f"a{idx}.Title = '{q_escaped}';")
            apex_lines.append(f"a{idx}.Summary = '{summary_escaped}';")
            apex_lines.append(f"a{idx}.UrlName = '{url_escaped}';")
            apex_lines.append(f"a{idx}.Answer__c = '{answer_escaped}';")
            apex_lines.append(f'articles.add(a{idx});')
            apex_lines.append('')

        apex_lines.append('insert articles;')
        apex_lines.append(f"System.debug('Batch {batch_num}: Inserted ' + articles.size() + ' articles');")

        batch_code = '\n'.join(apex_lines)
        batches.append(batch_code)

    return batches


def main():
    articles = parse_faq_markdown('/Users/mohaned.saleh/prd-ticket-agent/FAQ_Salesforce_Helpdesk.md')
    print(f"Found {len(articles)} FAQ articles")

    for i, art in enumerate(articles, 1):
        print(f"  {i}. [{art['category']}] {art['question'][:60]}...")

    batches = generate_apex_batches(articles, batch_size=10)
    print(f"\nGenerated {len(batches)} Apex batches")

    for i, batch in enumerate(batches):
        filepath = f'/Users/mohaned.saleh/prd-ticket-agent/apex_batch_{i+1}.txt'
        with open(filepath, 'w') as f:
            f.write(batch)
        print(f"  Batch {i+1}: {len(batch)} chars -> {filepath}")


if __name__ == '__main__':
    main()
