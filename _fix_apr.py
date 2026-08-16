import re

path = r"C:\Users\coemers\Desktop\Finance_Inbox\cloud_deploy\app.py"
content = open(path, encoding='utf-8').read()

# 1. Add a helper function to format APR, right after load_income()
helper = '''

def format_apr(bill):
    """Return a display string for a bill's APR, or empty string if unknown/missing."""
    apr = bill.get('apr')
    if apr is None or apr == "":
        return ""
    if isinstance(apr, (int, float)):
        return f" | {apr}% APR"
    return f" | APR: {apr}"

'''

marker = 'def load_income():'
idx = content.find(marker)
# find end of that function (next blank-line-triple or next top-level construct)
end_idx = content.find('\n\n\n', idx)
if end_idx == -1:
    end_idx = content.find('\n\n', idx)

content = content[:end_idx] + helper + content[end_idx:]

# 2. Update each bill display line in the 4 columns to append format_apr(bill)
targets = [
    (
        "st.success(f\"**{bill['name']}**\\n${bill['amount']:,.2f}\")",
        "st.success(f\"**{bill['name']}**\\n${bill['amount']:,.2f}{format_apr(bill)}\")"
    ),
]

# Also handle the warning/info/error lines which have varying dash characters
# Match any line like: st.warning(f"**{bill['name']}**\n${bill['amount']:,.2f} ... due {bill['day']}th")
pattern = re.compile(
    r'st\.(warning|info|error)\(f"\*\*\{bill\[\'name\'\]\}\*\*\\n\$\{bill\[\'amount\'\]:,\.2f\}[^"]*?due \{bill\[\'day\'\]\}th!?"\)'
)

def add_apr(match):
    original = match.group(0)
    # Insert {format_apr(bill)} right before the closing quote
    return original[:-2] + "{format_apr(bill)}" + original[-2:]

content, n_subs = pattern.subn(add_apr, content)
print(f"Warning/info/error lines updated: {n_subs}")

for old, new in targets:
    if old in content:
        content = content.replace(old, new)
        print("Paid column line updated")
    else:
        print("NOT FOUND: paid column line (may already be updated or different format)")

open(path, 'w', encoding='utf-8').write(content)
print("Done.")
