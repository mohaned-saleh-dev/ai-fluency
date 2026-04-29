#!/usr/bin/env python3
"""
Create final CSV file with Email persistence from the UPDATED file.
"""

import csv
import re
import os
import glob

# Find the input file
input_file = None
downloads_dir = '/Users/mohaned.saleh/Downloads'
possible_names = [
    'Tamara __ Salesforce Testing Guide - Roll-out Timeline_UPDATED.csv',
    'Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv',
    'Tamara __ Salesforce Testing Guide - Roll-out Timeline.csv'
]

for name in possible_names:
    full_path = os.path.join(downloads_dir, name)
    if os.path.exists(full_path):
        input_file = full_path
        break

if not input_file:
    # Try glob
    files = glob.glob(os.path.join(downloads_dir, '*Roll-out*Timeline*.csv'))
    if files:
        input_file = files[0]

if not input_file:
    print("❌ Could not find input file")
    exit(1)

print(f"✅ Using input file: {input_file}")

# Read the file
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

headers = rows[0]
coverage_idx = headers.index('Channels & Coverage')

print(f"Read {len(rows)} rows, {len(headers)} columns")

# Restructure headers - split Chat & Email
new_headers = headers[:8].copy()
column_mapping = {}

for idx, header in enumerate(headers):
    if idx < 8:
        continue
    
    parts = [p.strip() for p in header.split(' - ')]
    if len(parts) < 3:
        continue
    
    lob_name = parts[0]
    channel_part = parts[1]
    
    is_l2 = any(x in channel_part for x in ['Government', 'Executive', 'Trust & Safety', 'Technical Support',
                                             'Manager Escalations', 'Collections', 'Finance', 'Risk', 'Integrations'])
    
    if is_l2:
        segment = None
        region_part = parts[2] if len(parts) > 2 else None
    else:
        segment = parts[2] if len(parts) > 2 else None
        region_part = parts[3] if len(parts) > 3 else None
    
    lob_type = None
    if 'Customer Care' in lob_name:
        lob_type = 'Customer'
    elif 'Partner Onboarding' in lob_name:
        lob_type = 'Partner Onboarding'
    elif 'Partner Care' in lob_name:
        lob_type = 'Partner'
    elif any(x in lob_name for x in ['Government', 'Executive', 'Trust & Safety', 'Technical Support',
                                     'Manager Escalations', 'Collections', 'Finance', 'Risk']):
        lob_type = 'Customer'
    elif 'Integrations' in lob_name:
        lob_type = 'Partner Onboarding'
    
    if not lob_type:
        continue
    
    region = None
    if region_part == 'KSA':
        region = 'KSA'
    elif region_part == 'Rest of Countries':
        region = 'Rest of Countries'
    
    if not is_l2 and 'Chat & Email' in channel_part:
        for channel in ['Chat', 'Email']:
            new_header = f"{lob_name} - {channel} - {segment} - {region_part}"
            new_idx = len(new_headers)
            new_headers.append(new_header)
            column_mapping[new_idx] = {
                'lob': lob_type,
                'channel': channel,
                'region': region,
                'segment': segment,
                'is_l2': False
            }
    else:
        channel = None
        if not is_l2:
            if 'Chat' in channel_part:
                channel = 'Chat'
            elif 'Email' in channel_part:
                channel = 'Email'
            elif 'Phone' in channel_part:
                channel = 'Phone'
        
        if channel or is_l2:
            new_header = header
            new_idx = len(new_headers)
            new_headers.append(new_header)
            column_mapping[new_idx] = {
                'lob': lob_type,
                'channel': channel,
                'region': region,
                'segment': segment,
                'is_l2': is_l2
            }

print(f"New headers: {len(new_headers)} columns")

# Email state tracking (persists across waves)
email_state = {
    'Customer': {'enabled': False, 'percentage': 0},
    'Partner': {'enabled': False, 'percentage': 0},
    'Partner Onboarding': {'enabled': False, 'percentage': 0}
}

