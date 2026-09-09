import argparse
import sys

from calculator import add, subtract, multiply, divide

def parse_args():
    parser = argparse.ArgumentParser(description="Simple Calculator")
    parser.add_argument("num1", help="First number")
    parser.add_argument("num2", help="Second number")
    parser.add_argument("operation", choices=["add", "subtract", "multiply", "divide"],
                        help="Operation to perform")
    return parser.parse_args()

def main():
    args = parse_args()

    # Validate numbers
    try:
        num1 = float(args.num1)
    except ValueError:
        print(f"Error: Invalid number '{args.num1}'.")
        sys.exit(1)
    try:
        num2 = float(args.num2)
    except ValueError:
        print(f"Error: Invalid number '{args.num2}'.")
        sys.exit(1)

    operation = args.operation

    try:
        if operation == "add":
            result = add(num1, num2)
        elif operation == "subtract":
            result = subtract(num1, num2)
        elif operation == "multiply":
            result = multiply(num1, num2)
        elif operation == "divide":
            result = divide(num1, num2)
        else:
            print(f"Error: Unknown operation '{operation}'.")
            sys.exit(1)
    except ZeroDivisionError:
        print("Error: Division by zero is not allowed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Result: {result}")

if __name__ == "__main__":
    main()
