#!/usr/bin/env python3
"""
Restructure CSV to split Chat & Email columns, and update all LOB columns correctly.
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
        region = None
        if 'UAE + KSA' in entry or 'KSA + UAE' in entry:
            result[lob_type][channel]['UAE'] = percentage
            result[lob_type][channel]['KSA'] = percentage
            continue
        elif 'UAE' in entry:
            region = 'UAE'
        elif 'KSA' in entry:
            region = 'KSA'
        
        if region:
            result[lob_type][channel][region] = percentage
    
    return result

def restructure_headers(headers: List[str]) -> Tuple[List[str], Dict[int, Dict]]:
    """
    Restructure headers to split Chat & Email into separate columns.
    Returns new headers and a mapping from old column indices to new structure.
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
                    'is_l2': is_l2,
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
    print("Reading CSV file...")
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        rows = list(reader)
    
    if not rows:
        print("CSV file is empty")
        return
    
    headers = rows[0]
    coverage_col_idx = headers.index('Channels & Coverage')
    
    print("Restructuring headers to split Chat & Email...")
    new_headers, column_mapping = restructure_headers(headers)
    print(f"Original columns: {len(headers)}, New columns: {len(new_headers)}")
    
    print("\nProcessing rows and updating LOB columns...")
    new_rows = [new_headers]
    
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
            old_idx = col_info.get('old_idx', None)
            
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
                    # Special handling for Email: applies to both KSA and Rest of Countries
                    # because emails don't have country information
                    if channel == 'Email':
                        # Check all regions (UAE and KSA) for Email
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
        
        # Validation: Check a few key columns for Wave 2d
        if 'Wave 2d' in row[0]:
            print(f"\n✅ Validation for {row[0]}:")
            print(f"   Coverage: {coverage_text[:60]}...")
            print(f"   Parsed: Customer Chat UAE={coverage_data['Customer']['Chat']['UAE']}%, Phone UAE={coverage_data['Customer']['Phone']['UAE']}%")
            # Find Chat and Email columns for validation
            for new_col_idx, col_info in column_mapping.items():
                if col_info['lob'] == 'Customer' and col_info['region'] == 'Rest of Countries':
                    if col_info['channel'] == 'Chat':
                        print(f"   Customer Chat - Rest of Countries: {new_row[new_col_idx]}")
                    elif col_info['channel'] == 'Email':
                        print(f"   Customer Email - Rest of Countries: {new_row[new_col_idx]}")
                    elif col_info['channel'] == 'Phone':
                        print(f"   Customer Phone - Rest of Countries: {new_row[new_col_idx]}")
                    elif col_info['is_l2'] and 'Government' in new_headers[new_col_idx]:
                        print(f"   Customer Government Escalations - Rest of Countries: {new_row[new_col_idx]}")
    
    print(f"\nWriting updated CSV...")
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(new_rows)
    
    print(f"✅ Successfully restructured and updated CSV")
    print(f"✅ Output saved to: {output_file}")
    print(f"✅ Total rows processed: {len(new_rows) - 1}")

if __name__ == "__main__":
    input_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_UPDATED.csv"
    output_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv"
    
    process_csv(input_file, output_file)

