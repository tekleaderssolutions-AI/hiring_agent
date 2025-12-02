import re

# Read the corrupted file
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the position where corruption starts (after the outreach tbody opening)
# The corruption starts with </head> tag that shouldn't be there
corruption_start = content.find('</head>', 200)  # Skip the real </head> at the beginning

if corruption_start > 0:
    # Find where the interview section should start
    # Look for the Step 4 comment that comes after outreach
    step4_pattern = r'<!-- Step 4: Interviews -->'
    match = re.search(step4_pattern, content[corruption_start:])
    
    if match:
        # Get the clean part before corruption
        clean_start = content[:corruption_start]
        
        # Close the outreach tbody and table properly
        outreach_close = '''                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        '''
        
        # Get the interview section (from Step 4 onwards)
        interview_section = content[corruption_start + match.start():]
        
        # Combine them
        fixed_content = clean_start + outreach_close + interview_section
        
        # Write the fixed content
        with open('static/index.html', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("HTML file fixed successfully!")
    else:
        print("Could not find Step 4 section")
else:
    print("No corruption found or file is already clean")
