#!/usr/bin/env python3
"""
Update LOB columns based on Channels & Coverage information.
Separates Chat from Email and applies percentages correctly.
"""

import csv
import re
from typing import Dict, List, Tuple, Optional

def parse_coverage(coverage_text: str) -> Dict[str, Dict[str, int]]:
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
        # For UAT and Internal testing, set to 100% for all
        result['Customer'] = {'Email': {'UAE': 100, 'KSA': 100}, 'Chat': {'UAE': 100, 'KSA': 100}, 'Phone': {'UAE': 100, 'KSA': 100}}
        result['Partner'] = {'Email': {'UAE': 100, 'KSA': 100}, 'Chat': {'UAE': 100, 'KSA': 100}, 'Phone': {'UAE': 100, 'KSA': 100}}
        result['Partner Onboarding'] = {'Email': {'UAE': 100, 'KSA': 100}, 'Chat': {'UAE': 100, 'KSA': 100}, 'Phone': {'UAE': 100, 'KSA': 100}}
        return result
    
    # Parse individual channel entries
    # Pattern: "- Customer/Partner Email/Chat/Phone UAE/KSA (X% of agents)"
    # Entries can be on separate lines or on the same line separated by " - "
    lines = coverage_text.split('\n')
    entries = []
    for line in lines:
        line = line.strip()
        # Split by " - " to handle multiple entries on same line
        # Pattern: "- Entry1 - Entry2" where each entry starts with "-"
        parts = line.split(' - ')
        for part in parts:
            part = part.strip()
            if part.startswith('-'):
                part = part[1:].strip()  # Remove leading dash
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
            # Both regions
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

