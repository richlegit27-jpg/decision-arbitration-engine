from flask import Flask, session

from nova_backend.services.memory_service import MemoryService
from nova_backend.services.session_service import SessionService
from nova_backend.services.artifact_service import ArtifactService


app = Flask(__name__)
app.secret_key = "test"

memory = MemoryService("data/test_memory_wall.json")
sessions = SessionService("data/test_sessions_wall.json")
artifacts = ArtifactService("data/test_artifacts_wall.json")


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

    print("MEMORY OWNER:", memory_item.get("owner_id"))
    print("SESSION OWNER:", session_item.get("user_id"))
    print("ARTIFACT OWNER:", artifact_item.get("owner_id"))


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    print("MEMORY USER B:", memory.all())
    print(
    "SESSION USER B:",
    sessions.list_sessions(
        user_id="user_b"
    )
)
    print("ARTIFACT USER B:", artifacts.all())