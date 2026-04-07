from optimizer import optimize_java


def read_code_from_terminal():
    print("Paste your Java code below.")
    print("Type END on a new line when finished:\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


def main():
    source = read_code_from_terminal()

    print("\n--- Optimized Java Code ---\n")
    optimized = optimize_java(source)
    print(optimized)


if __name__ == "__main__":
    main()
