import inspect
import app

endpoint = app.app.view_functions["api_chat_route"]

print()
print("=" * 70)
print("LIVE /api/chat CLOSURE INSPECTION")
print("=" * 70)

print("LIVE ENDPOINT:", endpoint)
print("MODULE:", endpoint.__module__)
print("NAME:", endpoint.__name__)

closure = getattr(endpoint, "__closure__", None)

if not closure:
    print("NO CLOSURE FOUND")
else:
    print()
    print("CLOSURE CELLS:", len(closure))

    for index, cell in enumerate(closure):

        try:
            value = cell.cell_contents
        except ValueError:
            print(index, "EMPTY CELL")
            continue

        print()
        print("CELL:", index)
        print("TYPE:", type(value))
        print("VALUE:", value)

        if callable(value):

            print("CALLABLE MODULE:",
                  getattr(value, "__module__", None))

            print("CALLABLE NAME:",
                  getattr(value, "__name__", None))

            try:
                print("SOURCE FILE:",
                      inspect.getsourcefile(value))

                print("SOURCE LINE:",
                      inspect.getsourcelines(value)[1])

                print()
                print("SOURCE:")
                print(inspect.getsource(value))

            except Exception as error:
                print("SOURCE ERROR:", error)

print()
print("=" * 70)
print("DONE")
print("=" * 70)
