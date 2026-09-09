import inspect
import app

endpoint = app.app.view_functions["api_chat_route"]

print()
print("=" * 70)
print("LIVE API CHAT CLOSURE TRACE")
print("=" * 70)

print()
print("REGISTERED ENDPOINT:")
print(endpoint)
print("MODULE:", endpoint.__module__)
print("FILE:", inspect.getsourcefile(endpoint))

closure = endpoint.__closure__

if not closure:
    print("NO CLOSURE FOUND")
else:
    for index, cell in enumerate(closure):

        try:
            value = cell.cell_contents
        except ValueError:
            print(index, "EMPTY CELL")
            continue

        print()
        print("-" * 70)
        print("CELL:", index)
        print("TYPE:", type(value))
        print("VALUE:", value)

        if callable(value):

            print("CALLABLE NAME:", getattr(value, "__name__", None))
            print("CALLABLE MODULE:", getattr(value, "__module__", None))

            try:
                print(
                    "SOURCE FILE:",
                    inspect.getsourcefile(value),
                )

                print(
                    "SOURCE LINE:",
                    inspect.getsourcelines(value)[1],
                )

                print()
                print("SOURCE:")
                print(inspect.getsource(value))

            except Exception as error:
                print("SOURCE ERROR:", error)

print()
print("=" * 70)
print("DONE")
print("=" * 70)
