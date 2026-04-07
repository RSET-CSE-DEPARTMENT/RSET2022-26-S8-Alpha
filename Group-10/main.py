# main.py
# CLI + optimization + static time complexity analysis

from optimizer import optimize
from runtime import analyze_code


def read_code_from_terminal():
    print("Paste your Python code below.")
    print("Type END on a new line when you are done:\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


def main():
    source = read_code_from_terminal()

    # save original code
    with open("original_temp.py", "w") as f:
        f.write(source)

    # optimize code
    optimized = optimize(source)

    # save optimized code
    with open("optimized_temp.py", "w") as f:
        f.write(optimized)

    # print optimized output
    print("\n--- Optimized Code ---\n")
    print(optimized)

    # static time complexity analysis
    original_complexity = analyze_file("original_temp.py")
    optimized_complexity = analyze_file("optimized_temp.py")

    print("\n--- Time Complexity Analysis ---")
    print(f"Original Code  : {original_complexity}")
    print(f"Optimized Code : {optimized_complexity}")


if __name__ == "__main__":
    main()
