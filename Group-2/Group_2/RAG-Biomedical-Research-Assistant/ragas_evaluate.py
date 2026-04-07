import os
from openai import OpenAI
from datasets import Dataset
from ragas import evaluate
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory
from ragas.metrics.collections import (
    AnswerCorrectness,
    AnswerRelevancy,
    Faithfulness,
    ContextPrecision,
    ContextRecall,
)

# 1. Setup the local OpenAI-compatible client for Ollama
# Ensure Ollama is running at http://localhost:11434
local_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Ollama ignores the key but the client requires one
)

# 2. Initialize the LLM and Embeddings using the client
# Use 'llama3' or whichever model you have pulled in Ollama
evaluator_llm = llm_factory(model="llama3", client=local_client)
evaluator_embeddings = embedding_factory(model="mxbai-embed-large", client=local_client)

# 3. Prepare your evaluation data
data_samples = {
    "question": ["What is the role of oxidative stress in neurodegenerative disease?"],
    "contexts": [["... (your context chunks) ..."]],
    "answer": ["... (your system answer) ..."],
    "reference": ["... (your ground truth) ..."],
}
dataset = Dataset.from_dict(data_samples)

# 4. Initialize metrics and assign the local evaluator
metrics = [
    AnswerCorrectness(llm=evaluator_llm),
    AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
    Faithfulness(llm=evaluator_llm),
    ContextPrecision(llm=evaluator_llm),
    ContextRecall(llm=evaluator_llm),
]

# 5. Execute Evaluation
print("🔄 Running local evaluation (Single-threaded to avoid Ollama timeout)...")
scores = evaluate(
    dataset,
    metrics=metrics,
    is_async=False  # Required for most local Ollama setups
)

print("\n--- FINAL RAGAS SCORES ---")
print(scores)