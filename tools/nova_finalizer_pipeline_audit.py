from pathlib import Path
import re

APP = Path("app.py")

TARGET_TERMS = [
    "response.set_data",
    "Content-Length",
    "Content-Type",
    "assistant_message",
    "attachments",
    "session_attachments",
    "session_id",
    "active_session_id",
    "route_taken",
    "project_state_current_memory_direct_recall",
]

FINALIZER_TERMS = [
    "project_brain_state_recall_refresh",
    "session_response_finalizer",
    "attachment_response_finalizer",
    "project_brain_api_finalizer",
]

def read_lines():
    return APP.read_text(encoding="utf-8-sig").splitlines()

def find_nova_blocks(lines):
    starts = []
    for index, line in enumerate(lines):
        if re.search(r"#\s*NOVA_[A-Z0-9_]+", line):
            starts.append(index)

    blocks = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(lines)
        title = lines[start].strip()
        body = "\n".join(lines[start:end])
        blocks.append({
            "start": start + 1,
            "end": end,
            "size": end - start,
            "title": title,
            "body": body,
        })

    return blocks

def score_block(block):
    body = block["body"]
    lower = body.lower()

    score = 0
    hits = []

    for term in TARGET_TERMS:
        count = lower.count(term.lower())
        if count:
            score += count
            hits.append(f"{term}={count}")

    if "@app.after_request" in body:
        score += 10
        hits.append("after_request=1")

    if "after_request_funcs" in body:
        score += 8
        hits.append("manual_order=1")

    if "response.set_data" in body:
        score += 10

    if "attachments" in lower or "session_attachments" in lower:
        score += 5

    if "session_id" in lower or "active_session_id" in lower:
        score += 5

    if "project_state_current_memory_direct_recall" in lower:
        score += 5

    return score, hits

def main():
    lines = read_lines()
    blocks = find_nova_blocks(lines)

    scored = []
    for block in blocks:
        score, hits = score_block(block)
        if score:
            scored.append((score, hits, block))

    scored.sort(reverse=True, key=lambda item: item[0])

    print("NOVA FINALIZER PIPELINE AUDIT")
    print("=============================")
    print(f"app.py lines: {len(lines)}")
    print(f"NOVA blocks: {len(blocks)}")
    print("")

    print("TOP OVERLAPPING APP.PY MUTATOR BLOCKS")
    print("-------------------------------------")
    for score, hits, block in scored[:30]:
        print(f"{score:4d} | lines {block['start']:5d}-{block['end']:5d} | {block['size']:4d} lines | {block['title']}")
        print(f"     hits: {', '.join(hits[:12])}")

    print("")
    print("LIKELY FINALIZER-OVERLAP BUCKETS")
    print("--------------------------------")
    buckets = {
        "attachment_response": [],
        "session_response": [],
        "project_state_recall": [],
        "generic_json_mutator": [],
    }

    for score, hits, block in scored:
        lower = block["body"].lower()
        title = block["title"]

        if "attachment" in lower or "session_attachments" in lower:
            buckets["attachment_response"].append((score, block))
        if "session_id" in lower or "active_session_id" in lower:
            buckets["session_response"].append((score, block))
        if "project_state_current_memory_direct_recall" in lower or "project_state" in lower:
            buckets["project_state_recall"].append((score, block))
        if "response.set_data" in lower or "content-length" in lower:
            buckets["generic_json_mutator"].append((score, block))

    for name, values in buckets.items():
        print("")
        print(name)
        print("-" * len(name))
        for score, block in values[:12]:
            print(f"{score:4d} | lines {block['start']:5d}-{block['end']:5d} | {block['title']}")

    print("")
    print("RECOMMENDATION")
    print("--------------")
    print("Do not delete a block from this audit alone.")
    print("Pick the smallest high-overlap block, add a dedicated smoke proving behavior, then remove/quarantine one block.")
    print("Best first deletion candidate is usually a small final JSON response mutator, not a giant session or attachment route block.")
    print("")
    print("NOVA FINALIZER PIPELINE AUDIT COMPLETE")

if __name__ == "__main__":
    main()
