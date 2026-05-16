from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

bridge = '''

# ============================================================
# CHAT SERVICE METHOD BRIDGE
# Repairs methods that were accidentally defined outside class.
# ============================================================
try:
    for _name, _obj in list(globals().items()):
        if (
            callable(_obj)
            and isinstance(_name, str)
            and _name.startswith("_")
            and not _name.startswith("__")
            and not hasattr(ChatService, _name)
        ):
            setattr(ChatService, _name, _obj)
except Exception:
    pass
'''

if "CHAT SERVICE METHOD BRIDGE" not in s:
    s = s.rstrip() + bridge + "\n"

p.write_text(s, encoding="utf-8")
print("PATCHED_METHOD_BRIDGE")
