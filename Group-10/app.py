from unittest import result
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from optimizer import optimize
from runtime import analyze_code
from javaop import optimize_java


import torch
import os
from groq import Groq

app = Flask(__name__)
CORS(app)

device = "cuda" if torch.cuda.is_available() else "cpu"

# --------------------------------------------------
# LOAD PYTHON → JAVA MODEL
# --------------------------------------------------

PY_TO_JAVA_MODEL = "anithra/code-assistant-final"

print("🔹 Loading Python → Java model...")
py_java_tokenizer = AutoTokenizer.from_pretrained(PY_TO_JAVA_MODEL)
py_java_model = AutoModelForSeq2SeqLM.from_pretrained(PY_TO_JAVA_MODEL)

py_java_model.to(device)
py_java_model.eval()

print("✅ Python → Java model loaded.")

# --------------------------------------------------
# LOAD JAVA → PYTHON MODEL
# --------------------------------------------------

JAVA_TO_PY_MODEL = "anithra/java-to-python-assistant"

print("🔹 Loading Java → Python model...")
java_py_tokenizer = AutoTokenizer.from_pretrained(JAVA_TO_PY_MODEL)
java_py_model = AutoModelForSeq2SeqLM.from_pretrained(JAVA_TO_PY_MODEL)

java_py_model.to(device)
java_py_model.eval()

print("✅ Java → Python model loaded.")

# --------------------------------------------------
# GROQ SETUP
# --------------------------------------------------
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --------------------------------------------------
# STAGE 1 — PYTHON → JAVA (MODEL)
# --------------------------------------------------

def codet5_python_to_java(code):
    prompt = f"task: python_to_java | code: {code}"
    inputs = py_java_tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output = py_java_model.generate(
            **inputs,
            max_new_tokens=800,
            num_beams=4,
            do_sample=False,
            temperature=0.0
        )

    return py_java_tokenizer.decode(output[0], skip_special_tokens=True)

# --------------------------------------------------
# STAGE 1 — JAVA → PYTHON (MODEL)
# --------------------------------------------------

def codet5_java_to_python(code):
    prompt = f"task: java_to_python | code: {code}"
    inputs = java_py_tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output = java_py_model.generate(
            **inputs,
            max_new_tokens=800,
            num_beams=4,
            do_sample=False,
            temperature=0.0
        )

    return java_py_tokenizer.decode(output[0], skip_special_tokens=True)

# --------------------------------------------------
# STAGE 2 — GROQ REFINEMENT (PY → JAVA)
# --------------------------------------------------

def groq_refine_python_to_java(python_code, java_draft):
    prompt = f"""
You are a strict Java translator.

Convert the following Python code into a CORRECT, FULLY RUNNABLE Java program.

Rules:
- Output ONLY pure Java code
- No markdown
- Do NOT include ```java whatsoever
- Do NOT include triple quotes whatsoever
- Include public class Main
- Must compile with javac
- Preserve Python behavior EXACTLY
- No comments
- No extra text
- Include public class Main
- Do Not include explanations whatsoever
- No analysis
- Do not modify the logic, values, or input ranges. Preserve all variable names, numeric ranges, and algorithm structure exactly as given.
- If Python uses max() or min() on a list, convert it to Collections.max() or Collections.min() if using List, or implement a manual loop if using arrays. Do NOT use Math.max() or Math.min() on collections.
- When converting mathematical formulas, preserve the exact arithmetic expression. Do not introduce extra multiplications or modify exponent formulas.
- Ensure the generated Java code compiles without errors. Include all necessary imports. Do not assume implicit imports.
- Use ArrayList<Integer> for Python lists of integers. Do not randomly switch between arrays and lists unless required.
- Include ONLY the imports that are actually used in the generated Java code.
- Do not include unused or unnecessary imports.
- Remove any unused imports before outputting the final code.


Python code:
{python_code}

Java draft:
{java_draft}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    return response.choices[0].message.content.strip()

# --------------------------------------------------
# STAGE 2 — GROQ REFINEMENT (JAVA → PY)
# --------------------------------------------------

def groq_refine_java_to_python(java_code, python_draft):
    prompt = f"""
