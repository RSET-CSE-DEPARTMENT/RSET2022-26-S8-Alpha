# RAG-Based Code Assistant

A unified AI-powered system designed to help users understand, analyze, and improve source code using Retrieval-Augmented Generation (RAG) and Large Language Models (LLMs).

---

## Overview

The RAG-Based Code Assistant integrates multiple programming support functionalities into a single platform. It assists users in performing tasks such as syntax checking, code optimization, code conversion, explanation generation, and algorithm and flowchart creation. The system combines program analysis techniques with AI-based models to improve code understanding and productivity.

---

## Features

- Syntax error detection for Python, Java, and JavaScript  
- Code optimization using compiler-based techniques  
- Code conversion between Python and Java  
- Code explanation using Retrieval-Augmented Generation (RAG)  
- Algorithm generation from natural language problem statements  
- Flowchart generation using Graphviz  

---

## System Architecture

The system is built using a combination of AI models and software components:

- Retrieval-Augmented Generation (RAG) framework  
- CodeT5 model for code translation  
- LLaMA model via Groq API for explanation and generation  
- ChromaDB for vector storage and retrieval  
- Graphviz for flowchart visualization  

---

## Modules

### Syntax Checker
Performs static analysis to detect syntax and structural errors in code.

### Code Optimization
Applies techniques such as constant folding, copy propagation, and dead code elimination to improve program efficiency.

### Code Conversion
Translates code between Python and Java using a transformer-based model.

### Code Explanation (RAG-Based)
Generates line-by-line explanations by retrieving relevant context and using a language model.

### Algorithm and Flowchart Generation
Converts problem statements into structured algorithms and visual flowcharts.

---

## Tech Stack

- Backend: Python, Flask  
- Frontend: HTML, CSS, JavaScript  
- AI Models: CodeT5, LLaMA  
- Database: ChromaDB  
- Libraries: Transformers, Torch, AST, Javalang  
- Visualization: Graphviz  

---

## Dataset

- Approximately 2100+ Python–Java code pairs  
- Includes loops, functions, recursion, and conditional statements  
- Dataset split: 90% training, 10% testing  

---


cd your-repo-name
pip install -r requirements.txt
python app.py
