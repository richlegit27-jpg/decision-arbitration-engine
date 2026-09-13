import logging
import time
from typing import Callable, List, Optional

class TaskExecutionError(Exception):
    """Custom exception raised when a task fails during execution."""

class ExecutionFlow:
    """
    Manages the sequential execution of tasks with monitoring and error handling.
    """

    def __init__(self, tasks: List[Callable[[], None]], max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize the execution flow with tasks to run in sequence.

        Args:
            tasks (List[Callable[[], None]]): A list of callable task functions.
            max_retries (int): Maximum number of retries per task before failing.
            retry_delay (int): Delay in seconds between retries.
        """
        self.tasks = tasks
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_task_index = -1

    def execute(self):
        """
        Execute all tasks sequentially, retrying on failure as configured.
        Raises:
            TaskExecutionError: If a task fails after max retries.
        """
        self.logger.info("Starting execution flow for %d tasks.", len(self.tasks))

        for index, task in enumerate(self.tasks):
            self.current_task_index = index
            task_name = getattr(task, '__name__', f'task_{index}')
            self.logger.info("Starting task %d: %s", index + 1, task_name)

            attempt = 0
            while attempt <= self.max_retries:
                try:
                    attempt += 1
                    self.logger.debug("Attempt %d for task %s", attempt, task_name)
                    task()
                    self.logger.info("Completed task %d: %s", index + 1, task_name)
                    break  # Task succeeded, proceed to next
                except Exception as e:
                    self.logger.error("Error on task %s, attempt %d: %s", task_name, attempt, e, exc_info=True)
                    if attempt > self.max_retries:
                        self.logger.error("Task %s failed after %d attempts. Aborting execution.", task_name, attempt - 1)
                        raise TaskExecutionError(f"Task {task_name} failed after {attempt - 1} attempts.") from e
                    else:
                        self.logger.info("Retrying task %s after %d seconds...", task_name, self.retry_delay)
                        time.sleep(self.retry_delay)

        self.logger.info("Execution flow completed successfully.")

if __name__ == "__main__":
    # Configure basic logging to console with time and level info
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Dummy tasks for demonstration
    def task1():
        print("Running Task 1: Data extraction")
    
    def task2():
        print("Running Task 2: Data transformation")
        # Simulate failure once for retry
        if not hasattr(task2, "_has_failed"):
            task2._has_failed = True
            raise RuntimeError("Simulated transient error in task 2")

    def task3():
        print("Running Task 3: Data loading")

    tasks = [task1, task2, task3]

    flow = ExecutionFlow(tasks)
    try:
        flow.execute()
    except TaskExecutionError as err:
        print(f"Execution flow terminated with error: {err}")
