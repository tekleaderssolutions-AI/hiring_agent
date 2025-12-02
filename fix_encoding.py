import codecs

# Read the file with UTF-16LE encoding
with codecs.open('static/index.html', 'r', encoding='utf-16-le') as f:
    content = f.read()

# Write it back with UTF-8 encoding
with codecs.open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("File encoding converted from UTF-16LE to UTF-8 successfully!")
