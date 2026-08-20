import re

with open("static/style.css", "r") as f:
    css = f.read()

# Replace transition: all with more performant specific transitions
css = re.sub(r'transition:\s*all\s+(var\(--transition-[a-z]+\));', r'transition: transform \1, opacity \1, background \1, border-color \1, box-shadow \1;', css)
css = re.sub(r'transition:\s*all\s+([^;]+);', r'transition: transform \1, opacity \1, background \1, border-color \1, box-shadow \1;', css)

# Optimize backdrop filters: reduce blur radius or remove from heavy elements if necessary
# Let's reduce heavy blurs (e.g. 24px/25px) to 12px for better performance
css = re.sub(r'blur\(2[45]px\)', 'blur(12px)', css)
css = re.sub(r'blur\(20px\)', 'blur(10px)', css)

with open("static/style.css", "w") as f:
    f.write(css)

print("CSS optimized.")
