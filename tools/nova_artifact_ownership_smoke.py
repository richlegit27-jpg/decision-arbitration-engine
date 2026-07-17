from flask import Flask, session

from nova_backend.services.artifact_service import ArtifactService


app = Flask(__name__)
app.secret_key = "test"

service = ArtifactService("data/test_artifacts_ownership.json")


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    saved = service.save_artifact(
        {
            "title": "User A Artifact",
            "kind": "test",
        }
    )

    artifact_id = saved["id"]

    print("A CREATED:", saved.get("owner_id"))
    print("ARTIFACT ID:", artifact_id)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    visible = service.all()

    print("B SEES BEFORE:", visible)

    hacked = service.save_artifact(
        {
            "id": artifact_id,
            "title": "User B Replacement Attempt",
            "kind": "test",
        }
    )

    print("B SAVED:", hacked.get("owner_id"))

    visible_b = service.all()

    print("B FINAL:", visible_b)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    visible_a = service.all()

    print("A FINAL:", visible_a)

with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    deleted = service.delete_artifact(artifact_id)

    print("B DELETE RESULT:", deleted)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    after_delete = service.all()

    print("A AFTER DELETE:", after_delete)