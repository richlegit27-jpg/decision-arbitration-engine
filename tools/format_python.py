import sys
import re


def normalize_indentation(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    fixed_lines = []

    for line in lines:
        line = line.replace("\t", "    ")

        match = re.match(r"^( +)", line)
        if match:
            spaces = len(match.group(1))
            level = spaces // 4
            line = (" " * (level * 4)) + line.lstrip()

        fixed_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python format_python.py <file>")
        sys.exit(1)

    normalize_indentation(sys.argv[1])
    print("Indentation normalized.")
