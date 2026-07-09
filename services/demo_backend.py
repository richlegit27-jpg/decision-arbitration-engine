# =========================================================
# Nova Ultimate 2026 Phase 6
# Demo backend to pre-populate memory and artifacts
# =========================================================

from datetime import datetime, timezone

# Sample memory items
DEMO_MEMORY = [
    {"id": "mem1", "content": "User prefers dark theme", "kind": "preference", "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": "mem2", "content": "Project Nova endgame demo", "kind": "project", "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": "mem3", "content": "Frequent command: Build portable zip", "kind": "workflow", "created_at": datetime.now(timezone.utc).isoformat()},
]

# Sample artifacts
DEMO_ARTIFACTS = [
    {"id": "art1", "title": "Sample Output 1", "type": "document", "created_at": datetime.now(timezone.utc).isoformat(), "content": "This is a demo artifact."},
    {"id": "art2", "title": "Sample Code Snippet", "type": "code", "created_at": datetime.now(timezone.utc).isoformat(), "content": "print('Hello Nova Phase 6!')"},
]

# Functions to simulate backend API
def get_memory():
    return DEMO_MEMORY

def get_artifacts():
    return DEMO_ARTIFACTS

def get_messages():
    return [
        {"id": "msg1", "role": "user", "content": "Hello Nova!", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": "msg2", "role": "assistant", "content": "Hi! This is a Phase 6 demo message.", "created_at": datetime.now(timezone.utc).isoformat()},
    ]

def get_sessions():
    return [
        {"id": "sess1", "title": "Demo Session", "created_at": datetime.now(timezone.utc).isoformat(), "messages": get_messages()},
    ]

