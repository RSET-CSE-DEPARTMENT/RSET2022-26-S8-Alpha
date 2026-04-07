def algebraic_simplification(lines):
    new_lines = []

    for line in lines:
        if "+ 0" in line:
            line = line.replace("+ 0", "")
        if "* 1" in line:
            line = line.replace("* 1", "")
        if "- 0" in line:
            line = line.replace("- 0", "")
        if "/ 1" in line:
            line = line.replace("/ 1", "")
        new_lines.append(line)

    return new_lines
