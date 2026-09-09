import inspect
import app

fn = app.app.view_functions["api_chat_route"]

print()
print("=" * 70)
print("LIVE CHAT ENDPOINT CLOSURE INSPECTION")
print("=" * 70)

closure = getattr(fn, "__closure__", None)

if not closure:
    print("NO CLOSURE FOUND")
    raise SystemExit(1)

freevars = fn.__code__.co_freevars

for name, cell in zip(freevars, closure):

    print()
    print("-" * 70)
    print("FREE VARIABLE:", name)
    print("-" * 70)

    try:
        value = cell.cell_contents
    except Exception as exc:
        print("CELL ERROR:", exc)
        continue

    print("TYPE:", type(value))
    print("VALUE:", value)

    if callable(value):

        print("NAME:", getattr(value, "__name__", None))
        print(
            "MODULE:",
            getattr(value, "__module__", None),
        )

        try:
            print(
                "FILE:",
                inspect.getsourcefile(value),
            )

            print()
            print("SOURCE:")
            print(inspect.getsource(value))

        except Exception as exc:
            print("SOURCE ERROR:", exc)

print()
print("=" * 70)
print("DONE")
print("=" * 70)
