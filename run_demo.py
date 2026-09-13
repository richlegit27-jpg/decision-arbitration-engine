import threading
import time

def branch1_task1():
    print("Branch 1 - Task 1 started.")
    time.sleep(1)
    print("Branch 1 - Task 1 completed.")

def branch1_task2():
    print("Branch 1 - Task 2 started.")
    time.sleep(1)
    print("Branch 1 - Task 2 completed.")

def branch2_task1():
    print("Branch 2 - Task 1 started.")
    time.sleep(1)
    print("Branch 2 - Task 1 completed.")

def branch2_task2():
    print("Branch 2 - Task 2 started.")
    time.sleep(1)
    print("Branch 2 - Task 2 completed.")

def final_task():
    print("Final task started.")
    time.sleep(1)
    print("Final task completed.")

def run_branch1():
    branch1_task1()
    branch1_task2()

def run_branch2():
    branch2_task1()
    branch2_task2()

def main():
    # Start branch 1 and branch 2 in parallel
    thread1 = threading.Thread(target=run_branch1)
    thread2 = threading.Thread(target=run_branch2)

    thread1.start()
    thread2.start()

    # Wait for both branches to complete before final task
    thread1.join()
    thread2.join()

    # Run final task
    final_task()

if __name__ == "__main__":
    main()
