from pathlib import Path

text = Path("templates/app.html").read_text(encoding="utf-8")

depth = 0
in_script = False
line = 1

for i, c in enumerate(text):
    if text[i:i+7] == "<script":
        in_script = True

    if text[i:i+9] == "</script>":
        in_script = False

    if in_script:
        if c == "{":
            depth += 1

        elif c == "}":
            depth -= 1

            if depth < 0:
                print("BAD EXTRA }")
                print("position:", i)
                print("line:", line)
                print(text[i-300:i+300])
                break

    if c == "\n":
        line += 1

print("FINAL DEPTH:", depth)