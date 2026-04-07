from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import nltk
import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)


BIENCODER_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"

CROSSENCODER_CANDIDATES = [
    "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "NeuML/pubmedbert-base-embeddings-matryoshka",
    "abhi1nandy2/Literature-Based-QA-Cross-Encoder",
]

OLLAMA_MODEL = "qwen2"
OLLAMA_BASE_URL = "http://localhost:11434"

SYSTEM_PROMPT = (
    "You are an expert medical assistant specialized in clinical and biomedical question answering. "
    "Answer questions accurately using ONLY the context provided below. "
    "Do NOT use any outside knowledge. "
    "\n\n"
    "CRITICAL INSTRUCTIONS:\n"
    "- Use information from the ENTIRE context provided, not just the first few sentences\n"
    "- Include ALL relevant details: common symptoms, severe symptoms, complications, and variants\n"
    "- Do NOT omit information just because it appears later in the context\n"
    "- Organize your answer comprehensively: start with common findings, then progress to severe/complicated manifestations\n"
    "- If the context does not contain enough information to answer completely, state what is missing\n"
    "\n"
    "Structure your answer clearly and include all relevant medical information from every part of the context."
)
'''
SYSTEM_PROMPT = (
    "You are an expert medical assistant specialised in clinical and biomedical question answering. "
    "Answer questions accurately using ONLY the context provided. "
    "Do NOT use any outside knowledge. "
    "If the context does not contain enough information to answer, say so clearly."
)
'''

USER_TEMPLATE = (
    "Use the following context to answer the question below in 2–3 clear, complete sentences.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}"
)


@dataclass
class ScoredSentence:
    text: str
    source_idx: int
    bi_score: float = 0.0
    ce_score: float = 0.0
    mmr_score: float = 0.0
    rank: int = -1


@dataclass
class ExtractionResult:
    query: str
    selected: list[ScoredSentence] = field(default_factory=list)
    combined_context: str = ""


@dataclass
class GenerationResult:
    query: str
    extraction: ExtractionResult
    answer: str
    prompt_used: str = ""
    truncated: bool = False


