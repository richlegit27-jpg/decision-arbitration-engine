import subprocess
import sys

tests = [
    ["python", "tools/nova_smoke_test.py"],
    ["python", "tools/nova_attachment_smoke_test.py"],
]

failed = False

print("\nNOVA FULL CHECK")
print("=" * 60)

for command in tests:
    print("\nRUN:", " ".join(command))
    print("-" * 60)

    result = subprocess.run(command)

    if result.returncode != 0:
        failed = True

print("\nFINAL RESULT")
print("=" * 60)

if failed:
    print("FAIL")
    sys.exit(1)

print("PASS")
sys.exit(0)
