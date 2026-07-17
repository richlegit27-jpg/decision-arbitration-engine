from flask import Flask, session

from nova_backend.services.session_service import SessionService


app = Flask(__name__)
app.secret_key = "test"

sessions = SessionService("data/test_sessions_attack.json")


with app.test_request_context("/"):
    session["nova_user_id"] = "user_a"

    created = sessions.create(
        title="User A Secret Chat",
    )

    stolen_session_id = created["id"]

    print("CREATED:", stolen_session_id)


with app.test_request_context("/"):
    session["nova_user_id"] = "user_b"

    leaked = sessions.get(stolen_session_id)
    deleted = sessions.delete(stolen_session_id)

    print("USER B GET:", leaked)
    print("USER B DELETE:", deleted)