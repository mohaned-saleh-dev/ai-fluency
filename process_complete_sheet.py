#!/usr/bin/env python3
"""
Process the complete sheet:
1. Fix "Rest of Countries = UAE" logic
2. Incorporate user changes up to row 8
3. Mark L2 LOBs with "Yes (X%)" as TBD (add marker for yellow highlighting)
4. Process all waves correctly
"""

import csv
import re

input_file = '/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline.csv'
output_file = '/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv'

print("=" * 80)
print("PROCESSING COMPLETE SHEET")
print("=" * 80)

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

headers = rows[0]
coverage_idx = headers.index('Channels & Coverage')

print(f"Read {len(rows)} rows, {len(headers)} columns")

# Identify L2 LOB columns (for TBD marking)
l2_columns = []
for j, h in enumerate(headers):
    if any(x in h for x in ['Government', 'Executive', 'Trust & Safety', 'Technical Support',
                             'Manager Escalations', 'Collections', 'Finance', 'Risk', 'Integrations']):
        l2_columns.append(j)

print(f"Found {len(l2_columns)} L2 LOB columns")

# Identify region columns
def get_region_from_header(header):
    """Extract region from header."""
    if 'Rest of Countries' in header:
        return 'UAE'  # Rest of Countries = UAE
    elif 'KSA' in header:
        return 'KSA'
    return None

# Track Email state (persists across waves)
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
new_rows = [headers]

for row_idx, row in enumerate(rows[1:], start=2):
    if len(row) <= coverage_idx:
        new_rows.append(row)
        continue
    
    coverage_text = row[coverage_idx]
    coverage_data = parse_coverage(coverage_text)
    
    # Update Email state
    for lob_type in ['Customer', 'Partner', 'Partner Onboarding']:
        if 'Email' in coverage_data.get(lob_type, {}):
            uae_pct = coverage_data[lob_type]['Email'].get('UAE', 0)
            ksa_pct = coverage_data[lob_type]['Email'].get('KSA', 0)
            max_pct = max(uae_pct, ksa_pct)
            if max_pct > 0:
                email_state[lob_type]['enabled'] = True
                email_state[lob_type]['percentage'] = max(email_state[lob_type]['percentage'], max_pct)
    
    # Create new row (preserve user changes up to row 8)
    if row_idx <= 9:  # Rows 2-9 (user made changes)
        new_row = row.copy()
    else:
        new_row = row.copy()
    
    # Process each column
    for col_idx, header in enumerate(headers):
        if col_idx < 8:  # Skip metadata columns
            continue
        
        if len(new_row) <= col_idx:
            new_row.append('')
        
        # For user-edited rows (up to row 8), only skip if it's a non-LOB column
        # We still need to process LOB columns even if user made changes
        # (user changes are in metadata columns, not LOB columns)
        
        # Determine LOB type, channel, region
        lob_type = None
        channel = None
        region = None
        is_l2 = False
        
        if 'Customer Care' in header:
            lob_type = 'Customer'
        elif 'Partner Onboarding' in header:
            lob_type = 'Partner Onboarding'
        elif 'Partner Care' in header:
            lob_type = 'Partner'
        
        if any(x in header for x in ['Government', 'Executive', 'Trust & Safety', 'Technical Support',
                                     'Manager Escalations', 'Collections', 'Finance', 'Risk', 'Integrations']):
            is_l2 = True
        else:
            if 'Chat' in header:
                channel = 'Chat'
            elif 'Email' in header:
                channel = 'Email'
            elif 'Phone' in header:
                channel = 'Phone'
        
        region = get_region_from_header(header)
        
        # Calculate value
        value = 'No'
        
        if is_l2:
            # L2: use minimum of L1 percentages for the region
            all_pcts = []
            for ch in ['Email', 'Chat', 'Phone']:
                if ch in coverage_data.get(lob_type, {}):
                    p = coverage_data[lob_type][ch].get(region, 0)
                    if p > 0:
                        all_pcts.append(p)
            pct = min(all_pcts) if all_pcts else 0
            if pct > 0:
                value = f'Yes ({pct}%) [TBD]'  # Mark as TBD for yellow highlighting
        elif channel == 'Email':
            # Email: use persisted state
            if email_state[lob_type]['enabled']:
                pct = email_state[lob_type]['percentage']
                value = f'Yes ({pct}%)'
        else:
            # Chat and Phone: region-specific
            # Map "Rest of Countries" to "UAE" when checking coverage
            check_region = 'UAE' if region == 'UAE' or (region is None and 'Rest of Countries' in header) else region
            if channel in coverage_data.get(lob_type, {}):
                # If wave mentions UAE and column is Rest of Countries, use UAE coverage
                if 'Rest of Countries' in header and 'UAE' in coverage_text:
                    p = coverage_data[lob_type][channel].get('UAE', 0)
                else:
                    p = coverage_data[lob_type][channel].get(region, 0)
                if p > 0:
                    value = f'Yes ({p}%)'
        
        new_row[col_idx] = value
    
    new_rows.append(new_row)

# Write output
print(f"\nWriting to: {output_file}")
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(new_rows)

print(f"✅ Complete! {len(new_rows) - 1} rows processed")
print(f"   L2 LOBs marked with [TBD] for yellow highlighting")

# Verify Wave 1d
print("\nVerifying Wave 1d:")
for row in new_rows[1:]:
    if 'Wave 1d' in row[0]:
        print(f"  Phase: {row[0]}")
        for j, h in enumerate(headers):
            if 'Partner Care' in h and 'Chat' in h and 'Rest of Countries' in h:
                val = row[j] if len(row) > j else 'N/A'
                print(f"  {h}: {val}")

