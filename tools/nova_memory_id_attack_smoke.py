from flask import Flask, session

from nova_backend.services.memory_service import MemoryService


app = Flask(__name__)
app.secret_key = "test"

memory = MemoryService("data/test_memory_attack.json")


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    created = memory.add_memory(
        {
            "text": "User A secret memory",
            "kind": "fact",
        }
    )

    stolen_memory_id = created["id"]

    print("CREATED:", stolen_memory_id)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    leaked = memory.get(stolen_memory_id)
    deleted = memory.delete_memory(stolen_memory_id)

    print("USER B GET:", leaked)
    print("USER B DELETE:", deleted)