# Replace emojis with simple text in HTML file
with open('temp_clean.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace emojis with simple text symbols
replacements = {
    '👨‍💼': 'ADMIN',
    '🎯': 'TARGET',
    '📧': 'EMAIL',
    '📅': 'CALENDAR',
    '🧠': 'AI',
    '🎯': 'GOAL'
}

for emoji, text in replacements.items():
    content = content.replace(emoji, text)

# Write to index.html
with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Emojis replaced with text successfully!")
