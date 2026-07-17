from flask import Flask, session

from nova_backend.services.memory_service import MemoryService
from nova_backend.services.session_service import SessionService
from nova_backend.services.artifact_service import ArtifactService

from nova_backend.services.upload_ownership_service import (
    UploadOwnershipService,
)

app = Flask(__name__)
app.secret_key = "test"


memory = MemoryService("data/test_memory_full_wall.json")
sessions = SessionService("data/test_sessions_full_wall.json")
artifacts = ArtifactService("data/test_artifacts_full_wall.json")

uploads = UploadOwnershipService(
    "data/test_upload_ownership_full.json"
)

print("NOVA STORAGE OWNERSHIP FULL SMOKE")
print("=" * 40)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    memory_item = memory.add_memory(
        {
            "text": "User A private memory",
            "kind": "fact",
        }
    )

    session_item = sessions.create(
        title="User A private session",
    )

    artifact_item = artifacts.save_artifact(
        {
            "title": "User A private artifact",
            "kind": "test",
        }
    )

    upload_item = uploads.register_upload(
        "user_a_private_test.png",
        "user_a",
    )

    print("OWNER CREATE:")
    print("MEMORY:", memory_item.get("owner_id"))
    print("SESSION:", session_item.get("user_id"))
    print("ARTIFACT:", artifact_item.get("owner_id"))
    print("UPLOAD:", upload_item.get("owner_id"))

with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    print("\nUSER B WALL:")
    print("MEMORY:", memory.all())
    print("SESSION:", sessions.all())
    print("ARTIFACT:", artifacts.all())

    print(
        "UPLOAD:",
        uploads.belongs_to_user(
            "user_a_private_test.png",
            "user_b",
        ),
    )


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    print("\nUSER B ID ATTACK:")
    print(
        "SESSION GET:",
        sessions.get(session_item["id"]),
    )
    print(
        "SESSION DELETE:",
        sessions.delete(session_item["id"]),
    )
    print(
        "MEMORY GET:",
        memory.get(memory_item["id"]),
    )
    print(
        "MEMORY DELETE:",
        memory.delete_memory(memory_item["id"]),
    )
    print(
        "ARTIFACT VIEW:",
        artifacts.build_view_payload(
            artifact_item["id"]
        ),
    )

with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    print(
        "\nUSER A UPLOAD:",
        uploads.belongs_to_user(
            "user_a_private_test.png",
            "user_a",
        ),
    )

print("\nNOVA STORAGE OWNERSHIP FULL SMOKE PASSED")