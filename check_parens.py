from pathlib import Path

text = Path("static/js/nova-chat-stream.js").read_text(encoding="utf-8")

depth = 0

for i, c in enumerate(text):
    if c == "(":
        depth += 1
    elif c == ")":
        depth -= 1

    if depth < 0:
        print("DEPTH WENT NEGATIVE AT:", i)
        print(text[i-200:i+200])
        break
else:
    print("Never negative")
    print("Final depth:", depth)