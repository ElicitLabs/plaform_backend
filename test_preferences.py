"""
Test script to verify that preferences are being saved correctly.
"""
import os
import json
from pathlib import Path

def check_preferences_file():
    """Check if the preferences file exists and is valid JSON."""
    pref_file = Path("data/preferences.json")
    
    if not pref_file.exists():
        print(f"Preferences file not found at {pref_file.absolute()}")
        return
    
    try:
        with open(pref_file, 'r') as f:
            data = f.read()
            print(f"Raw file content:\n{data}")
            if not data.strip():
                print("File exists but is empty")
                return
            
            preferences = json.loads(data)
            print(f"Successfully loaded preferences: {len(preferences)} found")
            
            for i, pref in enumerate(preferences):
                print(f"Preference {i+1}: {pref.get('text')} (ID: {pref.get('id')})")
                
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"Error reading file: {e}")

def add_test_preference():
    """Add a test preference to the file."""
    pref_file = Path("data/preferences.json")
    
    # Create directory if it doesn't exist
    pref_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing preferences or start with empty list
    preferences = []
    if pref_file.exists():
        try:
            with open(pref_file, 'r') as f:
                content = f.read().strip()
                if content and content != '{}':
                    preferences = json.loads(content)
        except (json.JSONDecodeError, Exception):
            preferences = []
    
    # Add a test preference
    import uuid
    new_pref = {
        "text": f"Test preference {len(preferences)+1}",
        "source": "test_script",
        "id": str(uuid.uuid4())
    }
    preferences.append(new_pref)
    
    # Save to file
    with open(pref_file, 'w') as f:
        json.dump(preferences, f, indent=2)
        # Ensure file is written to disk
        f.flush()
        os.fsync(f.fileno())
    
    print(f"Added test preference: {new_pref['text']}")
    print(f"Total preferences: {len(preferences)}")

if __name__ == "__main__":
    print("Checking preferences file...")
    check_preferences_file()
    
    add_test = input("\nAdd a test preference? (y/n): ")
    if add_test.lower() == 'y':
        add_test_preference()
        print("\nAfter adding test preference:")
        check_preferences_file() 