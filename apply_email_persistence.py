#!/usr/bin/env python3
"""
Apply Email persistence to existing FINAL file.
Once Email is enabled for a LOB, it stays enabled for both regions.
"""

import csv
import re
import sys

# Read the FINAL file (which already has Chat & Email split)
input_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv"
output_file = "/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv"

try:
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
except FileNotFoundError:
    print(f"❌ File not found: {input_file}")
    print("Please ensure the file exists in Downloads folder")
    sys.exit(1)

headers = rows[0]
coverage_idx = headers.index('Channels & Coverage')

print("=" * 80)
print("APPLYING EMAIL PERSISTENCE")
print("=" * 80)
print(f"Input file: {input_file}")
print(f"Rows: {len(rows)}")

# Find Email column indices per LOB
email_columns = {
    'Customer': {'KSA': [], 'Rest of Countries': []},
    'Partner': {'KSA': [], 'Rest of Countries': []},
    'Partner Onboarding': {'KSA': [], 'Rest of Countries': []}
}

for j, h in enumerate(headers):
    if 'Email' in h and 'Chat & Email' not in h:
        if 'Customer Care' in h:
            if 'KSA' in h:
                email_columns['Customer']['KSA'].append(j)
            elif 'Rest of Countries' in h:
                email_columns['Customer']['Rest of Countries'].append(j)
        elif 'Partner Care' in h:
            if 'KSA' in h:
                email_columns['Partner']['KSA'].append(j)
            elif 'Rest of Countries' in h:
                email_columns['Partner']['Rest of Countries'].append(j)
        elif 'Partner Onboarding' in h:
            if 'KSA' in h:
                email_columns['Partner Onboarding']['KSA'].append(j)
            elif 'Rest of Countries' in h:
                email_columns['Partner Onboarding']['Rest of Countries'].append(j)

print(f"\nEmail columns found:")
for lob, regions in email_columns.items():
    print(f"  {lob}: KSA={len(regions['KSA'])}, Rest of Countries={len(regions['Rest of Countries'])}")

# Track Email state per LOB (persists across waves)
email_state = {
    'Customer': {'enabled': False, 'percentage': 0},
    'Partner': {'enabled': False, 'percentage': 0},
    'Partner Onboarding': {'enabled': False, 'percentage': 0}
}

def parse_coverage(coverage_text):
    """Parse coverage to check if Email is enabled."""
    if not coverage_text or not coverage_text.strip():
        return {}
    
    result = {}
    entries = []
    for line in coverage_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split(' - ')
        for part in parts:
            part = part.strip()
            if part.startswith('-'):
                part = part[1:].strip()
            if part and ('Customer' in part or 'Partner' in part):
                entries.append(part)
    
    for entry in entries:
        if 'Email' not in entry:
            continue
        
        pct_match = re.search(r'\((\d+)%', entry)
        if not pct_match:
            continue
        percentage = int(pct_match.group(1))
        
        lob_type = None
        if 'Customer' in entry:
            lob_type = 'Customer'
        elif 'Partner Onboarding' in entry:
            lob_type = 'Partner Onboarding'
        elif 'Partner' in entry:
            lob_type = 'Partner'
        
        if lob_type:
            result[lob_type] = percentage
    
    return result

# Process rows
print("\nProcessing rows...")
new_rows = [headers]

for row_idx, row in enumerate(rows[1:], start=2):
    if len(row) <= coverage_idx:
        new_rows.append(row)
        continue
    
    coverage_text = row[coverage_idx]
    email_coverage = parse_coverage(coverage_text)
    
    # Update Email state - if Email is enabled in this wave, persist it
    for lob_type, percentage in email_coverage.items():
        if percentage > 0:
            email_state[lob_type]['enabled'] = True
            email_state[lob_type]['percentage'] = max(email_state[lob_type]['percentage'], percentage)
    
    # Create new row
    new_row = row.copy()
    
    # Update Email columns based on persisted state
    for lob_type, regions in email_columns.items():
        if email_state[lob_type]['enabled']:
            pct = email_state[lob_type]['percentage']
            value = f'Yes ({pct}%)'
            
            # Set all Email columns for this LOB to the same value
            for region_type, col_indices in regions.items():
                for col_idx in col_indices:
                    if len(new_row) > col_idx:
                        new_row[col_idx] = value
                    else:
                        while len(new_row) <= col_idx:
                            new_row.append('')
                        new_row[col_idx] = value
    
    new_rows.append(new_row)

# Write output
print(f"\nWriting output to: {output_file}")
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(new_rows)

print(f"✅ Complete! Output: {output_file}")
print(f"   Rows: {len(new_rows) - 1}")

# Validation
print("\nValidating Email persistence...")
for row in new_rows[1:]:
    phase = row[0]
    if 'Wave 1a' in phase or 'Wave 3a' in phase:
        partner_email_ksa = None
        partner_email_roc = None
        
        for col_idx in email_columns['Partner']['KSA']:
            if len(row) > col_idx:
                partner_email_ksa = row[col_idx]
                break
        for col_idx in email_columns['Partner']['Rest of Countries']:
            if len(row) > col_idx:
                partner_email_roc = row[col_idx]
                break
        
        if partner_email_ksa and partner_email_roc:
            if partner_email_ksa == partner_email_roc:
                print(f"✅ {phase}: Partner Email synchronized = {partner_email_ksa}")
            else:
                print(f"❌ {phase}: Partner Email mismatch: KSA={partner_email_ksa}, ROC={partner_email_roc}")

print("\n✅ Email persistence applied!")