class SentenceExtractor:
    def __init__(
        self,
        top_n: int = 5,
        candidate_pool_size: int = 25,
        mmr_lambda: float = 0.7,
        min_sentence_tokens: int = 6,
        biencoder_model: str = BIENCODER_MODEL,
        crossencoder_model: Optional[str] = None,
        device: str = "cpu",
    ) -> None:
        self.top_n = top_n
        self.candidate_pool_size = candidate_pool_size
        self.mmr_lambda = mmr_lambda
        self.min_sentence_tokens = min_sentence_tokens
        self.device = device

        logger.info("Loading bi-encoder: %s", biencoder_model)
        self.biencoder = SentenceTransformer(biencoder_model, device=device)

        self.crossencoder: Optional[CrossEncoder] = None
        ce_name = crossencoder_model or self._resolve_crossencoder()
        if ce_name:
            logger.info("Loading cross-encoder: %s", ce_name)
            try:
                self.crossencoder = CrossEncoder(ce_name, device=device)
                logger.info("Cross-encoder loaded successfully.")
            except Exception as exc:
                logger.warning("Cross-encoder load failed (%s). Skipping.", exc)

    def extract(self, query: str, contexts: list[str]) -> ExtractionResult:
        sentences = self._segment(contexts)
        if not sentences:
            return ExtractionResult(query=query)

        sentences = self._biencoder_score(query, sentences)

        pool_size = min(self.candidate_pool_size, len(sentences))
        candidates = sorted(sentences, key=lambda s: s.bi_score, reverse=True)[:pool_size]

        if self.crossencoder:
            candidates = self._crossencoder_rerank(query, candidates)
            sort_key = lambda s: s.ce_score
        else:
            sort_key = lambda s: s.bi_score

        candidates = sorted(candidates, key=sort_key, reverse=True)
        selected = self._mmr_select(query, candidates, sort_key)

        for rank, sent in enumerate(selected, start=1):
            sent.rank = rank

        ordered = sorted(selected, key=lambda s: (s.source_idx, s.rank))
        combined = " ".join(" ".join(s.text.split()) for s in ordered)

        return ExtractionResult(query=query, selected=selected, combined_context=combined)

    def _resolve_crossencoder(self) -> Optional[str]:
        from sentence_transformers import CrossEncoder as CE
        for name in CROSSENCODER_CANDIDATES:
            try:
                CE(name, device=self.device)
                return name
            except Exception:
                continue
        return None

    def _segment(self, contexts: list[str]) -> list[ScoredSentence]:
        sentences: list[ScoredSentence] = []
        seen: set[str] = set()

        for idx, passage in enumerate(contexts):
            raw_sents = nltk.sent_tokenize(passage.strip())
            for raw in raw_sents:
                text = raw.strip()
                normalised = " ".join(text.lower().split())
                if not text or normalised in seen:
                    continue
                if len(text.split()) < self.min_sentence_tokens:
                    continue
                seen.add(normalised)
                sentences.append(ScoredSentence(text=text, source_idx=idx))

        return sentences

    def _biencoder_score(self, query: str, sentences: list[ScoredSentence]) -> list[ScoredSentence]:
        texts = [s.text for s in sentences]

        query_emb = self.biencoder.encode([query], normalize_embeddings=True, show_progress_bar=False)
        sent_embs = self.biencoder.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=64)

        scores = cosine_similarity(query_emb, sent_embs)[0]

        for sent, score in zip(sentences, scores):
            sent.bi_score = float(score)

        self._sent_embeddings = sent_embs
        self._emb_index = {s.text: i for i, s in enumerate(sentences)}

        return sentences

    def _crossencoder_rerank(self, query: str, candidates: list[ScoredSentence]) -> list[ScoredSentence]:
        pairs = [[query, s.text] for s in candidates]
        ce_scores = self.crossencoder.predict(pairs, show_progress_bar=False)

        for sent, score in zip(candidates, ce_scores):
            sent.ce_score = float(score)

        return candidates

    def _mmr_select(self, query: str, candidates: list[ScoredSentence], relevance_key):
        if not candidates:
            return []

        cand_embs = np.array(
            [self._sent_embeddings[self._emb_index[s.text]] for s in candidates]
        )

        raw_scores = np.array([relevance_key(s) for s in candidates], dtype=float)
        score_min, score_max = raw_scores.min(), raw_scores.max()
        if score_max > score_min:
            norm_scores = (raw_scores - score_min) / (score_max - score_min)
        else:
            norm_scores = np.ones_like(raw_scores)

        selected_indices = []
        remaining = list(range(len(candidates)))

        for _ in range(min(self.top_n, len(candidates))):
            if not selected_indices:
                best_idx = max(remaining, key=lambda i: norm_scores[i])
            else:
                sel_embs = cand_embs[selected_indices]
                rem_embs = cand_embs[remaining]
                sim_matrix = cosine_similarity(rem_embs, sel_embs)
                max_sim = sim_matrix.max(axis=1)

                mmr_scores = (
                    self.mmr_lambda * norm_scores[remaining]
                    - (1 - self.mmr_lambda) * max_sim
                )
                best_local = int(np.argmax(mmr_scores))
                best_idx = remaining[best_local]

            selected_indices.append(best_idx)
            remaining.remove(best_idx)

        return [candidates[i] for i in selected_indices]


class OllamaAnswerGenerator:
    def __init__(
        self,
        model: str = OLLAMA_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: int = 512,
        timeout: int = 600,
        system_prompt: str = SYSTEM_PROMPT,
        user_template: str = USER_TEMPLATE,
    ) -> None:
        import requests

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.system_prompt = system_prompt
        self.user_template = user_template
        self._requests = requests

        self._check_ollama_ready()

    def generate(self, query: str, context: str):
        user_message = self.user_template.format(context=context, question=query)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        prompt_repr = (
            f"[SYSTEM]\n{self.system_prompt}\n\n"
            f"[USER]\n{user_message}"
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_predict": self.max_tokens,
            },
        }

        response = self._requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        answer = data["message"]["content"].strip()

        return answer, prompt_repr, False

    def _check_ollama_ready(self):
        try:
            resp = self._requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except Exception:
            pass


class RAGAnswerPipeline:
    def __init__(
        self,
        extractor_kwargs: Optional[dict] = None,
        generator_kwargs: Optional[dict] = None,
        shared_device: Optional[str] = None,
    ) -> None:
        ext_kw = extractor_kwargs or {}
        gen_kw = generator_kwargs or {}

        if shared_device:
            ext_kw.setdefault("device", shared_device)

        self.extractor = SentenceExtractor(**ext_kw)
        self.generator = OllamaAnswerGenerator(**gen_kw)

    def run(self, query: str, contexts: list[str]) -> GenerationResult:
        extraction = self.extractor.extract(query=query, contexts=contexts)

        answer, prompt, truncated = self.generator.generate(
            query=query,
            context=extraction.combined_context,
        )

        return GenerationResult(
            query=query,
            extraction=extraction,
            answer=answer,
            prompt_used=prompt,
            truncated=truncated,
        )
