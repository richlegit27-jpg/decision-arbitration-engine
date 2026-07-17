from flask import Flask, session

from nova_backend.services.upload_ownership_service import (
    UploadOwnershipService,
)


app = Flask(__name__)
app.secret_key = "test"

uploads = UploadOwnershipService(
    "data/test_upload_ownership.json"
)


filename = "private_test_image.png"


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    uploads.register_upload(
        filename,
        "user_a",
    )


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    print(
        "USER B ACCESS:",
        uploads.belongs_to_user(
            filename,
            "user_b",
        ),
    )


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    print(
        "USER A ACCESS:",
        uploads.belongs_to_user(
            filename,
            "user_a",
        ),
    )