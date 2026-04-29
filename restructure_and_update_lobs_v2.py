#!/usr/bin/env python3
"""
Restructure CSV to split Chat & Email columns, and update all LOB columns correctly.
Email channels are synchronized across regions (KSA and Rest of Countries) since
emails don't have country information.
"""

import csv
import re
from typing import Dict, List, Tuple, Optional

def parse_coverage(coverage_text: str) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Parse the Channels & Coverage text to extract channel, region, and percentage.
    Returns a dict like: {
        'Customer': {'Email': {'UAE': 100, 'KSA': 0}, 'Chat': {'UAE': 20, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}},
        'Partner': {...},
        'Partner Onboarding': {...}
    }
    """
    result = {
        'Customer': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}},
        'Partner': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}},
        'Partner Onboarding': {'Email': {'UAE': 0, 'KSA': 0}, 'Chat': {'UAE': 0, 'KSA': 0}, 'Phone': {'UAE': 0, 'KSA': 0}}
    }
    
    if not coverage_text or coverage_text.strip() == '':
        return result
    
    # Handle "ALL Channels" case
    if 'ALL Channels' in coverage_text.upper():
        result['Customer'] = {'Email': {'UAE': 100, 'KSA': 100}, 'Chat': {'UAE': 100, 'KSA': 100}, 'Phone': {'UAE': 100, 'KSA': 100}}
        result['Partner'] = {'Email': {'UAE': 100, 'KSA': 100}, 'Chat': {'UAE': 100, 'KSA': 100}, 'Phone': {'UAE': 100, 'KSA': 100}}
        result['Partner Onboarding'] = {'Email': {'UAE': 100, 'KSA': 100}, 'Chat': {'UAE': 100, 'KSA': 100}, 'Phone': {'UAE': 100, 'KSA': 100}}
        return result
    
    # Parse individual channel entries
    # Entries can be on separate lines or on the same line separated by " - "
    lines = coverage_text.split('\n')
    entries = []
    for line in lines:
        line = line.strip()
        # Split by " - " to handle multiple entries on same line
        parts = line.split(' - ')
        for part in parts:
            part = part.strip()
            if part.startswith('-'):
                part = part[1:].strip()
            if part and ('Customer' in part or 'Partner' in part):
                entries.append(part)
    
    for entry in entries:
        # Extract percentage
        percent_match = re.search(r'\((\d+)%', entry)
        if not percent_match:
            continue
        percentage = int(percent_match.group(1))
        
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
        
        # Determine region
        # Special handling for Email: if ANY region is mentioned, apply to BOTH regions
        if channel == 'Email':
            # Email can't be split by country - if mentioned for any region, apply to both
            if 'UAE' in entry or 'KSA' in entry or 'UAE + KSA' in entry or 'KSA + UAE' in entry:
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

def restructure_headers(headers: List[str]) -> Tuple[List[str], Dict[int, Dict]]:
    """
    Restructure headers to split Chat & Email into separate columns.
    Returns new headers and a mapping from new column indices to metadata.
    """
    new_headers = headers[:8].copy()  # Keep first 8 columns as-is
    
    column_mapping = {}  # Maps new column index to metadata
    
    for idx, header in enumerate(headers):
        if idx < 8:  # Skip non-LOB columns
            continue
        
        parts = [p.strip() for p in header.split(' - ')]
        if len(parts) < 3:
            continue
        
        lob_name = parts[0]
        channel_part = parts[1]
        
        # Check if parts[1] is an L2 LOB name (no channel specified)
        is_l2_header = any(x in channel_part for x in ['Government', 'Executive', 'Trust & Safety', 'Technical Support', 
                                                          'Manager Escalations', 'Collections', 'Finance', 'Risk', 'Integrations'])
        
        if is_l2_header:
            # For L2 LOBs: "LOB - L2 Name - Region"
            segment = None
            region_part = parts[2] if len(parts) > 2 else None
        else:
            # For L1 LOBs: "LOB - Channel - Segment - Region"
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
        
        # Check if this is an L2 LOB
        is_l2 = is_l2_header
        
        # Determine region
        region = None
        if region_part == 'KSA':
            region = 'KSA'
        elif region_part == 'Rest of Countries':
            region = 'Rest of Countries'
        
        # Handle Chat & Email split (only for L1 LOBs)
        if not is_l2_header and 'Chat & Email' in channel_part:
            # Create two separate columns: Chat and Email
            for channel in ['Chat', 'Email']:
                new_header = f"{lob_name} - {channel} - {segment} - {region_part}"
                new_idx = len(new_headers)
                new_headers.append(new_header)
                column_mapping[new_idx] = {
                    'lob': lob_type,
                    'channel': channel,
                    'region': region,
                    'segment': segment,
                    'is_l2': False,
                    'old_idx': idx
                }
        else:
            # Single channel column (for L1 LOBs) or L2 LOB column
            channel = None
            if not is_l2_header:
                if 'Chat' in channel_part:
                    channel = 'Chat'
                elif 'Email' in channel_part:
                    channel = 'Email'
                elif 'Phone' in channel_part:
                    channel = 'Phone'
            
            if channel or is_l2:  # Include L2 LOBs even without channel
                new_header = header
                new_idx = len(new_headers)
                new_headers.append(new_header)
                column_mapping[new_idx] = {
                    'lob': lob_type,
                    'channel': channel,
                    'region': region,
                    'segment': segment,
                    'is_l2': is_l2,
                    'old_idx': idx
                }
    
    return new_headers, column_mapping

def get_l1_percentages_for_region(coverage_data: Dict, lob_type: str, region: str) -> List[int]:
    """Get all L1 percentages for a given LOB type and region."""
    percentages = []
    for channel in ['Email', 'Chat', 'Phone']:
        if channel in coverage_data.get(lob_type, {}):
            pct = coverage_data[lob_type][channel].get(region, 0)
            if pct > 0:
                percentages.append(pct)
    return percentages

def process_csv(input_file: str, output_file: str):
    """Process CSV: restructure headers and update LOB columns."""
    print("=" * 80)
    print("PROCESSING CSV - Restructuring and Updating LOB Columns")
    print("=" * 80)
    
    print("\n1. Reading CSV file...")
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        rows = list(reader)
    
    if not rows:
        print("❌ CSV file is empty")
        return
    
    headers = rows[0]
    coverage_col_idx = headers.index('Channels & Coverage')
    
    print("2. Restructuring headers to split Chat & Email...")
    new_headers, column_mapping = restructure_headers(headers)
    print(f"   Original columns: {len(headers)}")
    print(f"   New columns: {len(new_headers)}")
    print(f"   Columns added: {len(new_headers) - len(headers)}")
    
    print("\n3. Processing rows and updating LOB columns...")
    new_rows = [new_headers]
    
    validation_errors = []
    
    for row_idx, row in enumerate(rows[1:], start=2):
        if len(row) <= coverage_col_idx:
            continue
        
        coverage_text = row[coverage_col_idx]
        coverage_data = parse_coverage(coverage_text)
        
        # Create new row
        new_row = row[:8].copy()  # Keep first 8 columns
        
        # Process each new column
        for new_col_idx, col_info in column_mapping.items():
            lob_type = col_info['lob']
            channel = col_info['channel']
            region = col_info['region']
            is_l2 = col_info['is_l2']
            
            value = 'No'
            
            # Handle region mapping
            check_regions = []
            if region == 'Rest of Countries':
                check_regions = ['UAE', 'KSA']
            elif region:
                check_regions = [region]
            
            if is_l2:
                # L2 LOBs: use lowest percentage from L1 LOBs across all channels and regions
                all_l1_percentages = []
                for r in check_regions:
                    percentages = get_l1_percentages_for_region(coverage_data, lob_type, r)
                    all_l1_percentages.extend(percentages)
                percentage = min(all_l1_percentages) if all_l1_percentages else 0
                if percentage > 0:
                    value = f'Yes ({percentage}%)'
            else:
                # L1 LOBs: check specific channel
                if channel:
                    if channel == 'Email':
                        # Email: check ALL regions (UAE and KSA) and use max
                        # Because Email can't be split by country
                        percentages = []
                        for r in ['UAE', 'KSA']:
                            if channel in coverage_data.get(lob_type, {}):
                                pct = coverage_data[lob_type][channel].get(r, 0)
                                if pct > 0:
                                    percentages.append(pct)
                        percentage = max(percentages) if percentages else 0
                        if percentage > 0:
                            value = f'Yes ({percentage}%)'
                    else:
                        # Chat and Phone: region-specific
                        percentages = []
                        for r in check_regions:
                            if channel in coverage_data.get(lob_type, {}):
                                pct = coverage_data[lob_type][channel].get(r, 0)
                                if pct > 0:
                                    percentages.append(pct)
                        percentage = max(percentages) if percentages else 0
                        if percentage > 0:
                            value = f'Yes ({percentage}%)'
            
            new_row.append(value)
        
        new_rows.append(new_row)
        
        # Validation for key waves
        if 'Wave 1a' in row[0] or 'Wave 3a' in row[0]:
            phase = row[0]
            # Validate Email columns are synchronized
            email_cols = {}
            for new_col_idx, col_info in column_mapping.items():
                if col_info['channel'] == 'Email' and col_info['lob'] == 'Partner':
                    region_key = col_info['region']
                    if region_key:
                        header = new_headers[new_col_idx]
                        value = new_row[new_col_idx] if len(new_row) > new_col_idx else 'N/A'
                        if region_key not in email_cols:
                            email_cols[region_key] = []
                        email_cols[region_key].append((header, value))
            
            # Check if all Email columns for Partner Care have same value
            if email_cols:
                all_values = []
                for region_key, cols in email_cols.items():
                    for header, value in cols:
                        all_values.append(value)
                
                if len(set(all_values)) > 1:
                    validation_errors.append(f"{phase}: Partner Care Email columns have different values: {set(all_values)}")
    
    print(f"\n4. Writing updated CSV...")
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(new_rows)
    
    print(f"✅ Successfully restructured and updated CSV")
    print(f"✅ Output saved to: {output_file}")
    print(f"✅ Total rows processed: {len(new_rows) - 1}")
    
    if validation_errors:
        print(f"\n⚠️  Validation Errors Found:")
        for error in validation_errors:
            print(f"   - {error}")
    else:
        print(f"\n✅ No validation errors - all Email columns are correctly synchronized")
    
    return validation_errors == []

if __name__ == "__main__":
    input_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_UPDATED.csv"
    output_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv"
    
    success = process_csv(input_file, output_file)
    
    if success:
        print("\n" + "=" * 80)
        print("RUNNING COMPREHENSIVE VALIDATION...")
        print("=" * 80)
        
        # Run validation script
        import subprocess
        result = subprocess.run(['python3', 'validate_final_csv.py'], 
                              capture_output=True, text=True, cwd='/Users/mohaned.saleh/prd-ticket-agent')
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)













