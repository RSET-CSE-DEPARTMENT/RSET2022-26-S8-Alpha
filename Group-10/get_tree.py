import sys
import os
import subprocess
from tree_sitter import Parser
from tree_sitter_languages import get_language

# --- Map languages to test files ---
TEST_CODES = {
    "python": "test.py",
    "java": "Main.java",
    "javascript": "script.js"
}

# --- Get language from command line ---
if len(sys.argv) != 2:
    print("Usage: python get_tree.py <language>")
    print("Available languages: python, java, javascript")
    sys.exit(1)

lang_name = sys.argv[1].lower()
if lang_name not in TEST_CODES:
    print(f"Unsupported language: {lang_name}")
    sys.exit(1)

filename = TEST_CODES[lang_name]
if not os.path.exists(filename):
    print(f"File not found: {filename}")
    sys.exit(1)

# --- Read code ---
with open(filename, "r", encoding="utf-8") as f:
    code_str = f.read()

# --- Syntax check ---
syntax_ok = True
syntax_error = None

if lang_name == "python":
    try:
        compile(code_str, "<string>", "exec")
    except SyntaxError as e:
        syntax_ok = False
        syntax_error = f"Python Syntax Error: Line {e.lineno}, Col {e.offset}: {e.msg}"

elif lang_name == "java":
    tmp_name = "Main.java"
    with open(tmp_name, "w", encoding="utf-8") as tmp:
        tmp.write(code_str)
    result = subprocess.run(["javac", tmp_name], capture_output=True, text=True)
    if result.returncode != 0:
        syntax_ok = False
        syntax_error = f"Java Syntax Error:\n{result.stderr}"
    if os.path.exists(tmp_name):
        os.remove(tmp_name)
    class_file = tmp_name.replace(".java", ".class")
    if os.path.exists(class_file):
        os.remove(class_file)

elif lang_name == "javascript":
    result = subprocess.run(["node", "--check"], input=code_str, text=True, capture_output=True)
    if result.returncode != 0:
        syntax_ok = False
        syntax_error = f"JavaScript Syntax Error:\n{result.stderr}"

if not syntax_ok:
    print(syntax_error)
    sys.exit(1)

# --- Generate AST ---
parser = Parser()
if lang_name == "python":
    parser.set_language(get_language("python"))
elif lang_name == "java":
    parser.set_language(get_language("java"))
elif lang_name == "javascript":
    parser.set_language(get_language("javascript"))

tree = parser.parse(bytes(code_str, "utf8"))

# --- Pretty print tree (human-friendly) ---
def print_tree(node, prefix=""):
    """Prints tree using lines like ├─ and └─ for hierarchy"""
    children = node.children
    marker = "└─" if not prefix or prefix.endswith("└─") else "├─"
    print(f"{prefix}{marker}{node.type}")
    
    for i, child in enumerate(children):
        # Determine branch symbol
        is_last = i == len(children) - 1
        new_prefix = prefix + ("   " if is_last else "│  ")
        print_tree(child, new_prefix)

print_tree(tree.root_node)