You are a strict Python translator.

Convert the following Java code into CORRECT, FULLY RUNNABLE Python code.

Rules:
- Output ONLY pure Python code
- No explanations
- No markdown
- Do NOT include ```python whatsoever
- No markdown
- Do NOT include triple quotes whatsoever
- No triple quotes
- Preserve logic EXACTLY
- No extra text

Java code:
{java_code}

Python draft:
{python_draft}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    return response.choices[0].message.content.strip()
def clean_unused_imports(java_code):
    lines = java_code.split("\n")

    import_lines = [l for l in lines if l.strip().startswith("import")]
    body_lines = [l for l in lines if not l.strip().startswith("import")]

    body = "\n".join(body_lines)

    cleaned_imports = []

    for line in import_lines:
        class_name = line.split(".")[-1].replace(";", "").strip()
        if class_name in body:
            cleaned_imports.append(line)

    final_code = "\n".join(cleaned_imports + body_lines)
    return final_code

# --------------------------------------------------
# PIPELINES
# --------------------------------------------------

def python_to_java_pipeline(code):
    draft = codet5_python_to_java(code)
    refined = groq_refine_python_to_java(code, draft)
    cleaned = clean_unused_imports(refined)
    return cleaned
    #return groq_refine_python_to_java(code, draft)

def java_to_python_pipeline(code):
    draft = codet5_java_to_python(code)
    return groq_refine_java_to_python(code, draft)

# --------------------------------------------------
# ROUTE
# --------------------------------------------------

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    code = data.get("code", "").strip()
    language = data.get("language", "")

    if not code:
        return jsonify({"error": "No code provided"}), 400

    try:
        if language == "python":
            result = python_to_java_pipeline(code)

        elif language == "java":
            result = java_to_python_pipeline(code)

        else:
            return jsonify({"error": "Unsupported language"}), 400

        return jsonify({"converted_code": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------------------------------
@app.route("/optimize", methods=["POST"])
def optimize_code():
    data = request.json
    print("FULL DATA:", data)

    source = data.get("code", "").strip()
    language = data.get("language", "").strip().lower()

    print("LANGUAGE AFTER LOWER:", language)

    if not source:
        return jsonify({"error": "No code provided"}), 400

    try:
        if language == "python":
            print(">>> PYTHON BRANCH")
            optimized = optimize(source)
            original_complexity = analyze_code(source)
            optimized_complexity = analyze_code(optimized)

        elif language == "java":
            print(">>> JAVA BRANCH")
            optimized = optimize_java(source)
            print("JAVA OUTPUT:", optimized)
            original_complexity = "N/A"
            optimized_complexity = "N/A"

        else:
            print(">>> UNSUPPORTED LANGUAGE")
            return jsonify({"error": "Unsupported language"}), 400

        return jsonify({
            "optimized_code": optimized,
            "original_complexity": original_complexity,
            "optimized_complexity": optimized_complexity
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

import subprocess
import sys
import json

@app.route("/check-syntax", methods=["POST"])
def check_syntax_route():
    data = request.json
    lang_name = data.get("language")
    code_str = data.get("code")

    if not code_str:
        return jsonify({"syntax_error": "No code provided."}), 400

    result = subprocess.run(
        [sys.executable, "check_syntax.py", lang_name],
        input=code_str,
        text=True,
        capture_output=True
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)


    try:
        output_json = json.loads(result.stdout)
    except Exception:
        return jsonify({"syntax_error": "Invalid syntax checker response"}), 500

    if not output_json.get("syntax_ok", False):
        return jsonify({
        "syntax_ok": False,
        "syntax_error": output_json.get("syntax_error"),
        "manual_checks": output_json.get("manual_checks", []),
        "semantic_errors": output_json.get("semantic_errors", [])
    }), 400

    return jsonify({
    "syntax_ok": True,
    "syntax_result": "Code syntax is correct!",
    "manual_checks": output_json.get("manual_checks", []),
    "semantic_errors": output_json.get("semantic_errors", [])
})

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)