def parse_coverage(coverage_text):
    """Parse coverage text."""
    result = {
        'Customer': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}},
        'Partner': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}},
        'Partner Onboarding': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}}
    }
    
    if not coverage_text or not coverage_text.strip():
        return result
    
    if 'ALL Channels' in coverage_text.upper():
        for lob in result:
            for channel in result[lob]:
                result[lob][channel] = {'UAE': 100, 'KSA': 100}
        return result
    
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
        
        if not lob_type:
            continue
        
        channel = None
        if 'Email' in entry:
            channel = 'Email'
        elif 'Chat' in entry:
            channel = 'Chat'
        elif 'Phone' in entry:
            channel = 'Phone'
        
        if not channel:
            continue
        
        if channel == 'Email':
            if 'UAE' in entry or 'KSA' in entry:
                result[lob_type][channel]['UAE'] = max(result[lob_type][channel]['UAE'], percentage)
                result[lob_type][channel]['KSA'] = max(result[lob_type][channel]['KSA'], percentage)
        else:
            if 'UAE + KSA' in entry or 'KSA + UAE' in entry:
                result[lob_type][channel]['UAE'] = percentage
                result[lob_type][channel]['KSA'] = percentage
            elif 'UAE' in entry:
                result[lob_type][channel]['UAE'] = percentage
            elif 'KSA' in entry:
                result[lob_type][channel]['KSA'] = percentage
    
    return result

# Process rows
new_rows = [new_headers]

for row_idx, row in enumerate(rows[1:], start=2):
    if len(row) <= coverage_idx:
        continue
    
    coverage_text = row[coverage_idx]
    coverage_data = parse_coverage(coverage_text)
    
    # Update Email state - if Email is enabled in this wave, persist it
    for lob_type in ['Customer', 'Partner', 'Partner Onboarding']:
        if 'Email' in coverage_data.get(lob_type, {}):
            uae_pct = coverage_data[lob_type]['Email'].get('UAE', 0)
            ksa_pct = coverage_data[lob_type]['Email'].get('KSA', 0)
            max_pct = max(uae_pct, ksa_pct)
            if max_pct > 0:
                email_state[lob_type]['enabled'] = True
                email_state[lob_type]['percentage'] = max(email_state[lob_type]['percentage'], max_pct)
    
    new_row = row[:8].copy()
    
    for col_idx, col_info in column_mapping.items():
        lob_type = col_info['lob']
        channel = col_info['channel']
        region = col_info['region']
        is_l2 = col_info['is_l2']
        
        value = 'No'
        
        check_regions = []
        if region == 'Rest of Countries':
            check_regions = ['UAE', 'KSA']
        elif region:
            check_regions = [region]
        
        if is_l2:
            all_pcts = []
            for r in check_regions:
                for ch in ['Email', 'Chat', 'Phone']:
                    if ch in coverage_data.get(lob_type, {}):
                        p = coverage_data[lob_type][ch].get(r, 0)
                        if p > 0:
                            all_pcts.append(p)
            pct = min(all_pcts) if all_pcts else 0
            if pct > 0:
                value = f'Yes ({pct}%)'
        elif channel == 'Email':
            # Email: use persisted state (enabled for both regions once enabled)
            if email_state[lob_type]['enabled']:
                pct = email_state[lob_type]['percentage']
                value = f'Yes ({pct}%)'
        else:
            # Chat and Phone: region-specific
            pcts = []
            for r in check_regions:
                if channel in coverage_data.get(lob_type, {}):
                    p = coverage_data[lob_type][channel].get(r, 0)
                    if p > 0:
                        pcts.append(p)
            pct = max(pcts) if pcts else 0
            if pct > 0:
                value = f'Yes ({pct}%)'
        
        new_row.append(value)
    
    new_rows.append(new_row)

# Write output
output_file = '/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv'
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
        partner_email = {}
        for col_idx, col_info in column_mapping.items():
            if col_info['lob'] == 'Partner' and col_info['channel'] == 'Email':
                reg = col_info['region']
                val = row[col_idx] if len(row) > col_idx else 'N/A'
                if reg:
                    partner_email[reg] = val
        
        if partner_email:
            values = list(partner_email.values())
            if len(set(values)) == 1:
                print(f"✅ {phase}: Partner Email = {values[0]} (both regions)")
            else:
                print(f"❌ {phase}: Partner Email mismatch: {partner_email}")

print("\n✅ File created successfully!")













