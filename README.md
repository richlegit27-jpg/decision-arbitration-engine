# Calculator Application

This application is a command-line calculator that performs basic arithmetic operations. It supports addition, subtraction, multiplication, and division with two numeric operands.

## Prerequisites

- Python 3.6 or higher installed on your system.
- Basic familiarity with using the terminal or command prompt.

## Installation / Setup

No special installation is required. Simply ensure Python is installed and accessible from your command line.

Place the calculator script (e.g., `calculator.py`) in a directory of your choice.

## How to Run

1. Open your terminal or command prompt.

2. Navigate to the directory containing the calculator script:
   ```
   cd /path/to/directory
   ```

3. Run the calculator script with the following command syntax:
   ```
   python calculator.py <operation> <operand1> <operand2>
   ```
   or, if your system uses `python3`:
   ```
   python3 calculator.py <operation> <operand1> <operand2>
   ```

## Supported Operations

- `add` — Adds operand1 and operand2.
- `sub` — Subtracts operand2 from operand1.
- `mul` — Multiplies operand1 and operand2.
- `div` — Divides operand1 by operand2 (operand2 should not be zero).

Operands should be numbers (integers or decimals).

## Examples

- Addition:
  ```
  python calculator.py add 5 3
  ```
  Output:
  ```
  Result: 8
  ```

- Subtraction:
  ```
  python calculator.py sub 10 4
  ```
  Output:
  ```
  Result: 6
  ```

- Multiplication:
  ```
  python calculator.py mul 7 6
  ```
  Output:
  ```
  Result: 42
  ```

- Division:
  ```
  python calculator.py div 12 4
  ```
  Output:
  ```
  Result: 3
  ```

- Handling division by zero:
  ```
  python calculator.py div 5 0
  ```
  Output:
  ```
  Error: Cannot divide by zero.
  ```

## Notes

- If invalid operation or operands are provided, the program will display an error message with usage instructions.
- You can use either integer or floating point numbers for the operands, for example:
  ```
  python calculator.py mul 3.5 2
  ```

Enjoy your simple command-line calculator!
