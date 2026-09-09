import inspect
import app

endpoint = app.app.view_functions.get("api_chat")

print()
print("=" * 70)
print("FULL LIVE /api/chat WRAPPER CHAIN")
print("=" * 70)

depth = 0
seen = set()

while endpoint is not None and id(endpoint) not in seen:
    seen.add(id(endpoint))

    print()
    print(f"DEPTH: {depth}")
    print("FUNCTION:", endpoint)
    print("NAME:", getattr(endpoint, "__name__", None))
    print("MODULE:", getattr(endpoint, "__module__", None))

    try:
        print(
            "FILE:",
            inspect.getsourcefile(endpoint),
        )
        print(
            "LINE:",
            inspect.getsourcelines(endpoint)[1],
        )
    except Exception as error:
        print("SOURCE LOCATION ERROR:", error)

    print("HAS __wrapped__:", hasattr(endpoint, "__wrapped__"))

    endpoint = getattr(
        endpoint,
        "__wrapped__",
        None,
    )

    depth += 1

print()
print("=" * 70)
print("VIEW FUNCTION REGISTRY")
print("=" * 70)

for name, func in app.app.view_functions.items():

    if "chat" in name.lower():

        print()
        print("ENDPOINT NAME:", name)
        print("FUNCTION:", func)
        print("MODULE:", getattr(func, "__module__", None))

        try:
            print(
                "FILE:",
                inspect.getsourcefile(func),
            )
            print(
                "LINE:",
                inspect.getsourcelines(func)[1],
            )
        except Exception:
            pass

print()
print("=" * 70)
print("DONE")
print("=" * 70)
