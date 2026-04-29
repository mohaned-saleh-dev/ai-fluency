#!/usr/bin/env python3
"""
Merge Wave 1a and 3a (Partner Email) into single Wave 1a
Merge Wave 2a and 4a (Customer Email) into single Wave 2a
Remove duplicate waves and renumber
"""

import csv
import re

input_file = '/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv'
output_file = '/Users/mohaned.saleh/Downloads/Tamara_Rollout_Timeline_FINAL.csv'

print("=" * 80)
print("MERGING EMAIL WAVES")
print("=" * 80)

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

headers = rows[0]
coverage_idx = headers.index('Channels & Coverage')

print(f"Read {len(rows)} rows")

# Find Wave 1a and Wave 3a
wave_1a_idx = None
wave_3a_idx = None
wave_2a_idx = None
wave_4a_idx = None

for i, row in enumerate(rows):
    if 'Wave 1a' in row[0]:
        wave_1a_idx = i
    elif 'Wave 3a' in row[0]:
        wave_3a_idx = i
    elif 'Wave 2a' in row[0]:
        wave_2a_idx = i
    elif 'Wave 4a' in row[0]:
        wave_4a_idx = i

print(f"\nFound waves:")
print(f"  Wave 1a: row {wave_1a_idx}")
print(f"  Wave 3a: row {wave_3a_idx}")
print(f"  Wave 2a: row {wave_2a_idx}")
print(f"  Wave 4a: row {wave_4a_idx}")

# Merge Wave 1a and 3a
if wave_1a_idx and wave_3a_idx:
    wave_1a = rows[wave_1a_idx]
    wave_3a = rows[wave_3a_idx]
    
    # Update Wave 1a to include both UAE and KSA
    # Merge coverage text
    coverage_1a = wave_1a[coverage_idx]
    coverage_3a = wave_3a[coverage_idx]
    
    # Wave 1a should mention both regions
    new_coverage_1a = "- Partner Email UAE + KSA (100% of agents)"
    
    # Merge team info if needed
    team_1a = wave_1a[4] if len(wave_1a) > 4 else ''
    team_3a = wave_3a[4] if len(wave_3a) > 4 else ''
    new_team = f"{team_1a} + {team_3a}" if team_3a and team_3a != team_1a else team_1a
    
    # Update Wave 1a
    new_wave_1a = wave_1a.copy()
    new_wave_1a[0] = "Wave 1a - Partner Care (Email full rollout - UAE + KSA)"
    new_wave_1a[3] = new_coverage_1a
    new_wave_1a[4] = new_team
    
    # Update dates to span both
    dates_1a = wave_1a[1] if len(wave_1a) > 1 else ''
    dates_3a = wave_3a[1] if len(wave_3a) > 1 else ''
    # Extract dates and merge
    if '→' in dates_1a and '→' in dates_3a:
        start_1a = dates_1a.split('→')[0].strip()
        end_3a = dates_3a.split('→')[1].strip()
        new_wave_1a[1] = f"{start_1a} → {end_3a}"
    
    rows[wave_1a_idx] = new_wave_1a
    print(f"\n✅ Merged Wave 1a and 3a into Wave 1a")
    print(f"   New coverage: {new_coverage_1a}")
    print(f"   New dates: {new_wave_1a[1]}")

# Merge Wave 2a and 4a
if wave_2a_idx and wave_4a_idx:
    wave_2a = rows[wave_2a_idx]
    wave_4a = rows[wave_4a_idx]
    
    # Update Wave 2a to include both UAE and KSA
    new_coverage_2a = "- Customer Email UAE + KSA (100% of agents)"
    
    team_2a = wave_2a[4] if len(wave_2a) > 4 else ''
    team_4a = wave_4a[4] if len(wave_4a) > 4 else ''
    new_team = f"{team_2a} + {team_4a}" if team_4a and team_4a != team_2a else team_2a
    
    # Update Wave 2a
    new_wave_2a = wave_2a.copy()
    new_wave_2a[0] = "Wave 2a - Customer Care (Email full rollout - UAE + KSA)"
    new_wave_2a[3] = new_coverage_2a
    new_wave_2a[4] = new_team
    
    # Merge dates
    dates_2a = wave_2a[1] if len(wave_2a) > 1 else ''
    dates_4a = wave_4a[1] if len(wave_4a) > 1 else ''
    if '→' in dates_2a and '→' in dates_4a:
        start_2a = dates_2a.split('→')[0].strip()
        end_4a = dates_4a.split('→')[1].strip()
        new_wave_2a[1] = f"{start_2a} → {end_4a}"
    
    rows[wave_2a_idx] = new_wave_2a
    print(f"\n✅ Merged Wave 2a and 4a into Wave 2a")
    print(f"   New coverage: {new_coverage_2a}")
    print(f"   New dates: {new_wave_2a[1]}")

# Remove Wave 3a and 4a, and renumber subsequent waves
print(f"\nRemoving Wave 3a and 4a, and renumbering...")

new_rows = [headers]
wave_num = 1

for i, row in enumerate(rows[1:], start=1):
    phase = row[0]
    
    # Skip Wave 3a and 4a
    if 'Wave 3a' in phase or 'Wave 4a' in phase:
        print(f"  Removing: {phase}")
        continue
    
    # Renumber waves after removal
    if 'Wave' in phase:
        # Extract wave number and letter
        match = re.search(r'Wave (\d+)([a-z])', phase)
        if match:
            old_num = int(match.group(1))
            letter = match.group(2)
            
            # Renumber: 3b->2b, 3c->2c, etc. and 4b->3b, 4c->3c, etc.
            if old_num == 3:
                new_num = 2
            elif old_num == 4:
                new_num = 3
            else:
                new_num = old_num
            
            # Update phase name
            new_phase = re.sub(r'Wave \d+([a-z])', f'Wave {new_num}{letter}', phase)
            row[0] = new_phase
            
            # Update "go/no-go to Wave X" references
            if len(row) > len(headers) - 1:
                last_col = row[-1] if len(row) > 0 else ''
                if 'go/no-go to Wave' in last_col:
                    # Update the reference
                    ref_match = re.search(r'go/no-go to Wave (\d+)([a-z])', last_col)
                    if ref_match:
                        ref_num = int(ref_match.group(1))
                        ref_letter = ref_match.group(2)
                        if ref_num == 3:
                            new_ref_num = 2
                        elif ref_num == 4:
                            new_ref_num = 3
                        else:
                            new_ref_num = ref_num
                        row[-1] = re.sub(r'go/no-go to Wave \d+[a-z]', f'go/no-go to Wave {new_ref_num}{ref_letter}', last_col)
    
    new_rows.append(row)

print(f"\nNew row count: {len(new_rows) - 1} (removed 2 waves)")

# Write output
print(f"\nWriting to: {output_file}")
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(new_rows)

print(f"✅ Complete!")
print(f"   Original rows: {len(rows) - 1}")
print(f"   New rows: {len(new_rows) - 1}")

# Validate
print("\nValidating merged waves...")
for row in new_rows[1:]:
    phase = row[0]
    if 'Wave 1a' in phase:
        print(f"✅ {phase}")
        print(f"   Coverage: {row[3] if len(row) > 3 else 'N/A'}")
    elif 'Wave 2a' in phase:
        print(f"✅ {phase}")
        print(f"   Coverage: {row[3] if len(row) > 3 else 'N/A'}")













