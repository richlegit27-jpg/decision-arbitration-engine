import unittest
from unittest.mock import MagicMock, patch, call
import asyncio

# Assuming command_result_handler is the module to be tested
# and it contains CommandResultHandler class or functions to handle command results.
# Since the code is not provided, this is a conceptual test suite.

# Mocks/stubs for command result handler components
class DummyNotificationService:
    def __init__(self):
        self.notifications = []

    def notify_success(self, message):
        self.notifications.append(('success', message))

    def notify_failure(self, message):
        self.notifications.append(('failure', message))

    def notify_warning(self, message):
        self.notifications.append(('warning', message))


class DummyLogger:
    def __init__(self):
        self.logs = []

    def info(self, message):
        self.logs.append(('info', message))

    def warning(self, message):
        self.logs.append(('warning', message))

    def error(self, message):
        self.logs.append(('error', message))


class DummyCommandResultHandler:
    """
    A dummy class to imitate command result handler behavior,
    to allow tests to carry on with known behavior.
    This should be replaced with actual import in real tests.
    """
    def __init__(self, notifier=None, logger=None):
        self.notifier = notifier or DummyNotificationService()
        self.logger = logger or DummyLogger()

    def handle_result(self, result):
        # Result dict expected keys: status, output, error, warnings
        if not isinstance(result, dict):
            raise ValueError("Result must be a dict")

        status = result.get("status")
        if status == "success":
            self.logger.info("Command succeeded.")
            self.notifier.notify_success(f"Success: {result.get('output', '')}")
            return True
        elif status == "failure":
            self.logger.error(f"Command failed with error: {result.get('error', '')}")
            self.notifier.notify_failure(f"Failure: {result.get('error', '')}")
            return False
        elif status == "warning":
            self.logger.warning(f"Command completed with warnings: {result.get('warnings', '')}")
            self.notifier.notify_warning(f"Warning: {result.get('warnings', '')}")
            return True
        else:
            self.logger.error("Unknown command status.")
            raise ValueError("Unknown command status")

    async def handle_result_async(self, result):
        # Simulate some async processing before calls
        await asyncio.sleep(0)
        return self.handle_result(result)


