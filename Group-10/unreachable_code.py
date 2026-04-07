def unreachable_code_removal(lines):
    new_lines = []
    skip = False

    for line in lines:
        if "if (false)" in line:
            skip = True
            continue
        if skip and "}" in line:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    return new_lines
