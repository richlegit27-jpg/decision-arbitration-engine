from pathlib import Path

path = Path("static/js/mobile/nova-mobile-simple-session-drawer-v1.js")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''                const row = document.createElement("button");

                row.type = "button";
''',
'''                const row = document.createElement("div");

                row.setAttribute("role", "button");
                row.tabIndex = 0;
''',
1
)

text = text.replace(
'''                row.addEventListener("click", function () {
                    openSession(sessionId);
                });
''',
'''                row.addEventListener("click", function () {
                    openSession(sessionId);
                });

                row.addEventListener("keydown", function (event) {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        openSession(sessionId);
                    }
                });
''',
1
)

path.write_text(text, encoding="utf-8")
print("Changed simple session rows from buttons to div role=button.")
