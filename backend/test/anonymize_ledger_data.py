#!/usr/bin/env python3
"""
Script to anonymize refid and ledger IDs in Kraken ledger JSON files
while maintaining consistency across all files.
"""

import json
import random
import string
import os
from typing import Dict, Set

def generate_anonymized_id(original_id: str, existing_ids: Set[str]) -> str:
    """
    Generate an anonymized ID that maintains the same structure as the original
    and doesn't clash with existing IDs by adding PYTEST- prefix.
    
    Args:
        original_id: The original ID to anonymize
        existing_ids: Set of existing IDs to avoid clashes
        
    Returns:
        Anonymized ID with PYTEST- prefix and same length/character types
    """
    # Generate the anonymized part
    anonymized_part = ""
    for char in original_id:
        if char.isalpha():
            # Replace letters with random letters, maintaining case
            if char.isupper():
                anonymized_part += random.choice(string.ascii_uppercase)
            else:
                anonymized_part += random.choice(string.ascii_lowercase)
        elif char.isdigit():
            # Replace digits with random digits
            anonymized_part += random.choice(string.digits)
        else:
            # Keep special characters (like hyphens) unchanged
            anonymized_part += char
    
    # Always add PYTEST- prefix to ensure no clashes
    result = "PYTEST-" + anonymized_part
    
    # If there's still a clash (very unlikely), add a random suffix
    if result in existing_ids:
        suffix = random.choice(string.ascii_uppercase) + random.choice(string.digits)
        result = result + suffix
    
    return result

def anonymize_ledger_files():
    """Anonymize all ledger files while maintaining consistency."""
    
    files = [
        'backend/test/data/_get_ledger_0.json',
        'backend/test/data/_get_ledger_1.json', 
        'backend/test/data/_get_ledger_2.json',
        'backend/test/data/_get_ledger_3.json'
    ]
    
    # First pass: collect all unique IDs
    all_ids: Set[str] = set()
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Warning: File {file_path} not found, skipping...")
            continue
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Collect refids from ledger entries
        for entry in data['result']['ledger'].values():
            all_ids.add(entry['refid'])
        
        # Collect ledger entry IDs (keys)
        all_ids.update(data['result']['ledger'].keys())
    
    print(f"Found {len(all_ids)} unique IDs to anonymize")
    
    # Create consistent mapping, ensuring no clashes
    id_mapping: Dict[str, str] = {}
    used_ids: Set[str] = set()
    
    for original_id in sorted(all_ids):
        anonymized_id = generate_anonymized_id(original_id, used_ids)
        id_mapping[original_id] = anonymized_id
        used_ids.add(anonymized_id)
    
    # Second pass: anonymize all files and save with new names
    for file_path in files:
        if not os.path.exists(file_path):
            continue
            
        # Create new filename
        base_name = os.path.splitext(file_path)[0]
        new_file_path = f"{base_name}_anonymized.json"
        
        print(f"Anonymizing {file_path} -> {new_file_path}...")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Anonymize ledger entry IDs (keys)
        new_ledger = {}
        for entry_id, entry_data in data['result']['ledger'].items():
            new_entry_id = id_mapping[entry_id]
            new_ledger[new_entry_id] = entry_data.copy()
            # Anonymize refid within the entry
            new_ledger[new_entry_id]['refid'] = id_mapping[entry_data['refid']]
        
        data['result']['ledger'] = new_ledger
        
        # Write to new file
        with open(new_file_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        print(f"  Anonymized {len(new_ledger)} entries")
    
    print("Anonymization complete!")
    
    # Save mapping for reference
    mapping_file = 'backend/test/data/id_mapping.json'
    with open(mapping_file, 'w') as f:
        json.dump(id_mapping, f, indent=4, sort_keys=True)
    print(f"ID mapping saved to {mapping_file}")
    
    # Print summary of new files
    print("\nAnonymized files created:")
    for file_path in files:
        if os.path.exists(file_path):
            base_name = os.path.splitext(file_path)[0]
            new_file_path = f"{base_name}_anonymized.json"
            print(f"  {new_file_path}")

if __name__ == "__main__":
    # Set random seed for reproducible results
    random.seed(42)
    anonymize_ledger_files() 