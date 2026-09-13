import subprocess

result = subprocess.run(["python", "runtime_test_task.py"], capture_output=True, text=True)

with open("runtime_test.txt", "w") as f:
    f.write(result.stdout)
