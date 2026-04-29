#!/usr/bin/env python3
"""
Fresh implementation: Restructure CSV and update LOB columns correctly.
Key rules:
1. Split Chat & Email into separate columns
2. Email is synchronized across regions (KSA and Rest of Countries) at LOB level
3. Chat and Phone are region-specific
4. L2 LOBs use lowest percentage from L1 LOBs
"""

import csv
import re
from typing import Dict, List

def parse_coverage(coverage_text: str) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Parse coverage text and return structured data.
    For Email: if ANY region is mentioned, apply to BOTH regions.
    """
    result = {
        'Customer': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}},
        'Partner': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}},
        'Partner Onboarding': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}}
    }
    
    if not coverage_text or not coverage_text.strip():
        return result
    
    # Handle "ALL Channels"
    if 'ALL Channels' in coverage_text.upper():
        for lob in result:
            for channel in result[lob]:
                result[lob][channel] = {'UAE': 100, 'KSA': 100}
        return result
    
    # Parse entries - split by " - " to handle multiple entries on one line
    entries = []
    for line in coverage_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Split by " - " to get individual entries
        parts = line.split(' - ')
        for part in parts:
            part = part.strip()
            if part.startswith('-'):
                part = part[1:].strip()
            if part and ('Customer' in part or 'Partner' in part):
                entries.append(part)
    
    # Process each entry
    for entry in entries:
        # Extract percentage
        pct_match = re.search(r'\((\d+)%', entry)
        if not pct_match:
            continue
        percentage = int(pct_match.group(1))
        
        # Determine LOB type
        lob_type = None
        if 'Customer' in entry:
            lob_type = 'Customer'
        elif 'Partner Onboarding' in entry:
            lob_type = 'Partner Onboarding'
        elif 'Partner' in entry:
            lob_type = 'Partner'
        
        if not lob_type:
            continue
        
        # Determine channel
        channel = None
        if 'Email' in entry:
            channel = 'Email'
        elif 'Chat' in entry:
            channel = 'Chat'
        elif 'Phone' in entry:
            channel = 'Phone'
        
        if not channel:
            continue
        
        # Determine region - SPECIAL HANDLING FOR EMAIL
        if channel == 'Email':
            # Email: if ANY region mentioned, apply to BOTH
            if 'UAE' in entry or 'KSA' in entry:
                result[lob_type][channel]['UAE'] = max(result[lob_type][channel]['UAE'], percentage)
                result[lob_type][channel]['KSA'] = max(result[lob_type][channel]['KSA'], percentage)
        else:
            # Chat and Phone: region-specific
            if 'UAE + KSA' in entry or 'KSA + UAE' in entry:
                result[lob_type][channel]['UAE'] = percentage
                result[lob_type][channel]['KSA'] = percentage
            elif 'UAE' in entry:
                result[lob_type][channel]['UAE'] = percentage
            elif 'KSA' in entry:
                result[lob_type][channel]['KSA'] = percentage
    
    return result

def restructure_headers(headers: List[str]) -> tuple:
    """Split Chat & Email columns and create column mapping."""
    new_headers = headers[:8].copy()  # Keep first 8 columns
    
    column_mapping = {}
    
    for idx, header in enumerate(headers):
        if idx < 8:
            continue
        
        parts = [p.strip() for p in header.split(' - ')]
        if len(parts) < 3:
            continue
        
        lob_name = parts[0]
        channel_part = parts[1]
        
        # Check if L2 LOB
        is_l2 = any(x in channel_part for x in ['Government', 'Executive', 'Trust & Safety', 'Technical Support',
                                                 'Manager Escalations', 'Collections', 'Finance', 'Risk', 'Integrations'])
        
        if is_l2:
            segment = None
            region_part = parts[2] if len(parts) > 2 else None
        else:
            segment = parts[2] if len(parts) > 2 else None
            region_part = parts[3] if len(parts) > 3 else None
        
        # Determine LOB type
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
        
        # Determine region
        region = None
        if region_part == 'KSA':
            region = 'KSA'
        elif region_part == 'Rest of Countries':
            region = 'Rest of Countries'
        
        # Handle Chat & Email split
        if not is_l2 and 'Chat & Email' in channel_part:
            # Create separate Chat and Email columns
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
            # Single channel or L2
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
    """Get all L1 percentages for given LOB and regions."""
    percentages = []
    for region in regions:
        for channel in ['Email', 'Chat', 'Phone']:
            if channel in coverage_data.get(lob_type, {}):
                pct = coverage_data[lob_type][channel].get(region, 0)
                if pct > 0:
                    percentages.append(pct)
    return percentages

def process_csv(input_file: str, output_file: str):
    """Main processing function."""
    print("=" * 80)
    print("FRESH RESTRUCTURE - Starting from scratch")
    print("=" * 80)
    
    # Read CSV
    print("\n1. Reading CSV...")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    headers = rows[0]
    coverage_idx = headers.index('Channels & Coverage')
    
    # Restructure headers
    print("2. Restructuring headers (splitting Chat & Email)...")
    new_headers, column_mapping = restructure_headers(headers)
    print(f"   Original: {len(headers)} columns")
    print(f"   New: {len(new_headers)} columns")
    
    # Process rows
    print("3. Processing rows...")
    new_rows = [new_headers]
    
    for row_idx, row in enumerate(rows[1:], start=2):
        if len(row) <= coverage_idx:
            continue
        
        coverage_text = row[coverage_idx]
        coverage_data = parse_coverage(coverage_text)
        
        new_row = row[:8].copy()
        
        # Process each column
        for col_idx, col_info in column_mapping.items():
            lob_type = col_info['lob']
            channel = col_info['channel']
            region = col_info['region']
            is_l2 = col_info['is_l2']
            
            value = 'No'
            
            # Determine regions to check
            check_regions = []
            if region == 'Rest of Countries':
                check_regions = ['UAE', 'KSA']
            elif region:
                check_regions = [region]
            
            if is_l2:
                # L2: lowest of all L1 percentages
                all_pcts = get_l1_percentages(coverage_data, lob_type, check_regions)
                pct = min(all_pcts) if all_pcts else 0
                if pct > 0:
                    value = f'Yes ({pct}%)'
            elif channel == 'Email':
                # Email: check ALL regions (UAE and KSA) - synchronized
                pcts = []
                for r in ['UAE', 'KSA']:
                    if 'Email' in coverage_data.get(lob_type, {}):
                        p = coverage_data[lob_type]['Email'].get(r, 0)
                        if p > 0:
                            pcts.append(p)
                pct = max(pcts) if pcts else 0
                if pct > 0:
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
    print("4. Writing output...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)
    
    print(f"\n✅ Complete!")
    print(f"   Output: {output_file}")
    print(f"   Rows: {len(new_rows) - 1}")
    
    # Quick validation
    print("\n5. Quick validation...")
    errors = []
    
    # Check Wave 1a and 3a - Partner Email should be synchronized
    for row in new_rows[1:]:
        phase = row[0]
        if 'Wave 1a' in phase or 'Wave 3a' in phase:
            # Find Partner Email columns
            partner_email = {}
            for col_idx, col_info in column_mapping.items():
                if col_info['lob'] == 'Partner' and col_info['channel'] == 'Email':
                    reg = col_info['region']
                    val = row[col_idx] if len(row) > col_idx else 'N/A'
                    if reg:
                        partner_email[reg] = val
            
            if len(set(partner_email.values())) > 1:
                errors.append(f"{phase}: Partner Email not synchronized: {partner_email}")
    
    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"   - {e}")
    else:
        print("✅ Validation passed!")
    
    return len(errors) == 0

if __name__ == "__main__":
    input_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_UPDATED.csv"
    output_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv"
    
    process_csv(input_file, output_file)