def get_column_mapping(headers: List[str]) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Map column headers to LOB type, channel, and region.
    Returns: {column_index: {'lob': 'Customer', 'channel': 'Email', 'region': 'KSA', 'segment': 'Standard'}}
    """
    mapping = {}
    
    for idx, header in enumerate(headers):
        if idx < 8:  # Skip non-LOB columns (Phase, Dates, Objective, Channels & Coverage, Team, Training, Ops Excellence, Ops, Capacity Planning)
            continue
        
        # Parse header structure: "LOB - Channel - Segment - Region"
        # Examples:
        # "Customer Care - Chat & Email - Standard - KSA"
        # "Customer Care - Phone - Standard - Rest of Countries"
        # "Partner Care - Chat & Email - T3 - KSA"
        
        parts = [p.strip() for p in header.split(' - ')]
        if len(parts) < 3:
            continue
        
        lob_name = parts[0]  # "Customer Care", "Partner Care", "Partner Onboarding"
        channel_part = parts[1]  # "Chat & Email", "Phone", or L2 LOB name like "Government & Executive Escalations"
        
        # Check if parts[1] is an L2 LOB name (no channel specified)
        is_l2_header = any(x in channel_part for x in ['Government', 'Executive', 'Trust & Safety', 'Technical Support', 
                                                          'Manager Escalations', 'Collections', 'Finance', 'Risk', 'Integrations'])
        
        if is_l2_header:
            # For L2 LOBs: "LOB - L2 Name - Region"
            segment = None
            region_part = parts[2] if len(parts) > 2 else None  # Region is in parts[2]
        else:
            # For L1 LOBs: "LOB - Channel - Segment - Region"
            segment = parts[2] if len(parts) > 2 else None  # "Standard", "Smart", "T3"
            region_part = parts[3] if len(parts) > 3 else None  # "KSA", "Rest of Countries"
        
        # Determine LOB type
        lob_type = None
        if 'Customer Care' in lob_name:
            lob_type = 'Customer'
        elif 'Partner Onboarding' in lob_name:
            lob_type = 'Partner Onboarding'
        elif 'Partner Care' in lob_name:
            lob_type = 'Partner'
        elif 'Government' in lob_name or 'Executive' in lob_name:
            lob_type = 'Customer'  # L2 LOB, will be handled separately
        elif 'Trust & Safety' in lob_name:
            lob_type = 'Customer'  # L2 LOB
        elif 'Technical Support' in lob_name:
            lob_type = 'Customer'  # L2 LOB
        elif 'Manager Escalations' in lob_name:
            lob_type = 'Customer'  # L2 LOB
        elif 'Collections' in lob_name:
            lob_type = 'Customer'  # L2 LOB
        elif 'Finance' in lob_name:
            lob_type = 'Customer'  # L2 LOB
        elif 'Risk' in lob_name:
            lob_type = 'Customer'  # L2 LOB
        elif 'Integrations' in lob_name:
            lob_type = 'Partner Onboarding'  # L2 LOB
        
        if not lob_type:
            continue
        
        # Determine channel (only for L1 LOBs)
        channel = None
        if not is_l2_header:
            if 'Chat & Email' in channel_part:
                # This needs to be split - we'll handle both
                channel = 'Chat & Email'
            elif 'Chat' in channel_part:
                channel = 'Chat'
            elif 'Email' in channel_part:
                channel = 'Email'
            elif 'Phone' in channel_part:
                channel = 'Phone'
        
        # Determine region
        region = None
        if region_part == 'KSA':
            region = 'KSA'
        elif region_part == 'Rest of Countries':
            # "Rest of Countries" typically refers to UAE in this context
            # But we need to check both UAE and KSA coverage
            region = 'Rest of Countries'  # Special marker to check both
        else:
            region = None
        
        # Check if this is an L2 LOB (already determined above)
        is_l2 = is_l2_header
        
        mapping[idx] = {
            'lob': lob_type,
            'channel': channel,
            'region': region,
            'segment': segment,
            'is_l2': is_l2
        }
    
    return mapping

def get_l1_percentage(coverage_data: Dict, lob_type: str, region: str) -> int:
    """Get the lowest percentage from L1 LOBs for a given LOB type and region."""
    percentages = []
    
    for channel in ['Email', 'Chat', 'Phone']:
        if channel in coverage_data.get(lob_type, {}):
            pct = coverage_data[lob_type][channel].get(region, 0)
            if pct > 0:
                percentages.append(pct)
    
    return min(percentages) if percentages else 0

def update_lob_columns(input_file: str, output_file: str):
    """Update LOB columns based on Channels & Coverage data."""
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        rows = list(reader)
    
    if not rows:
        print("CSV file is empty")
        return
    
    headers = rows[0]
    coverage_col_idx = headers.index('Channels & Coverage')
    column_mapping = get_column_mapping(headers)
    
    print(f"Found {len(column_mapping)} LOB columns to update")
    
    # Process each data row
    for row_idx, row in enumerate(rows[1:], start=2):
        if len(row) <= coverage_col_idx:
            continue
        
        coverage_text = row[coverage_col_idx]
        coverage_data = parse_coverage(coverage_text)
        
        # Update each LOB column
        for col_idx, col_info in column_mapping.items():
            if len(row) <= col_idx:
                # Extend row if needed
                while len(row) <= col_idx:
                    row.append('')
            
            lob_type = col_info['lob']
            channel = col_info['channel']
            region = col_info['region']
            is_l2 = col_info['is_l2']
            
            # Determine value
            value = 'No'
            
            # Handle region mapping
            check_regions = []
            if region == 'Rest of Countries':
                # Check both UAE and KSA, use the higher percentage
                check_regions = ['UAE', 'KSA']
            elif region:
                check_regions = [region]
            else:
                check_regions = []
            
            if is_l2:
                # L2 LOBs: use lowest percentage from L1 LOBs across checked regions
                # Collect all L1 percentages from all channels and regions
                all_l1_percentages = []
                for r in check_regions:
                    for channel in ['Email', 'Chat', 'Phone']:
                        if channel in coverage_data.get(lob_type, {}):
                            pct = coverage_data[lob_type][channel].get(r, 0)
                            if pct > 0:
                                all_l1_percentages.append(pct)
                percentage = min(all_l1_percentages) if all_l1_percentages else 0
                if percentage > 0:
                    value = f'Yes ({percentage}%)'
            else:
                # L1 LOBs: check coverage data
                percentages = []
                for r in check_regions:
                    if channel == 'Chat & Email':
                        # Check both Chat and Email, use the higher one
                        chat_pct = coverage_data.get(lob_type, {}).get('Chat', {}).get(r, 0)
                        email_pct = coverage_data.get(lob_type, {}).get('Email', {}).get(r, 0)
                        pct = max(chat_pct, email_pct)
                        if pct > 0:
                            percentages.append(pct)
                    elif channel in coverage_data.get(lob_type, {}):
                        pct = coverage_data[lob_type][channel].get(r, 0)
                        if pct > 0:
                            percentages.append(pct)
                
                # Use the maximum percentage across regions (for Rest of Countries)
                percentage = max(percentages) if percentages else 0
                if percentage > 0:
                    value = f'Yes ({percentage}%)'
            
            row[col_idx] = value
        
        print(f"Row {row_idx}: Updated LOB columns based on: {coverage_text[:50]}...")
    
    # Write updated CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(rows)
    
    print(f"\n✅ Successfully updated LOB columns")
    print(f"✅ Updated CSV saved to: {output_file}")

if __name__ == "__main__":
    input_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_UPDATED.csv"
    output_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv"
    
    update_lob_columns(input_file, output_file)

