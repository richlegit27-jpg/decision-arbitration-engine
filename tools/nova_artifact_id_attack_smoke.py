from flask import Flask, session

from nova_backend.services.artifact_service import ArtifactService


app = Flask(__name__)
app.secret_key = "test"

artifacts = ArtifactService("data/test_artifacts_attack.json")


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    created = artifacts.save_artifact(
        {
            "title": "User A Secret Artifact",
            "kind": "test",
        }
    )

    stolen_artifact_id = created["id"]

    print("CREATED:", stolen_artifact_id)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    leaked = artifacts.build_view_payload(
        stolen_artifact_id
    )

    listed = artifacts.all()

    print("USER B VIEW:", leaked)
    print("USER B ALL:", listed)