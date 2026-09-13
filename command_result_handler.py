import logging
import time
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

class CommandResultHandler:
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        escalate_function: Optional[Callable[[Any], None]] = None,
    ):
        """
        Initialize the command result handler with retry policies and escalation.

        Args:
            max_retries (int): Maximum number of retries before escalation.
            retry_delay (float): Delay between retries in seconds.
            escalate_function (Callable[[Any], None], optional): 
                Function to call to escalate the error if retries fail.
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.escalate_function = escalate_function

    def handle_result(self, command_func: Callable, *args, **kwargs) -> Any:
        """
        Executes a command function and handles its result including retries and error handling.

        Args:
            command_func (Callable): The command function to execute.
            *args: Positional arguments for the command function.
            **kwargs: Keyword arguments for the command function.

        Returns:
            Any: The result of the command function if successful.

        Raises:
            Exception: Propagates the final exception if all retries fail and escalation is not successful.
        """
        attempt = 0
        while attempt <= self.max_retries:
            try:
                result = command_func(*args, **kwargs)
                if self._is_error(result):
                    error_msg = f"Command returned error result: {result}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                logger.debug(f"Command succeeded on attempt {attempt + 1} with result: {result}")
                return result
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed with error: {e}")
                attempt += 1
                if attempt > self.max_retries:
                    logger.error("Max retries exceeded.")
                    if self.escalate_function:
                        try:
                            logger.info("Escalating error.")
                            self.escalate_function(e)
                        except Exception as esc_e:
                            logger.error(f"Escalation failed with error: {esc_e}")
                    raise
                else:
                    logger.info(f"Retrying after {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)

    def _is_error(self, result: Any) -> bool:
        """
        Determines if the result indicates an error.

        Args:
            result (Any): The result to check.

        Returns:
            bool: True if the result indicates an error, False otherwise.
        """
        # Example error check:
        # Assume result is a dict and contains an 'error' key when an error occurred.
        if isinstance(result, dict) and result.get("error"):
            return True
        return False
