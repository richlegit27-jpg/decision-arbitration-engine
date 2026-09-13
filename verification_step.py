from typing import Any, Dict


class VerificationStep:
    """
    VerificationStep verifies the analysis output against defined criteria.
    """

    def __init__(self, criteria: Dict[str, Any]) -> None:
        """
        Initialize the VerificationStep with criteria.
        
        Args:
            criteria (Dict[str, Any]): Dictionary containing verification criteria.
        """
        self.criteria = criteria

    def verify(self, analysis_output: Dict[str, Any]) -> bool:
        """
        Verify the analysis output against the criteria.
        
        Args:
            analysis_output (Dict[str, Any]): The output data from the analysis to verify.
        
        Returns:
            bool: True if output meets the criteria, False otherwise.
        """
        for key, expected_value in self.criteria.items():
            if key not in analysis_output:
                # Missing key in output
                return False

            actual_value = analysis_output[key]
            if not self._matches_criteria(actual_value, expected_value):
                return False

        return True

    def _matches_criteria(self, actual: Any, expected: Any) -> bool:
        """
        Determine if actual value matches expected criteria.

        Supports:
          - direct value equality
          - numeric range if expected is a dict with 'min' and/or 'max'

        Args:
            actual (Any): actual value from output
            expected (Any): expected criteria, can be:
                - direct value
                - dict with optional 'min' and 'max' keys for range check
        
        Returns:
            bool: True if actual matches criteria, else False
        """
        if isinstance(expected, dict):
            # Range or complex criteria expected
            min_val = expected.get('min', None)
            max_val = expected.get('max', None)

            try:
                val = float(actual)
            except (TypeError, ValueError):
                return False

            if min_val is not None and val < min_val:
                return False
            if max_val is not None and val > max_val:
                return False
            return True

        else:
            return actual == expected
