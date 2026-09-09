import inspect
import app

print()
print("=" * 70)
print("LIVE FLASK BEFORE_REQUEST HOOKS")
print("=" * 70)

hooks = app.app.before_request_funcs

for blueprint, functions in hooks.items():

    print()
    print("BLUEPRINT:", repr(blueprint))

    for index, func in enumerate(functions):

        print()
        print("INDEX:", index)
        print("FUNCTION:", func)
        print("NAME:", getattr(func, "__name__", None))
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
        except Exception as error:
            print(
                "SOURCE ERROR:",
                error,
            )

print()
print("=" * 70)
print("LIVE WSGI APP")
print("=" * 70)

wsgi = app.app.wsgi_app
depth = 0
seen = set()

while wsgi is not None and id(wsgi) not in seen:

    seen.add(id(wsgi))

    print()
    print("DEPTH:", depth)
    print("WSGI:", wsgi)
    print("TYPE:", type(wsgi))
    print("MODULE:", getattr(
        type(wsgi),
        "__module__",
        None,
    ))

    wrapped = getattr(
        wsgi,
        "__wrapped__",
        None,
    )

    if wrapped is None:
        wrapped = getattr(
            wsgi,
            "app",
            None,
        )

    if wrapped is wsgi:
        break

    wsgi = wrapped
    depth += 1

print()
print("=" * 70)
print("DONE")
print("=" * 70)
