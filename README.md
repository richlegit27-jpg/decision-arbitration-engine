# Calculator Application

## Project Purpose

This project implements a simple command-line calculator designed to perform basic arithmetic operations. Its purpose is to provide a lightweight and easy-to-use tool that supports addition, subtraction, multiplication, and division on two numeric operands, directly from the terminal. This makes it useful for quick calculations without requiring a full-featured calculator application or external libraries.

## Design and Dependency Graph

The calculator is implemented as a standalone Python script (`calculator.py`) that relies solely on the Python standard library. It has no external dependencies, making it portable and easy to run in any standard Python 3.6+ environment.

### Key Components:

- **Input Parser:** Validates and extracts command-line arguments for operation type and operands.
- **Operation Validator:** Checks that the operation requested is one of the supported types (`add`, `sub`, `mul`, `div`).
- **Operand Validator:** Ensures operands are valid numeric values.
- **Error Handler:** Detects improper inputs (invalid operation, non-numeric operands, division by zero) and reports user-friendly errors.
- **Calculator Engine:** Performs the specified arithmetic operation.
- **Output Formatter:** Prints the result or an appropriate error message.

The dependency flow is linear:

Command Line Arguments → Input Parser → Operation Validator + Operand Validator → Calculator Engine → Output Formatter

If any validation fails, control transfers to the Error Handler to output the error message and terminate.

## The Three-Task Execution Flow

This calculator implementation follows a structured three-task execution flow to ensure clarity, modularity, and maintainability. The flow consists of:

1. **Validation Task**  
   - Validates command-line inputs (operation and operands).  
   - Checks operation is supported.  
   - Checks operands are numeric and division-by-zero is avoided.  
   - Any failures here are immediately reported through error messages, preventing the calculator engine from running with invalid input.

2. **Execution Task**  
   - Performs the arithmetic operation using a dedicated calculator engine component.  
   - Uses sanitized, validated arguments from the previous step.

3. **Output Task**  
   - Formats and displays the result if successful.  
   - If an error occurred earlier, prints the corresponding error message.  
   - Ensures user-friendly output for both success and failure scenarios.

---

## How to Use the Calculator (User Guide)

### Running the Calculator

1. Ensure Python 3.6 or higher is installed and accessible via your command line.

2. Place the `calculator.py` script in a convenient directory.

3. Open your terminal/command prompt and navigate to that directory:
   ```
   cd /path/to/directory
   ```

4. Run the script with the following syntax:
   ```
   python calculator.py <operation> <operand1> <operand2>
   ```
   or, if your system uses `python3`:
   ```
   python3 calculator.py <operation> <operand1> <operand2>
   ```

### Supported Operations:

- `add` — Addition
- `sub` — Subtraction
- `mul` — Multiplication
- `div` — Division

### Example Commands:

- Addition:  
  ```
  python calculator.py add 10 5
  ```
- Subtraction:  
  ```
  python calculator.py sub 7 2
  ```
- Multiplication:  
  ```
  python calculator.py mul 3.5 2
  ```
- Division:  
  ```
  python calculator.py div 20 4
  ```

### Interpreting Output

- **Successful Operation Output:**  
  ```
  Result: <number>
  ```
  where `<number>` is the calculated value.

- **Error Output:** Provides friendly descriptive messages indicating the problem:
  - Unsupported operation:  
    ```
    Error: Unsupported operation 'mod'. Supported operations are add, sub, mul, div.
    ```
  - Invalid numeric operands:  
    ```
    Error: Operands must be numbers.
    ```
  - Division by zero attempt:  
    ```
    Error: Cannot divide by zero.
    ```
  - Incorrect usage (missing or extra arguments):  
    ```
    Usage: python calculator.py <operation> <operand1> <operand2>
    ```

---

## Monitoring the Calculator Execution Flow (Developer Guide)

### Understanding Task Separation

The three-task flow ensures each concern is isolated:

- **Validation:**  
  Fail-fast approach on invalid inputs facilitates early error detection and prevents unnecessary computation.

- **Execution:**  
  Centralizing arithmetic logic ensures consistency and simplifies future extension with new operations.

- **Output:**  
  Clear, user-friendly messages improve usability and reduce frustration during incorrect usage.

### Logging and Debugging

Although the current version outputs errors directly to the console, developers can enhance observability by:

- Adding logging at each task boundary to track input validation outcomes and execution results.
- Catching unexpected exceptions in the execution task to prevent crashes and provide meaningful diagnostics.
- Implementing verbose/debug mode flags to reveal internal states and execution steps during troubleshooting.

### Execution Flow Walkthrough

- **Step 1 (Validation):** The program reads command-line input and validates the following:
  - Exactly three arguments are provided.
  - The operation keyword is among supported operations.
  - Both operands can be converted to numbers.
  - Division by zero is not attempted if operation is `div`.

- **Step 2 (Execution):** After successful validation, the calculator engine performs the corresponding arithmetic operation on the parsed operands, producing a numeric result.

- **Step 3 (Output):** The output task formats the result or outputs error messages if validation failed. This ensures clear communication to the user.

---

## Maintenance Recommendations

- **Extensibility:**  
  When adding new operations, update the operation validator and calculator engine components, keeping separation from other tasks intact.

- **Testing:**  
  Implement unit tests for each task:
  - Validation tests ensuring invalid inputs produce expected errors.
  - Execution tests verifying correct calculation results.
  - Output tests confirming proper message formatting.

- **Code Documentation:**  
  Maintain comments and docstrings especially in the validation and execution logic for clarity.

- **Version Control:**  
  Use semantic versioning to track changes affecting user-facing behavior versus internal refactoring.

- **Dependency Updates:**  
  Since this script uses standard libraries only, keep abreast of Python runtime updates that might affect script compatibility.

- **Monitoring:**  
  For production environments or complex uses, extend logging or monitoring tools around the three-task flow to track failures, performance, and usage metrics.

---

Thank you for using this simple, effective command-line calculator! For questions or contributions, please contact the project maintainer.
