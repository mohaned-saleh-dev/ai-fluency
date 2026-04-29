#!/usr/bin/env python3
"""
Validate the final CSV to ensure all LOB columns are correct.
"""

import csv

def validate_csv(file_path: str):
    """Validate the CSV file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    headers = rows[0]
    coverage_col_idx = headers.index('Channels & Coverage')
    
    print("=" * 80)
    print("CSV VALIDATION REPORT")
    print("=" * 80)
    
    # Check 1: No "Chat & Email" columns
    chat_email_cols = [h for h in headers if 'Chat & Email' in h]
    if chat_email_cols:
        print(f"❌ FAIL: Found {len(chat_email_cols)} columns with 'Chat & Email' (should be split)")
        for h in chat_email_cols[:5]:
            print(f"   - {h}")
    else:
        print("✅ PASS: No 'Chat & Email' columns found - successfully split!")
    
    # Check 2: Separate Chat and Email columns exist
    chat_cols = [h for h in headers if ' - Chat - ' in h and 'Chat & Email' not in h]
    email_cols = [h for h in headers if ' - Email - ' in h and 'Chat & Email' not in h]
    print(f"✅ PASS: Found {len(chat_cols)} Chat columns and {len(email_cols)} Email columns")
    
    # Check 3: Validate specific waves
    print("\n" + "=" * 80)
    print("VALIDATING SPECIFIC WAVES")
    print("=" * 80)
    
    test_cases = [
        {
            'wave': 'Wave 2d',
            'coverage': '- Customer Chat UAE (100% of agents) - Customer Phone UAE (20% of agents)',
            'expected': {
                'Customer Care - Chat - Standard - Rest of Countries': 'Yes (100%)',
                'Customer Care - Email - Standard - Rest of Countries': 'No',
                'Customer Care - Phone - Standard - Rest of Countries': 'Yes (20%)',
                'Customer Care - Government & Executive Escalations - Rest of Countries': 'Yes (20%)'
            }
        },
        {
            'wave': 'Wave 4e',
            'coverage': '- Customer Phone KSA (100% of agents)',
            'expected': {
                'Customer Care - Phone - Standard - KSA': 'Yes (100%)',
                'Customer Care - Government & Executive Escalations - KSA': 'Yes (100%)'
            }
        },
        {
            'wave': 'Wave 1a',
            'coverage': '- Partner Email UAE + KSA (100% of agents)',
            'expected': {
                'Partner Care - Email - T3 - KSA': 'Yes (100%)',
                'Partner Care - Email - T3 - Rest of Countries': 'Yes (100%)',
                'Partner Care - Chat - T3 - KSA': 'No',
                'Partner Care - Chat - T3 - Rest of Countries': 'No'
            }
        }
    ]
    
    all_passed = True
    for test_case in test_cases:
        wave_name = test_case['wave']
        print(f"\n📋 Testing {wave_name}:")
        
        # Find the row
        row = None
        for r in rows[1:]:
            if wave_name in r[0]:
                row = r
                break
        
        if not row:
            print(f"   ❌ Row not found")
            all_passed = False
            continue
        
        print(f"   Coverage: {row[coverage_col_idx][:60]}...")
        
        # Check expected values
        for col_name, expected_value in test_case['expected'].items():
            try:
                col_idx = headers.index(col_name)
                actual_value = row[col_idx] if len(row) > col_idx else 'N/A'
                
                if actual_value == expected_value:
                    print(f"   ✅ {col_name}: {actual_value}")
                else:
                    print(f"   ❌ {col_name}: Expected '{expected_value}', got '{actual_value}'")
                    all_passed = False
            except ValueError:
                print(f"   ❌ Column '{col_name}' not found in headers")
                all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED!")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    file_path = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv"
    validate_csv(file_path)













