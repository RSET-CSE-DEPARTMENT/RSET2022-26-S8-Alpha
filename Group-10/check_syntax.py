import sys
import os
import re
import subprocess
import json
import tempfile
import ast
import contextlib
import io


# Read code from stdin
code_str = sys.stdin.read().replace("\r\n", "\n").replace("\r", "\n")

if len(sys.argv) < 2:
    print(json.dumps({"syntax_ok": False, "syntax_error": "No language specified"}))
    sys.exit(1)

lang_name = sys.argv[1].lower()

result = {
    "syntax_ok": False,
    "syntax_error": "",
    "manual_checks": [],
    "semantic_errors": []
}

# ---------------------------
# PYTHON
# ---------------------------
if lang_name == "python":

    try:
        compile(code_str, "<string>", "exec")
        result["syntax_ok"] = True
    except (SyntaxError, IndentationError, TabError) as e:
        result["syntax_error"] = f"Python Syntax Error at line {e.lineno}, column {e.offset}: {e.msg}"
        if e.text:
            result["syntax_error"] += f"\nCode: {e.text.strip()}"

    # -------- STATIC ANALYSIS --------
    if result["syntax_ok"]:
        tree = ast.parse(code_str)

        defined_vars = set()
        reported = set()

        class Analyzer(ast.NodeVisitor):

            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_vars.add(target.id)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                defined_vars.add(node.name)

                for arg in node.args.args:
                    defined_vars.add(arg.arg)

                found_return = False
                for stmt in node.body:
                    if found_return:
                        result["semantic_errors"].append(
                            f"Unreachable code at line {stmt.lineno}"
                        )
                    if isinstance(stmt, ast.Return):
                        found_return = True

                self.generic_visit(node)

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load):
                    if (
                        node.id not in defined_vars
                        and node.id not in dir(__builtins__)
                        and node.id not in reported
                    ):
                        result["semantic_errors"].append(
                            f"Possible undefined variable '{node.id}' at line {node.lineno}"
                        )
                        reported.add(node.id)

                self.generic_visit(node)

            def visit_BinOp(self, node):
                if isinstance(node.op, ast.Div):
                    if isinstance(node.right, ast.Constant) and node.right.value == 0:
                        result["semantic_errors"].append(
                            f"Possible division by zero at line {node.lineno}"
                        )

                if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                    if type(node.left.value) != type(node.right.value):
                        result["semantic_errors"].append(
                            f"Possible type mismatch at line {node.lineno}"
                        )

                self.generic_visit(node)

        Analyzer().visit(tree)

        # -------- RUNTIME CHECK (SAFE) --------
        try:
            fake_stdout = io.StringIO()
            fake_stderr = io.StringIO()

            with contextlib.redirect_stdout(fake_stdout), contextlib.redirect_stderr(fake_stderr):
                exec(code_str, {})

        except ZeroDivisionError:
            result["semantic_errors"].append("Runtime ZeroDivisionError detected")

        except NameError as e:
            result["semantic_errors"].append(f"Runtime Undefined Variable: {str(e)}")

        except TypeError as e:
            result["semantic_errors"].append(f"Runtime TypeError: {str(e)}")

        except Exception:
            pass

    # -------- MANUAL CHECKS --------
    lines = code_str.split("\n")
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        if any(stripped.startswith(kw) for kw in ["if ", "for ", "while ", "def ", "class "]):
            if not stripped.endswith(":"):
                result["manual_checks"].append(f"Possible missing colon at line {i}")

        leading_spaces = len(line) - len(line.lstrip(" "))
        if stripped and leading_spaces % 4 != 0:
            result["manual_checks"].append(f"Unusual indentation at line {i}")


# ---------------------------
# JAVA
# ---------------------------
elif lang_name == "java":

    match = re.search(r'public\s+class\s+(\w+)', code_str)
    class_name = match.group(1) if match else "Main"

    with tempfile.TemporaryDirectory() as tmpdir:
        filename = os.path.join(tmpdir, f"{class_name}.java")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_str)

        proc = subprocess.run(
            ["javac", filename],
            capture_output=True,
            text=True
        )

        if proc.returncode == 0:
            result["syntax_ok"] = True

            run_proc = subprocess.run(
                ["java", "-cp", tmpdir, class_name],
                capture_output=True,
                text=True
            )

            runtime_error = run_proc.stderr

            if "ArithmeticException" in runtime_error:
                result["semantic_errors"].append("Runtime ArithmeticException (possible division by zero)")

            if "NullPointerException" in runtime_error:
                result["semantic_errors"].append("Runtime NullPointerException detected")

            if "ArrayIndexOutOfBoundsException" in runtime_error:
                result["semantic_errors"].append("Runtime ArrayIndexOutOfBoundsException detected")

        else:
            error_output = proc.stderr.strip()
            result["syntax_error"] = "Java Syntax Error:\n" + error_output

    if "class " not in code_str:
        result["manual_checks"].append("No class declaration found.")

    if code_str.count("{") != code_str.count("}"):
        result["manual_checks"].append("Unmatched braces detected.")


# ---------------------------
# JAVASCRIPT
# ---------------------------
elif lang_name == "javascript":

    proc = subprocess.run(
        ["node", "--check"],
        input=code_str,
        text=True,
        capture_output=True
    )

    if proc.returncode == 0:
        result["syntax_ok"] = True

        run_proc = subprocess.run(
            ["node"],
            input=code_str,
            text=True,
            capture_output=True
        )

        runtime_error = run_proc.stderr
        runtime_output = run_proc.stdout

        if "ReferenceError" in runtime_error:
            result["semantic_errors"].append("Runtime ReferenceError (undefined variable) detected")

        if "TypeError" in runtime_error:
            result["semantic_errors"].append("Runtime TypeError detected")

        if "RangeError" in runtime_error:
            result["semantic_errors"].append("Runtime RangeError detected")

        if "Infinity" in runtime_output:
            result["semantic_errors"].append("Possible division by zero (Infinity detected)")

    else:
        result["syntax_error"] = "JavaScript Syntax Error:\n" + proc.stderr


# ---------------------------
# UNSUPPORTED
# ---------------------------
else:
    result["syntax_error"] = f"Unsupported language: {lang_name}"


# Output JSON
print(json.dumps(result))
sys.exit(0 if result["syntax_ok"] else 1)
