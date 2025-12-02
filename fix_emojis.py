
import os
import sys

# Set stdout to utf-8 to handle printing special characters if possible, 
# but better to just avoid printing them directly if it causes issues.
sys.stdout.reconfigure(encoding='utf-8')

file_path = 'static/index.html'

# Read the file
with open(file_path, 'rb') as f:
    content = f.read()

try:
    text_content = content.decode('utf-8')
    
    # Replacement map
    replacements = {
        '≡ƒöä': '🔄'
    }
    
    new_content = text_content
    changes_made = False
    
    for corrupted, correct in replacements.items():
        if corrupted in new_content:
            print(f"Found corrupted sequence, replacing with correct emoji.")
            new_content = new_content.replace(corrupted, correct)
            changes_made = True
        else:
            print(f"Could not find corrupted sequence.")
            
    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully updated index.html")
    else:
        print("No changes made.")

except Exception as e:
    print(f"Error: {e}")
