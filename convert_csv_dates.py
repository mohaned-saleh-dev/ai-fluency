#!/usr/bin/env python3
"""
Convert dates in CSV file from YYYY-MM-DD to DD/MM/YYYY format.
"""

import csv
import re
from datetime import datetime

def convert_date_format(date_string):
    """
    Convert date from YYYY-MM-DD to DD/MM/YYYY format.
    Handles date ranges like "2026-01-02 → 2026-01-16"
    """
    if not date_string or not date_string.strip():
        return date_string
    
    # Pattern to match dates in YYYY-MM-DD format
    date_pattern = r'(\d{4})-(\d{2})-(\d{2})'
    
    def replace_date(match):
        year, month, day = match.groups()
        return f"{day}/{month}/{year}"
    
    # Replace all dates in the string
    converted = re.sub(date_pattern, replace_date, date_string)
    return converted

def process_csv(input_file, output_file):
    """Process CSV file and convert dates in the Dates column."""
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        rows = list(reader)
    
    if not rows:
        print("CSV file is empty")
        return
    
    # Find the Dates column index
    header = rows[0]
    try:
        dates_col_index = header.index('Dates')
    except ValueError:
        print("Error: 'Dates' column not found in CSV")
        return
    
    print(f"Found 'Dates' column at index {dates_col_index}")
    
    # Convert dates in all rows (skip header)
    converted_count = 0
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > dates_col_index and row[dates_col_index]:
            original = row[dates_col_index]
            converted = convert_date_format(original)
            row[dates_col_index] = converted
            if original != converted:
                converted_count += 1
                print(f"Row {i}: {original} → {converted}")
    
    # Write the updated CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(rows)
    
    print(f"\n✅ Successfully converted {converted_count} date entries")
    print(f"✅ Updated CSV saved to: {output_file}")

if __name__ == "__main__":
    input_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline.csv"
    output_file = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_UPDATED.csv"
    
    process_csv(input_file, output_file)













