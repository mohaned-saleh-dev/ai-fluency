#!/usr/bin/env python3
"""
Fix wave structure:
1. Ensure Wave 1a and 2a have correct merged titles
2. Remove duplicate Wave 3a and 4a (Email waves)
3. Ensure Wave 3a and 4a are Chat pilot waves
"""

import csv
import re
import os

# Try to find the file
possible_paths = [
    '/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv',
    '/Users/mohaned.saleh/Downloads/Tamara __ Salesforce Testing Guide - Roll-out Timeline_FINAL.csv'
]

input_file = None
for path in possible_paths:
    if os.path.exists(path):
        input_file = path
        break

if not input_file:
    print("❌ Could not find input file")
    exit(1)

output_file = input_file

print("=" * 80)
print("FIXING WAVE STRUCTURE")
print("=" * 80)
print(f"Input: {input_file}")

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

headers = rows[0]
print(f"Read {len(rows)} rows")

# Fix Wave 1a title
for i, row in enumerate(rows):
    if 'Wave 1a' in row[0]:
        if 'UAE + KSA' not in row[0] or 'Partner Care (Email' not in row[0]:
            old = row[0]
            row[0] = "Wave 1a - Partner Care (Email full rollout - UAE + KSA)"
            print(f"\n✅ Fixed Wave 1a:")
            print(f"   Old: {old}")
            print(f"   New: {row[0]}")

# Fix Wave 2a title
for i, row in enumerate(rows):
    if 'Wave 2a' in row[0]:
        if 'UAE + KSA' not in row[0] or 'Customer Care (Email' not in row[0]:
            old = row[0]
            row[0] = "Wave 2a - Customer Care (Email full rollout - UAE + KSA)"
            print(f"\n✅ Fixed Wave 2a:")
            print(f"   Old: {old}")
            print(f"   New: {row[0]}")

# Remove duplicate Email waves (Wave 3a and 4a that are Email)
new_rows = [headers]
removed = []
for row in rows[1:]:
    phase = row[0]
    
    # Remove Wave 3a if it's about Email (duplicate of Wave 1a)
    if 'Wave 3a' in phase and 'Email' in phase:
        print(f"\n❌ Removing duplicate Wave 3a (Email): {phase}")
        removed.append(phase)
        continue
    
    # Remove Wave 4a if it's about Email (duplicate of Wave 2a)
    if 'Wave 4a' in phase and 'Email' in phase:
        print(f"\n❌ Removing duplicate Wave 4a (Email): {phase}")
        removed.append(phase)
        continue
    
    new_rows.append(row)

print(f"\n✅ Removed {len(removed)} duplicate Email waves")

# Verify Wave 3a and 4a are Chat pilot waves
print("\n✅ Verifying Wave 3a and 4a:")
for row in new_rows[1:]:
    if 'Wave 3a' in row[0]:
        print(f"   Wave 3a: {row[0]}")
        if 'Chat' not in row[0] and 'Email' not in row[0]:
            print(f"   ⚠️  Warning: Wave 3a doesn't mention Chat or Email")
    if 'Wave 4a' in row[0]:
        print(f"   Wave 4a: {row[0]}")
        if 'Chat' not in row[0] and 'Email' not in row[0]:
            print(f"   ⚠️  Warning: Wave 4a doesn't mention Chat or Email")

# Write
print(f"\nWriting to: {output_file}")
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(new_rows)

print(f"✅ File updated: {len(new_rows) - 1} rows (removed {len(removed)} waves)")

# Final summary
print("\n" + "=" * 80)
print("FINAL STRUCTURE")
print("=" * 80)
waves = [row[0] for row in new_rows if 'Wave' in row[0]]
for w in waves:
    print(f"  {w}")













