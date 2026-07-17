from flask import Flask, session

from nova_backend.services.memory_service import MemoryService


app = Flask(__name__)
app.secret_key = "test"

memory = MemoryService("data/test_memory_ownership.json")


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    saved = memory.add_memory(
        {
            "text": "User A private memory",
            "kind": "fact",
        }
    )

    print("A CREATED:", saved.get("owner_id"))

    visible = memory.all()

    print("A SEES:", visible)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    visible = memory.all()

    print("B SEES BEFORE:", visible)

    saved_b = memory.add_memory(
        {
            "text": "User A private memory",
            "kind": "fact",
        }
    )

    print("B CREATED:", saved_b.get("owner_id"))

    visible_b = memory.all()

    print("B SEES AFTER:", visible_b)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    visible_a = memory.all()

    print("A FINAL:", visible_a)