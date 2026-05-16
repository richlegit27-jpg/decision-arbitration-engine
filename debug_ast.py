import ast

p = r"C:\Users\Owner\nova\nova_backend\services\chat_service.py"

print("READING:", p)

with open(p, encoding="utf-8") as f:
    src = f.read()

print("FILE SIZE:", len(src))
print("HAS TEXT class ChatService:", "class ChatService" in src)
print("HAS TEXT def _execute_general_chat:", "def _execute_general_chat" in src)

tree = ast.parse(src)

print("\nTOP LEVEL NODES:")
for node in tree.body:
    print(type(node).__name__, getattr(node, "name", ""), getattr(node, "lineno", ""))

print("\nCLASS METHODS:")
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == "ChatService":
        print("FOUND ChatService:", node.lineno, node.end_lineno)
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name in ("handle", "_execute_general_chat"):
                    print("METHOD:", item.name, item.lineno, item.end_lineno)