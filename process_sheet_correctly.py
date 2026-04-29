#!/usr/bin/env python3
"""
Process the complete sheet correctly:
1. Preserve ALL original structure including Exit / sign-off column
2. Fix "Rest of Countries = UAE" logic
3. Preserve user changes up to row 8
4. Mark L2 LOBs with "Yes (X%)" as [TBD]
5. Process all waves correctly
"""

import csv
import re

input_file = '/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline.csv'
output_file = '/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv'

print("=" * 80)
print("PROCESSING SHEET CORRECTLY - FROM SCRATCH")
print("=" * 80)

# Read original file
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

headers = rows[0]
num_cols = len(headers)
coverage_idx = headers.index('Channels & Coverage')
exit_idx = headers.index('Exit / sign-off')

print(f"Read {len(rows)} rows, {num_cols} columns")
print(f"Coverage column index: {coverage_idx}")
print(f"Exit / sign-off column index: {exit_idx}")

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
    # Ensure row has correct number of columns
    while len(row) < num_cols:
        row.append('')
    
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
    
    # Create new row - preserve metadata columns (0-7) for user-edited rows, but process all LOB columns
    new_row = row.copy()
    preserve_metadata = (row_idx <= 9)  # Preserve metadata for rows 2-9
    
    # Process each LOB column (skip metadata columns 0-7 and Exit column)
    for col_idx in range(8, exit_idx):  # Process columns 8 to exit_idx-1
        header = headers[col_idx]
        
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
        else:
            continue  # Skip if not a recognized LOB
        
        # Check if L2
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
        
        # Determine region - Rest of Countries = UAE
        if 'Rest of Countries' in header:
            region = 'UAE'
        elif 'KSA' in header:
            region = 'KSA'
        else:
            region = None
        
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
                value = f'Yes ({pct}%) [TBD]'  # Mark as TBD
        elif channel == 'Email':
            # Email: use persisted state
            if email_state[lob_type]['enabled']:
                pct = email_state[lob_type]['percentage']
                value = f'Yes ({pct}%)'
        else:
            # Chat and Phone: region-specific
            # IMPORTANT: Rest of Countries = UAE
            if channel in coverage_data.get(lob_type, {}):
                # If wave mentions UAE and column is Rest of Countries, use UAE coverage
                if 'Rest of Countries' in header and 'UAE' in coverage_text:
                    p = coverage_data[lob_type][channel].get('UAE', 0)
                else:
                    p = coverage_data[lob_type][channel].get(region, 0)
                if p > 0:
                    value = f'Yes ({p}%)'
        
        # Always update LOB columns (user changes are in metadata, not LOB columns)
        new_row[col_idx] = value
    
    # Find Exit value from original row (it might be at a different index due to trailing commas)
    # Priority: go/no-go > Full migration > UAT sign-off > No (but only if it's actually in Exit column context)
    exit_value = ''
    
    # First, try to find by specific keywords (these are Exit column specific)
    for j, val in enumerate(row):
        if val and val.strip():
            val_clean = val.strip()
            if 'go/no-go' in val_clean or 'Full migration' in val_clean or 'UAT sign-off' in val_clean:
                exit_value = val_clean
                break
    
    # If not found, check the expected Exit column index
    if not exit_value and len(row) > exit_idx:
        exit_value = row[exit_idx].strip() if row[exit_idx] else ''
    
    # For rows 2-9, also check if "No" is in the Exit column position
    if not exit_value and row_idx <= 9:
        # Check around the Exit column index
        for j in range(max(0, exit_idx-5), min(len(row), exit_idx+1)):
            if j == exit_idx and row[j] and row[j].strip() == 'No':
                exit_value = 'No'
                break
    
    # Ensure row has correct length
    while len(new_row) < num_cols:
        new_row.append('')
    
    # Place Exit value at correct index
    new_row[exit_idx] = exit_value
    
    # Ensure row has correct length
    while len(new_row) < num_cols:
        new_row.append('')
    
    new_rows.append(new_row)

# Write output
print(f"\nWriting to: {output_file}")
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(new_rows)

print(f"✅ Complete! {len(new_rows) - 1} rows processed")

# Verification
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

# Check Exit column
exit_issues = 0
for i, row in enumerate(new_rows[1:], start=2):
    if len(row) <= exit_idx:
        print(f"❌ Row {i}: Missing Exit column")
        exit_issues += 1
    elif i <= 9 and len(rows[i-1]) > exit_idx:
        orig_exit = rows[i-1][exit_idx] if len(rows[i-1]) > exit_idx else ''
        new_exit = row[exit_idx] if len(row) > exit_idx else ''
        if orig_exit != new_exit:
            print(f"⚠️  Row {i}: Exit column changed")
            print(f"   Original: {orig_exit}")
            print(f"   New: {new_exit}")

if exit_issues == 0:
    print("✅ Exit / sign-off column preserved correctly")

# Check Wave 1d
print("\nWave 1d verification:")
for row in new_rows[1:]:
    if 'Wave 1d' in row[0]:
        print(f"  Phase: {row[0]}")
        for j, h in enumerate(headers):
            if 'Partner Care' in h and 'Chat' in h and 'Rest of Countries' in h:
                val = row[j] if len(row) > j else 'N/A'
                print(f"  {h}: {val}")
                if 'Yes (100%)' in val:
                    print("  ✅ Correct!")
                else:
                    print("  ❌ Should be Yes (100%)")

# Check column counts
print(f"\nColumn count check:")
print(f"  Headers: {len(headers)}")
for i, row in enumerate(new_rows[1:5], start=2):
    print(f"  Row {i}: {len(row)} columns")
    if len(row) != num_cols:
        print(f"    ⚠️  Mismatch! Expected {num_cols}, got {len(row)}")

print("\n✅ Processing complete!")