class TestCommandResultHandler(unittest.TestCase):

    def setUp(self):
        self.notifier = DummyNotificationService()
        self.logger = DummyLogger()
        self.handler = DummyCommandResultHandler(self.notifier, self.logger)

    def test_handle_success_result(self):
        result = {"status": "success", "output": "All good"}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('info', "Command succeeded."), self.logger.logs)
        self.assertIn(('success', "Success: All good"), self.notifier.notifications)

    def test_handle_failure_result(self):
        result = {"status": "failure", "error": "Fatal error occurred"}
        ret = self.handler.handle_result(result)
        self.assertFalse(ret)
        self.assertIn(('error', "Command failed with error: Fatal error occurred"), self.logger.logs)
        self.assertIn(('failure', "Failure: Fatal error occurred"), self.notifier.notifications)

    def test_handle_warning_result(self):
        result = {"status": "warning", "warnings": "Minor issues detected"}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('warning', "Command completed with warnings: Minor issues detected"), self.logger.logs)
        self.assertIn(('warning', "Warning: Minor issues detected"), self.notifier.notifications)

    def test_handle_unknown_status_raises(self):
        result = {"status": "unknown", "output": ""}
        with self.assertRaises(ValueError) as cm:
            self.handler.handle_result(result)
        self.assertEqual(str(cm.exception), "Unknown command status")
        self.assertIn(('error', "Unknown command status."), self.logger.logs)

    def test_handle_result_with_non_dict_raises(self):
        with self.assertRaises(ValueError) as cm:
            self.handler.handle_result("not a dict")
        self.assertEqual(str(cm.exception), "Result must be a dict")

    def test_handle_result_missing_status_key_raises(self):
        result = {"output": "missing status"}
        with self.assertRaises(ValueError) as cm:
            self.handler.handle_result(result)
        self.assertEqual(str(cm.exception), "Unknown command status")
        self.assertIn(('error', "Unknown command status."), self.logger.logs)

    def test_handle_empty_success_output(self):
        result = {"status": "success"}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('success', "Success: "), self.notifier.notifications)

    def test_handle_empty_failure_error(self):
        result = {"status": "failure"}
        ret = self.handler.handle_result(result)
        self.assertFalse(ret)
        self.assertIn(('failure', "Failure: "), self.notifier.notifications)

    def test_handle_empty_warning_warnings(self):
        result = {"status": "warning"}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('warning', "Warning: "), self.notifier.notifications)

    @patch('asyncio.sleep', return_value=None)
    def test_handle_result_async_success(self, mock_sleep):
        result = {"status": "success", "output": "Async success"}
        loop = asyncio.new_event_loop()
        ret = loop.run_until_complete(self.handler.handle_result_async(result))
        self.assertTrue(ret)
        self.assertIn(('success', "Success: Async success"), self.notifier.notifications)
        loop.close()

    @patch('asyncio.sleep', return_value=None)
    def test_handle_result_async_failure(self, mock_sleep):
        result = {"status": "failure", "error": "Async failure"}
        loop = asyncio.new_event_loop()
        ret = loop.run_until_complete(self.handler.handle_result_async(result))
        self.assertFalse(ret)
        self.assertIn(('failure', "Failure: Async failure"), self.notifier.notifications)
        loop.close()

    def test_multiple_notifications(self):
        # Simulate sequence of command results
        results = [
            {"status": "success", "output": "Step 1"},
            {"status": "warning", "warnings": "Step 2 warning"},
            {"status": "failure", "error": "Step 3 error"},
        ]
        results_status = []
        for r in results:
            try:
                res = self.handler.handle_result(r)
                results_status.append(res)
            except Exception:
                results_status.append('exception')

        self.assertEqual(results_status, [True, True, False])
        # Check notifications captured correctly in order
        expected_notifications = [
            ('success', "Success: Step 1"),
            ('warning', "Warning: Step 2 warning"),
            ('failure', "Failure: Step 3 error"),
        ]
        self.assertEqual(self.notifier.notifications, expected_notifications)

    def test_handler_removes_sensitive_info(self):
        # Test that handler does not include sensitive info in notifications/logs (edge case)
        # This assumes handler tries to mask sensitive keys
        class SecureHandler(DummyCommandResultHandler):
            def handle_result(self, result):
                # Mask any value associated with keys 'password' or 'token'
                safe_result = result.copy()
                for key in ['password', 'token']:
                    if key in safe_result:
                        safe_result[key] = '***MASKED***'
                return super().handle_result(safe_result)

        secure_handler = SecureHandler(self.notifier, self.logger)
        result = {"status": "failure", "error": "Bad credentials", "password": "secretpass"}
        ret = secure_handler.handle_result(result)

        self.assertFalse(ret)
        # Ensure masked password does not appear in logs or notifications
        failure_msgs = [msg for k, msg in self.notifier.notifications if k == 'failure']
        self.assertTrue(all('secretpass' not in m for m in failure_msgs))

        error_logs = [msg for k, msg in self.logger.logs if k == 'error']
        self.assertTrue(all('secretpass' not in m for m in error_logs))

    def test_handle_result_with_extra_unexpected_keys(self):
        # Extra keys should be ignored safely
        result = {
            "status": "success",
            "output": "Extra info here",
            "unexpected_key": "unexpected_value",
            "another_one": 12345
        }
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('success', "Success: Extra info here"), self.notifier.notifications)

    def test_handle_result_with_null_values(self):
        # Null or None outputs should be handled gracefully
        result = {"status": "success", "output": None}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('success', "Success: None"), self.notifier.notifications)

    def test_handle_result_large_output(self):
        # Test handling very large output
        large_output = "x" * 10_000
        result = {"status": "success", "output": large_output}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        found = False
        for note_type, msg in self.notifier.notifications:
            if note_type == 'success' and msg.endswith(large_output[-10:]):
                found = True
        self.assertTrue(found)

    def test_handle_result_unicode_output(self):
        # Ensure unicode characters are handled properly
        unicode_output = "✓ All tests passed 🚀"
        result = {"status": "success", "output": unicode_output}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('success', f"Success: {unicode_output}"), self.notifier.notifications)

    def test_handle_result_warning_without_warnings_key(self):
        # Warning status with missing warnings key should default to empty
        result = {"status": "warning"}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('warning', "Warning: "), self.notifier.notifications)
        self.assertIn(('warning', "Command completed with warnings: "), self.logger.logs)

    def test_handle_result_failure_with_non_string_error(self):
        # error key is not string (e.g. list), handler should convert to string
        result = {"status": "failure", "error": ["error1", "error2"]}
        ret = self.handler.handle_result(result)
        self.assertFalse(ret)
        self.assertIn(('failure', "Failure: ['error1', 'error2']"), self.notifier.notifications)
        self.assertIn(('error', "Command failed with error: ['error1', 'error2']"), self.logger.logs)

    def test_handle_result_success_with_non_string_output(self):
        # output key not string (e.g. dict), handler should convert to string
        result = {"status": "success", "output": {"key": "value"}}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('success', "Success: {'key': 'value'}"), self.notifier.notifications)
        self.assertIn(('info', "Command succeeded."), self.logger.logs)

    def test_handle_result_warning_with_non_string_warnings(self):
        # warnings key not string (e.g. list), handler should convert to string
        result = {"status": "warning", "warnings": [1, 2, 3]}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('warning', "Warning: [1, 2, 3]"), self.notifier.notifications)
        self.assertIn(('warning', "Command completed with warnings: [1, 2, 3]"), self.logger.logs)

    def test_handle_result_unicode_error_message(self):
        unicode_error = "Error: Не удалось выполнить команду"
        result = {"status": "failure", "error": unicode_error}
        ret = self.handler.handle_result(result)
        self.assertFalse(ret)
        self.assertIn(('failure', f"Failure: {unicode_error}"), self.notifier.notifications)
        self.assertIn(('error', f"Command failed with error: {unicode_error}"), self.logger.logs)

    def test_handle_result_with_empty_dict(self):
        # No status key at all should raise
        result = {}
        with self.assertRaises(ValueError) as cm:
            self.handler.handle_result(result)
        self.assertEqual(str(cm.exception), "Unknown command status")
        self.assertIn(('error', "Unknown command status."), self.logger.logs)

    def test_handle_result_with_none_input(self):
        with self.assertRaises(ValueError) as cm:
            self.handler.handle_result(None)
        self.assertEqual(str(cm.exception), "Result must be a dict")

    def test_handle_result_async_raises_for_invalid_result(self):
        loop = asyncio.new_event_loop()
        with self.assertRaises(ValueError):
            loop.run_until_complete(self.handler.handle_result_async("invalid"))
        loop.close()

    def test_handle_result_with_overflowing_messages(self):
        # Very long warning message
        long_warning = "warning " * 2000
        result = {"status": "warning", "warnings": long_warning}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertTrue(any(long_warning in msg for k, msg in self.notifier.notifications if k == 'warning'))

    def test_handle_result_called_multiple_times_resets_notifications(self):
        # Confirm notifications accumulate, test handler re-instantiation resets notifier
        result1 = {"status": "success", "output": "First output"}
        self.handler.handle_result(result1)
        self.assertIn(('success', "Success: First output"), self.notifier.notifications)

        result2 = {"status": "failure", "error": "Second error"}
        self.handler.handle_result(result2)
        self.assertIn(('failure', "Failure: Second error"), self.notifier.notifications)

        new_notifier = DummyNotificationService()
        new_handler = DummyCommandResultHandler(new_notifier, self.logger)
        self.assertEqual(new_notifier.notifications, [])

    def test_handle_result_with_boolean_output(self):
        # output is boolean True/False
        result = {"status": "success", "output": True}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('success', "Success: True"), self.notifier.notifications)

    def test_handle_result_with_empty_strings(self):
        result = {"status": "failure", "error": ""}
        ret = self.handler.handle_result(result)
        self.assertFalse(ret)
        self.assertIn(('failure', "Failure: "), self.notifier.notifications)

    def test_handle_result_with_numeric_error_output(self):
        result = {"status": "failure", "error": 404}
        ret = self.handler.handle_result(result)
        self.assertFalse(ret)
        self.assertIn(('failure', "Failure: 404"), self.notifier.notifications)

    def test_handle_result_with_nested_dict_in_output(self):
        result = {"status": "success", "output": {"key1": "value1", "key2": 2}}
        ret = self.handler.handle_result(result)
        self.assertTrue(ret)
        self.assertIn(('success', "Success: {'key1': 'value1', 'key2': 2}"), self.notifier.notifications)

    def test_handle_result_with_status_case_sensitivity(self):
        # Status is case sensitive, should raise for 'Success' instead of 'success'
        result = {"status": "Success", "output": "case test"}
        with self.assertRaises(ValueError):
            self.handler.handle_result(result)

    def test_handle_result_async_handles_warnings(self):
        result = {"status": "warning", "warnings": "Async warning"}
        loop = asyncio.new_event_loop()
        ret = loop.run_until_complete(self.handler.handle_result_async(result))
        self.assertTrue(ret)
        self.assertIn(('warning', "Warning: Async warning"), self.notifier.notifications)
        loop.close()


if __name__ == "__main__":
    unittest.main()
