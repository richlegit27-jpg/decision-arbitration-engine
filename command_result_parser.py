import json
import re
from typing import Any, Dict, Optional, Tuple, Union


class CommandResultParserError(Exception):
    """Custom exception for command result parsing errors."""
    pass


class CommandResultParser:
    """
    Parses and validates command results according to predefined formats.
    """

    # Define the expected command result schemas
    # For this example, we assume 3 possible command result formats:
    # 1) JSON output with status and data keys
    # 2) Plain text success/failure messages
    # 3) Key=Value pairs output
    #
    # The actual formats should be extended based on application requirements.

    @staticmethod
    def parse(result: Union[str, bytes]) -> Dict[str, Any]:
        """
        Parse the raw command result into structured data.

        :param result: The raw result output as string or bytes.
        :return: Parsed result as dictionary.
        :raises CommandResultParserError: If parsing or validation fails.
        """
        if not result:
            raise CommandResultParserError("Empty result cannot be parsed.")

        if isinstance(result, bytes):
            try:
                result = result.decode('utf-8')
            except UnicodeDecodeError as e:
                raise CommandResultParserError(f"Failed to decode bytes result: {e}")

        # Try to parse JSON first
        parsed, used_format = CommandResultParser._try_parse_json(result)
        if parsed is not None:
            CommandResultParser._validate_json(parsed)
            return parsed

        # Try to parse key=value pairs
        parsed, used_format = CommandResultParser._try_parse_key_value_pairs(result)
        if parsed is not None:
            CommandResultParser._validate_key_value(parsed)
            return parsed

        # Try to parse plain text result
        parsed, used_format = CommandResultParser._try_parse_plain_text(result)
        if parsed is not None:
            CommandResultParser._validate_plain_text(parsed)
            return parsed

        raise CommandResultParserError("Result format not recognized or invalid.")

    @staticmethod
    def _try_parse_json(text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data, "json"
            else:
                return None, "json"
        except json.JSONDecodeError:
            return None, "json"

    @staticmethod
    def _try_parse_key_value_pairs(text: str) -> Tuple[Optional[Dict[str, str]], str]:
        # Expect lines like: key=value
        lines = text.strip().splitlines()
        if not lines:
            return None, "key_value"

        result_dict = {}
        for line in lines:
            if '=' not in line:
                return None, "key_value"
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if not key:
                return None, "key_value"
            result_dict[key] = value
        return result_dict, "key_value"

    @staticmethod
    def _try_parse_plain_text(text: str) -> Tuple[Optional[Dict[str, str]], str]:
        # Assume the plain text results are one of a few standard messages
        valid_texts = {"success", "failure", "error", "ok"}
        text_lower = text.strip().lower()
        if text_lower in valid_texts:
            return {"status": text_lower}, "plain_text"
        else:
            return None, "plain_text"

    @staticmethod
    def _validate_json(data: Dict[str, Any]) -> None:
        # Validate expected keys and value types
        if 'status' not in data:
            raise CommandResultParserError("JSON result missing mandatory key 'status'.")

        if not isinstance(data['status'], str):
            raise CommandResultParserError("'status' field must be of type string in JSON result.")

        # Optional: validate that if 'status' is 'success', 'data' key should be present
        if data['status'].lower() == 'success':
            if 'data' not in data:
                raise CommandResultParserError("JSON success result missing 'data' field.")

    @staticmethod
    def _validate_key_value(data: Dict[str, str]) -> None:
        # Validate keys and values are nonempty strings
        for key, value in data.items():
            if not key or not isinstance(key, str):
                raise CommandResultParserError("Invalid key in key-value result.")
            if not isinstance(value, str):
                raise CommandResultParserError("Invalid value in key-value result.")

        # Simple example of validation: require a 'status' key
        if 'status' not in data:
            raise CommandResultParserError("Key-value result missing mandatory 'status' key.")

        # Validate status value
        if data['status'].lower() not in {"success", "failure", "error", "ok"}:
            raise CommandResultParserError(f"Invalid status value: {data['status']}")

    @staticmethod
    def _validate_plain_text(data: Dict[str, str]) -> None:
        # Plain text already validated during parsing since only allowed values are accepted
        pass
