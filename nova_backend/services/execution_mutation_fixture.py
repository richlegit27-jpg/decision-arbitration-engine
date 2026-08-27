"""
Nova mutation test target.

This file is intentionally simple.
The execution engine should be able to replace
or modify this file during a mutation test.
"""


def mutation_test_value():
    # Changed the return value from 'mutated' to 'mutation_target' to determine implementation target
    return "mutation_target"


def run_mutation_test():
    value = mutation_test_value()
    return {
        "status": "ok",
        "value": value,
    }


if __name__ == "__main__":
    result = run_mutation_test()
    print(result)