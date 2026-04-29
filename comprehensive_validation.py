#!/usr/bin/env python3
"""
Comprehensive validation of the final CSV to ensure correctness.
"""

import csv

def validate_csv(file_path: str):
    """Comprehensive validation of the CSV file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    headers = rows[0]
    coverage_col_idx = headers.index('Channels & Coverage')
    
    print("=" * 80)
    print("COMPREHENSIVE VALIDATION REPORT")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    # Test Case 1: Wave 1a - Partner Email UAE + KSA
    print("\n📋 Test Case 1: Wave 1a - Partner Email UAE + KSA (100%)")
    print("-" * 80)
    for row in rows[1:]:
        if 'Wave 1a' in row[0]:
            coverage = row[coverage_col_idx]
            print(f"Coverage: {coverage}")
            
            # Check Partner Care Email columns
            partner_email_cols = {}
            for j, h in enumerate(headers):
                if 'Partner Care' in h and 'Email' in h and 'Chat & Email' not in h:
                    if 'KSA' in h:
                        partner_email_cols['KSA'] = row[j] if len(row) > j else 'N/A'
                    elif 'Rest of Countries' in h:
                        partner_email_cols['Rest of Countries'] = row[j] if len(row) > j else 'N/A'
            
            print(f"Partner Care Email columns:")
            for region, value in sorted(partner_email_cols.items()):
                print(f"  {region}: {value}")
            
            if len(set(partner_email_cols.values())) == 1:
                if list(partner_email_cols.values())[0] == 'Yes (100%)':
                    print("✅ PASS: All Partner Care Email columns are Yes (100%)")
                else:
                    errors.append(f"Wave 1a: Partner Care Email should be Yes (100%), got {list(partner_email_cols.values())[0]}")
            else:
                errors.append(f"Wave 1a: Partner Care Email columns have different values: {partner_email_cols}")
            break
    
    # Test Case 2: Wave 3a - Partner Email KSA only
    print("\n📋 Test Case 2: Wave 3a - Partner Email KSA (100%)")
    print("-" * 80)
    for row in rows[1:]:
        if 'Wave 3a' in row[0]:
            coverage = row[coverage_col_idx]
            print(f"Coverage: {coverage}")
            
            # Check Partner Care Email columns - BOTH should be Yes (100%) even though coverage only mentions KSA
            partner_email_cols = {}
            for j, h in enumerate(headers):
                if 'Partner Care' in h and 'Email' in h and 'Chat & Email' not in h:
                    if 'KSA' in h:
                        partner_email_cols['KSA'] = row[j] if len(row) > j else 'N/A'
                    elif 'Rest of Countries' in h:
                        partner_email_cols['Rest of Countries'] = row[j] if len(row) > j else 'N/A'
            
            print(f"Partner Care Email columns:")
            for region, value in sorted(partner_email_cols.items()):
                print(f"  {region}: {value}")
            
            if len(set(partner_email_cols.values())) == 1:
                if list(partner_email_cols.values())[0] == 'Yes (100%)':
                    print("✅ PASS: All Partner Care Email columns are Yes (100%) (synchronized even though coverage only mentions KSA)")
                else:
                    errors.append(f"Wave 3a: Partner Care Email should be Yes (100%), got {list(partner_email_cols.values())[0]}")
            else:
                errors.append(f"Wave 3a: Partner Care Email columns have different values: {partner_email_cols}")
            break
    
    # Test Case 3: Wave 2a - Customer Email UAE
    print("\n📋 Test Case 3: Wave 2a - Customer Email UAE (100%)")
    print("-" * 80)
    for row in rows[1:]:
        if 'Wave 2a' in row[0]:
            coverage = row[coverage_col_idx]
            print(f"Coverage: {coverage}")
            
            # Check Customer Care Email columns - BOTH should be Yes (100%)
            customer_email_cols = {}
            for j, h in enumerate(headers):
                if 'Customer Care' in h and 'Email' in h and 'Chat & Email' not in h and 'Standard' in h:
                    if 'KSA' in h:
                        customer_email_cols['KSA'] = row[j] if len(row) > j else 'N/A'
                    elif 'Rest of Countries' in h:
                        customer_email_cols['Rest of Countries'] = row[j] if len(row) > j else 'N/A'
            
            print(f"Customer Care Email columns (Standard):")
            for region, value in sorted(customer_email_cols.items()):
                print(f"  {region}: {value}")
            
            if len(set(customer_email_cols.values())) == 1:
                if list(customer_email_cols.values())[0] == 'Yes (100%)':
                    print("✅ PASS: All Customer Care Email columns are Yes (100%)")
                else:
                    errors.append(f"Wave 2a: Customer Care Email should be Yes (100%), got {list(customer_email_cols.values())[0]}")
            else:
                errors.append(f"Wave 2a: Customer Care Email columns have different values: {customer_email_cols}")
            break
    
    # Test Case 4: Wave 4a - Customer Email KSA
    print("\n📋 Test Case 4: Wave 4a - Customer Email KSA (100%)")
    print("-" * 80)
    for row in rows[1:]:
        if 'Wave 4a' in row[0]:
            coverage = row[coverage_col_idx]
            print(f"Coverage: {coverage}")
            
            # Check Customer Care Email columns - BOTH should be Yes (100%)
            customer_email_cols = {}
            for j, h in enumerate(headers):
                if 'Customer Care' in h and 'Email' in h and 'Chat & Email' not in h and 'Standard' in h:
                    if 'KSA' in h:
                        customer_email_cols['KSA'] = row[j] if len(row) > j else 'N/A'
                    elif 'Rest of Countries' in h:
                        customer_email_cols['Rest of Countries'] = row[j] if len(row) > j else 'N/A'
            
            print(f"Customer Care Email columns (Standard):")
            for region, value in sorted(customer_email_cols.items()):
                print(f"  {region}: {value}")
            
            if len(set(customer_email_cols.values())) == 1:
                if list(customer_email_cols.values())[0] == 'Yes (100%)':
                    print("✅ PASS: All Customer Care Email columns are Yes (100%)")
                else:
                    errors.append(f"Wave 4a: Customer Care Email should be Yes (100%), got {list(customer_email_cols.values())[0]}")
            else:
                errors.append(f"Wave 4a: Customer Care Email columns have different values: {customer_email_cols}")
            break
    
    # Test Case 5: Verify Chat and Phone remain region-specific
    print("\n📋 Test Case 5: Wave 2d - Chat and Phone should be region-specific")
    print("-" * 80)
    for row in rows[1:]:
        if 'Wave 2d' in row[0]:
            coverage = row[coverage_col_idx]
            print(f"Coverage: {coverage}")
            
            # Check Chat columns
            chat_cols = {}
            phone_cols = {}
            for j, h in enumerate(headers):
                if 'Customer Care' in h and 'Standard' in h:
                    if 'Chat' in h and 'Chat & Email' not in h:
                        if 'KSA' in h:
                            chat_cols['KSA'] = row[j] if len(row) > j else 'N/A'
                        elif 'Rest of Countries' in h:
                            chat_cols['Rest of Countries'] = row[j] if len(row) > j else 'N/A'
                    elif 'Phone' in h:
                        if 'KSA' in h:
                            phone_cols['KSA'] = row[j] if len(row) > j else 'N/A'
                        elif 'Rest of Countries' in h:
                            phone_cols['Rest of Countries'] = row[j] if len(row) > j else 'N/A'
            
            print(f"Chat columns:")
            for region, value in sorted(chat_cols.items()):
                print(f"  {region}: {value}")
            print(f"Phone columns:")
            for region, value in sorted(phone_cols.items()):
                print(f"  {region}: {value}")
            
            # Chat and Phone CAN differ by region (unlike Email)
            if chat_cols.get('Rest of Countries') == 'Yes (100%)' and chat_cols.get('KSA') == 'No':
                print("✅ PASS: Chat is correctly region-specific (UAE=100%, KSA=No)")
            else:
                warnings.append(f"Wave 2d: Chat columns may not be correct: {chat_cols}")
            
            if phone_cols.get('Rest of Countries') == 'Yes (20%)' and phone_cols.get('KSA') == 'No':
                print("✅ PASS: Phone is correctly region-specific (UAE=20%, KSA=No)")
            else:
                warnings.append(f"Wave 2d: Phone columns may not be correct: {phone_cols}")
            break
    
    # Test Case 6: L2 LOBs should reflect lowest L1 percentage
    print("\n📋 Test Case 6: Wave 2d - L2 LOBs should reflect lowest L1 percentage")
    print("-" * 80)
    for row in rows[1:]:
        if 'Wave 2d' in row[0]:
            coverage = row[coverage_col_idx]
            print(f"Coverage: {coverage}")
            
            # Get L1 percentages for Rest of Countries
            l1_percentages = []
            for j, h in enumerate(headers):
                if 'Customer Care' in h and 'Standard' in h and 'Rest of Countries' in h:
                    if 'Chat' in h or 'Email' in h or 'Phone' in h:
                        value = row[j] if len(row) > j else 'No'
                        if 'Yes (' in value:
                            pct = int(value.split('(')[1].split('%')[0])
                            l1_percentages.append(pct)
            
            min_l1 = min(l1_percentages) if l1_percentages else 0
            print(f"L1 percentages: {l1_percentages}")
            print(f"Minimum L1 percentage: {min_l1}%")
            
            # Check L2 LOB
            l2_value = None
            for j, h in enumerate(headers):
                if 'Customer Care' in h and 'Government' in h and 'Rest of Countries' in h:
                    l2_value = row[j] if len(row) > j else 'No'
                    print(f"L2 (Government Escalations): {l2_value}")
            
            if l2_value and f'Yes ({min_l1}%)' in l2_value:
                print(f"✅ PASS: L2 LOB correctly reflects minimum L1 percentage ({min_l1}%)")
            else:
                errors.append(f"Wave 2d: L2 LOB should be Yes ({min_l1}%), got {l2_value}")
            break
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    if errors:
        print(f"❌ ERRORS FOUND: {len(errors)}")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ NO ERRORS FOUND")
    
    if warnings:
        print(f"\n⚠️  WARNINGS: {len(warnings)}")
        for warning in warnings:
            print(f"   - {warning}")
    
    print("\n" + "=" * 80)
    
    return len(errors) == 0

if __name__ == "__main__":
    file_path = "/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv"
    success = validate_csv(file_path)
    exit(0 if success else 1)













