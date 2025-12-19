import re

regex = r'\[\s*(?:REPLY|MSG)[^0-9]+(\d+)\s*\]'
strings = [
    "[REPLY-20]",
    "[MSG-20]",
    "[REPLY 20]",
    "[reply-20]",
    " [REPLY-20] ",
    '"[REPLY-20]"',
    "'[REPLY-20]'",
    "[REPLY: 20]",
    "MSG-20]",
    "[MSG-20",
    "[REPLY-20] hello"
]

print(f"Testing Regex: {regex}")
for s in strings:
    match = re.search(regex, s, re.IGNORECASE)
    print(f"'{s}': {match.group(0) if match else 'NO MATCH'}")


