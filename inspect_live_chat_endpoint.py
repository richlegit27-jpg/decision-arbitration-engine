import inspect
import app

fn = app.app.view_functions["api_chat_route"]

print()
print("=" * 70)
print("LIVE /api/chat FUNCTION")
print("=" * 70)

depth = 0

while fn is not None:

    print()
    print(f"WRAPPER DEPTH: {depth}")
    print("FUNCTION:", fn)
    print("NAME:", getattr(fn, "__name__", None))
    print("MODULE:", getattr(fn, "__module__", None))
    print("FILE:", inspect.getsourcefile(fn))

    try:
        print()
        print("SOURCE:")
        print(inspect.getsource(fn))
    except Exception as e:
        print("SOURCE ERROR:", e)

    wrapped = getattr(fn, "__wrapped__", None)

    if wrapped is None:
        break

    fn = wrapped
    depth += 1

print()
print("=" * 70)
print("DONE")
print("=" * 70)
