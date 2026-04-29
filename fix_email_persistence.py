#!/usr/bin/env python3
"""
Fix Email persistence: Once Email is enabled for a LOB, it stays enabled
for both regions across all subsequent waves.
"""

import csv
import re
from typing import Dict, List

def parse_coverage(coverage_text: str) -> Dict[str, Dict[str, Dict[str, int]]]:
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
            # Email: if ANY region mentioned, apply to BOTH
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

def restructure_headers(headers: List[str]) -> tuple:
    """Split Chat & Email columns."""
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
    
    return new_headers, column_mapping

def get_l1_percentages(coverage_data: Dict, lob_type: str, regions: List[str]) -> List[int]:
    """Get all L1 percentages."""
    percentages = []
    for region in regions:
        for channel in ['Email', 'Chat', 'Phone']:
            if channel in coverage_data.get(lob_type, {}):
                pct = coverage_data[lob_type][channel].get(region, 0)
                if pct > 0:
                    percentages.append(pct)
    return percentages

def process_csv(input_file: str, output_file: str):
    """Process CSV with Email persistence."""
    print("=" * 80)
    print("FIXING EMAIL PERSISTENCE")
    print("=" * 80)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    headers = rows[0]
    coverage_idx = headers.index('Channels & Coverage')
    
    print("\n1. Restructuring headers...")
    new_headers, column_mapping = restructure_headers(headers)
    print(f"   Columns: {len(new_headers)}")
    
    print("\n2. Processing rows with Email persistence...")
    new_rows = [new_headers]
    
    # Track Email state per LOB (persists across waves)
    email_state = {
        'Customer': {'enabled': False, 'percentage': 0},
        'Partner': {'enabled': False, 'percentage': 0},
        'Partner Onboarding': {'enabled': False, 'percentage': 0}
    }
    
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
                all_pcts = get_l1_percentages(coverage_data, lob_type, check_regions)
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
    
    print("\n3. Writing output...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)
    
    print(f"\n✅ Complete!")
    print(f"   Output: {output_file}")
    print(f"   Rows: {len(new_rows) - 1}")
    
    # Validation
    print("\n4. Validating Email persistence...")
    errors = []
    
    # Check Wave 1a and 3a - Partner Email should be same
    wave_1a_email = None
    wave_3a_email = None
    
    for row in new_rows[1:]:
        phase = row[0]
        if 'Wave 1a' in phase:
            for col_idx, col_info in column_mapping.items():
                if col_info['lob'] == 'Partner' and col_info['channel'] == 'Email':
                    wave_1a_email = row[col_idx] if len(row) > col_idx else 'N/A'
                    break
        elif 'Wave 3a' in phase:
            for col_idx, col_info in column_mapping.items():
                if col_info['lob'] == 'Partner' and col_info['channel'] == 'Email':
                    wave_3a_email = row[col_idx] if len(row) > col_idx else 'N/A'
                    break
    
    if wave_1a_email and wave_3a_email:
        if wave_1a_email == wave_3a_email:
            print(f"   ✅ Wave 1a and 3a Partner Email match: {wave_1a_email}")
        else:
            errors.append(f"Wave 1a and 3a Partner Email don't match: {wave_1a_email} vs {wave_3a_email}")
    
    # Check Wave 2a and 4a - Customer Email should be same
    wave_2a_email = None
    wave_4a_email = None
    
    for row in new_rows[1:]:
        phase = row[0]
        if 'Wave 2a' in phase:
            for col_idx, col_info in column_mapping.items():
                if col_info['lob'] == 'Customer' and col_info['channel'] == 'Email' and col_info.get('segment') == 'Standard':
                    wave_2a_email = row[col_idx] if len(row) > col_idx else 'N/A'
                    break
        elif 'Wave 4a' in phase:
            for col_idx, col_info in column_mapping.items():
                if col_info['lob'] == 'Customer' and col_info['channel'] == 'Email' and col_info.get('segment') == 'Standard':
                    wave_4a_email = row[col_idx] if len(row) > col_idx else 'N/A'
                    break
    
    if wave_2a_email and wave_4a_email:
        if wave_2a_email == wave_4a_email:
            print(f"   ✅ Wave 2a and 4a Customer Email match: {wave_2a_email}")
        else:
            errors.append(f"Wave 2a and 4a Customer Email don't match: {wave_2a_email} vs {wave_4a_email}")
    
    if errors:
        print("\n❌ Errors found:")
        for e in errors:
            print(f"   - {e}")
    else:
        print("\n✅ All validations passed!")
    
    return len(errors) == 0

if __name__ == "__main__":
    import os
    
    # Try to find the input file - use UPDATED file which has dates fixed
    possible_inputs = [
        "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_UPDATED.csv",
        "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv",
        "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline.csv"
    ]
    
    input_file = None
    for f in possible_inputs:
        if os.path.exists(f):
            input_file = f
            break
    
    if not input_file:
        print("❌ Could not find input file. Please check the Downloads folder.")
        exit(1)
    
    output_file = "/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv"
    
    print(f"Using input file: {input_file}")
    process_csv(input_file, output_file)

