from nova_backend.config import SESSIONS_FILE, MEMORY_FILE, ARTIFACTS_FILE
from nova_backend.services.chat_service import ChatService
from nova_backend.services.session_service import SessionService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.web_service import WebService
from nova_backend.services.recon_service import ReconService

sessions = SessionService(SESSIONS_FILE)
memory = MemoryService(MEMORY_FILE)
artifacts = ArtifactService(ARTIFACTS_FILE)
web = WebService()
recon = ReconService()

cs = ChatService(
    sessions,
    memory,
    artifacts,
    web,
    recon,
)

print("RANK:", hasattr(cs, "_rank_memory_context"))
print("EXTRACT:", hasattr(cs, "_extract_response_text"))
print("RECON:", hasattr(cs, "_reconcile_execution_state"))

print("DIR SAMPLE:", [x for x in dir(cs) if "_" in x][:50])