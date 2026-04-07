def copy_propagation(lines):
    aliases = {}
    new_lines = []

    for line in lines:
        if "=" in line and "int" in line:
            parts = line.replace("int", "").replace(";", "").split("=")
            var = parts[0].strip()
            val = parts[1].strip()

            if val.isidentifier():
                aliases[var] = val

        for a in aliases:
            if a in line:
                line = line.replace(a, aliases[a])

        new_lines.append(line)

    return new_lines
