from pathlib import Path

text = Path("static/js/nova-chat-stream.js").read_text(encoding="utf-8")

stack = []

for i, c in enumerate(text):
    if c == "{":
        stack.append(i)
    elif c == "}":
        if stack:
            stack.pop()

print("Remaining opening braces:", len(stack))

for pos in stack:
    print("\nOPEN BRACE AT:", pos)
    print(text[pos-100:pos+150])