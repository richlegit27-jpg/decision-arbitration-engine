from time import sleep

def task1_branch1():
    print("Branch1 - Task1: Starting")
    sleep(2)  # Simulate work
    result = "Data from branch1 task1"
    print("Branch1 - Task1: Completed")
    return result

def task2_branch1(input_data):
    print("Branch1 - Task2: Starting with input:", input_data)
    sleep(1)  # Simulate work
    processed_result = f"Processed ({input_data}) in branch1 task2"
    print("Branch1 - Task2: Completed")
    return processed_result

def branch1():
    # First task
    result1 = task1_branch1()
    # Second task depends on the first
    result2 = task2_branch1(result1)
    return result2

if __name__ == "__main__":
    final_result = branch1()
    print("Branch1 final result:", final_result)
