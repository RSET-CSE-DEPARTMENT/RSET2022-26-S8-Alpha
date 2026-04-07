import torch
import re
from transformers import T5Tokenizer, T5ForConditionalGeneration
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# BM25 — pip install rank-bm25
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("[WARN] rank-bm25 not installed. Run: pip install rank-bm25")

# Nomic embedding for semantic sentence scoring
try:
    from nomic import embed as nomic_embed
    NOMIC_AVAILABLE = True
except ImportError:
    NOMIC_AVAILABLE = False
    print("[WARN] nomic not installed. Run: pip install nomic")

# =====================================================
# Optional: BERTScore — pip install bert-score
# =====================================================
try:
    from bert_score import score as bert_score
    BERTSCORE_AVAILABLE = True
except ImportError:
    BERTSCORE_AVAILABLE = False

# =====================================================
# Configuration
# =====================================================
MODEL_NAME              = "google/flan-t5-large"
DEVICE                  = "cuda" if torch.cuda.is_available() else "cpu"
TOP_SENTENCES_PER_CHUNK = 3
MAX_ANSWER_SENTENCES    = 6

tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME, legacy=False)

if DEVICE == "cuda":
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME, torch_dtype=torch.float16)
else:
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)

model.to(DEVICE)
model.eval()
print(f"✅ Model loaded on {DEVICE}")


# =====================================================
# Utilities
# =====================================================
def clean_raw_text(text: str) -> str:
    """
    Cleans real retrieved biomedical text, handling:
    - Markdown bold/italic: **Table 1**, _p_, *text*
    - Figure/Table references: (Fig. 3), **Fig. 2B**, (Table 2)
    - Inline citations: [1], [2,3]
    - Escaped underscores from PDFs: _p_ → p
    - Confidence interval formatting: normalize (95% CI x, y)
    - Stray caption fragments starting with Fig./Table
    - et al. normalization
    """
    # Remove markdown bold and italic markers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # **bold** → bold
    text = re.sub(r'\*(.+?)\*',     r'\1', text)    # *italic* → italic
    text = re.sub(r'_(.+?)_',       r'\1', text)    # _italic_ → italic

    # Remove figure/table caption fragments (e.g. "Fig. 2 Effect of..." or "Table 1 Demographic...")
    text = re.sub(r'\bFig\.?\s*\d+[A-Za-z]?\b[^.]*', '', text)
    text = re.sub(r'\bTable\s+\d+\b[^.]*',            '', text)

    # Remove inline citation brackets: [1], [1,2], [1-3]
    text = re.sub(r'\[\d+(?:[,\-]\s*\d+)*\]', '', text)

    # Remove hyperlink artifacts from PDF/HTML extraction
    # Handles all these patterns seen in real retrieved text:
    #   [text](javascript:void(0))  →  text
    #   and](javascript:void(0))    →  and          (text before ] with no opening [)
    #   [text](https://...)         →  text
    #   (javascript:void(0))        →  (removed)
    text = re.sub(r'\[([^\]]+)\]\(javascript:[^)]*\)', r'\1', text)  # [text](js)
    text = re.sub(r'\]\(javascript:[^)]*\)',              '',     text)  # ](js) — no opening bracket
    text = re.sub(r'\[([^\]]+)\]\(https?://[^)]*\)',   r'\1', text)  # [text](url)
    text = re.sub(r'\(javascript:[^)]*\)',                 '',     text)  # bare (js)
    text = re.sub(r'javascript:void\(0\)',                 '',     text)  # stray js text

    # Remove orphaned open brackets: [deaths globally → deaths globally
    text = re.sub(r'\[([^\]]*?)(?=\s+\w)', r'\1', text)

    # Remove HTML tags and partial tags: <br>, <br/>, br>, .br>
    text = re.sub(r'\.?br>',  '', text)   # .br> or br> artifacts
    text = re.sub(r'<[^>]+>',  '', text)   # full HTML tags
    text = re.sub(r'&nbsp;',   ' ', text)
    text = re.sub(r'&amp;',    '&', text)
    text = re.sub(r'&lt;',     '<', text)
    text = re.sub(r'&gt;',     '>', text)

    # Remove stray lone ) left after javascript removal: "and) outcomes" → "and outcomes"
    text = re.sub(r'(?<=\w)\)\s', ' ', text)

    # Remove parenthetical figure/table refs: (Fig. 3), (Figure 2A), (Fig. 3A, B)
    text = re.sub(r'\(\s*Fig(?:ure)?\.?\s*\d+[A-Za-z]?\s*\)', '', text)
    text = re.sub(r'\(\s*Table\s*\d+\s*\)',                    '', text)

    # Also catch semicolon-separated refs inside parens: (...; p < 0.001) followed by ref
    # Remove trailing fig ref inside a closing paren: "; p < 0.001) (Fig. 3)" style
    text = re.sub(r'\(\s*Fig(?:ure)?\.?\s*\d+[A-Za-z]?\s*[,;]?\s*\)', '', text)

    # Normalize p-value formatting: _p_ < 0.001 → p < 0.001
    text = re.sub(r'_\s*p\s*_', 'p', text)

    # Normalize unicode comparison symbols
    text = re.sub(r'−', '-', text)      # unicode minus → hyphen-minus
    text = re.sub(r'≥', '>=', text)     # unicode ≥ → >=
    text = re.sub(r'≤', '<=', text)     # unicode ≤ → <=
    text = re.sub(r'±', '+/-', text)    # unicode ± → +/-
    text = re.sub(r'\s+-\s+', ' - ', text)  # normalize spaced dashes

    # Remove trailing orphaned open parenthesis at end of text
    # e.g. "dramatically increased ( ." or "group ( ."
    text = re.sub(r'\s*\(\s*\.?\s*$', '.', text)

    # Normalize et al.
    text = re.sub(r'et al\.', 'et al', text)

    # Clean up stray empty parentheses left after removing fig/table refs
    # e.g. "(. .)" or "( )" artifacts
    text = re.sub(r'\(\s*[.;,\s]*\)',   '', text)
    text = re.sub(r'\(\s*\.\s*\.\s*\)', '', text)
    # Remove any remaining unmatched open parens at end of clause
    text = re.sub(r'\s*\(\s*\.?\s*$',  '', text)
    text = re.sub(r'\s*\(\.\s',        ' ', text)

    # Fix space before punctuation: "group ." → "group."
    text = re.sub(r'\s+([.!?,;])', r'\1', text)

    # Collapse whitespace
    return " ".join(text.split()).strip()


def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def split_into_sentences(text: str) -> list[str]:
    """
    Splits cleaned biomedical text into sentences.
    Extra filters for real retrieved text:
    - Drops pure caption/label fragments (no verb likely)
    - Drops sentences that are just numbers/percentages with no context
    - Requires minimum 7 words (raised from 6 to filter table row fragments)
    """
    # Protect abbreviations from false splits
    text = re.sub(r'\b(Fig|Tab|Dr|Prof|et al|vs|approx|Ref|No|Vol|pp|CI|HbA1c)\.', r'\1<P>', text)

    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    sentences = [s.replace('<P>', '.').strip() for s in sentences]

    clean = []
    for s in sentences:
        # Must end with proper punctuation
        if not s or s[-1] not in '.!?':
            continue
        # Must have at least 7 words
        if len(s.split()) < 7:
            continue
        # Drop fragments that are purely numeric/percentage lists
        # (table row artifacts like "70.0%; 81.8%; 78.6%")
        non_numeric = re.sub(r'[\d\s%();,.\-/]', '', s)
        if len(non_numeric) < 10:
            continue
        # Drop sentences containing cleaning artifacts (leftover ". ." or "(. .")
        if re.search(r'\(\.\s*\.|\.\s+\.', s):
            continue
        clean.append(s)

    return clean

def all_numbers_preserved(original: str, paraphrased: str) -> bool:
    """
    Checks that every number, percentage, and p-value in the original
    sentence also appears in the paraphrased version.
    Returns True if all numbers are preserved, False if any are missing.
    """
    numbers = re.findall(r'\d+\.?\d*', original)
    for n in numbers:
        if n not in paraphrased:
            return False
    return True


# =====================================================
# 1. Hybrid BM25 + Nomic Semantic Sentence Extraction
#
#    Replaces TF-IDF with a two-signal hybrid scorer:
#
#    Signal A — BM25 (keyword matching)
#      Rewards sentences that share exact terms with the
#      query. Strong for precise biomedical terms like
#      "HbA1c", "gliclazide", "p=0.003", "42% reduction".
#
#    Signal B — Nomic semantic embeddings (meaning matching)
#      Rewards sentences semantically related to the query
#      even with no word overlap. Strong for conceptual
#      queries like "symptoms of malaria" matching
#      "fever, chills and headache are observed".
#
#    Final score = alpha * BM25_norm + (1-alpha) * semantic_norm
#
#    alpha=0.5  → equal weight (default, good general use)
#    alpha=0.7  → favor keywords (better for metric queries)
#    alpha=0.3  → favor semantics (better for concept queries)
#
#    Fallback chain:
#      Both available  → hybrid scoring
#      BM25 only       → BM25 scoring
#      Nomic only      → semantic scoring
#      Neither         → TF-IDF (original method, always works)
# =====================================================

def _normalize(arr: np.ndarray) -> np.ndarray:
    """Min-max normalize array to 0-1 range."""
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-9:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


def _bm25_scores(query: str, sentences: list[str]) -> np.ndarray:
    """Score sentences against query using BM25Okapi."""
    tokenized_sents  = [s.lower().split() for s in sentences]
    tokenized_query  = query.lower().split()
    bm25             = BM25Okapi(tokenized_sents)
    return np.array(bm25.get_scores(tokenized_query))


def _semantic_scores(query: str, sentences: list[str]) -> np.ndarray:
    """
    Score sentences against query using Nomic embeddings.
    Query uses task_type="search_query",
    sentences use task_type="search_document" — critical for
    Nomic v1 asymmetric retrieval accuracy.
    """
    try:
        q_resp = nomic_embed.text(
            texts=[query],
            model="nomic-embed-text-v1",
            task_type="search_query"
        )
        s_resp = nomic_embed.text(
            texts=sentences,
            model="nomic-embed-text-v1",
            task_type="search_document"
        )
        query_vec  = np.array(q_resp["embeddings"])          # (1, dim)
        sent_vecs  = np.array(s_resp["embeddings"])          # (N, dim)
        return cosine_similarity(query_vec, sent_vecs).flatten()
    except Exception as e:
        print(f"   [WARN] Nomic embedding failed: {e} — falling back to BM25/TF-IDF")
        return None


def extract_top_sentences(
    query: str,
    chunk_text: str,
    top_n: int = TOP_SENTENCES_PER_CHUNK,
    alpha: float = 0.5
) -> list[str]:
    """
    Extracts top_n most relevant sentences from chunk_text using
    hybrid BM25 + Nomic semantic scoring.

    Args:
        query:      The biomedical research question.
        chunk_text: Raw text of one retrieved chunk.
        top_n:      Number of sentences to return.
        alpha:      Weight for BM25 vs semantic (0=all semantic, 1=all BM25).
                    Default 0.5 = equal weight.

    Returns:
        List of top_n sentences in original reading order.
    """
    clean_text = clean_raw_text(chunk_text)
    sentences  = split_into_sentences(clean_text)

    if not sentences:
        return []
    if len(sentences) <= top_n:
        return sentences

    # ---- Signal A: BM25 ----
    bm25_raw = None
    if BM25_AVAILABLE:
        try:
            bm25_raw = _bm25_scores(query, sentences)
        except Exception as e:
            print(f"   [WARN] BM25 scoring failed: {e}")

    # ---- Signal B: Nomic Semantic ----
    sem_raw = None
    if NOMIC_AVAILABLE:
        sem_raw = _semantic_scores(query, sentences)

    # ---- Combine signals ----
    if bm25_raw is not None and sem_raw is not None:
        # Full hybrid
        scores = alpha * _normalize(bm25_raw) + (1 - alpha) * _normalize(sem_raw)
        method = f"hybrid (BM25 {alpha:.0%} + semantic {1-alpha:.0%})"

    elif bm25_raw is not None:
        scores = _normalize(bm25_raw)
        method = "BM25 only"

    elif sem_raw is not None:
        scores = _normalize(sem_raw)
        method = "semantic only"

    else:
        # Final fallback — TF-IDF (original method, no dependencies)
        try:
            corpus = [query] + sentences
            tfidf  = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(corpus)
            scores = cosine_similarity(tfidf[0], tfidf[1:]).flatten()
            method = "TF-IDF fallback"
        except ValueError:
            return sentences[:top_n]

    print(f"   📐 Extraction method: {method}")

    # Return top_n sentences in original reading order
    top_idx = sorted(np.argsort(scores)[::-1][:top_n])
    return [sentences[i] for i in top_idx]


# =====================================================
# 2. Deduplication
# =====================================================
def deduplicate_sentences(sentences: list[str], threshold: float = 0.85) -> list[str]:
    if len(sentences) <= 1:
        return sentences
    try:
        tfidf = TfidfVectorizer(stop_words="english").fit_transform(sentences)
        kept  = [0]
        for i in range(1, len(sentences)):
            sims = cosine_similarity(tfidf[i], tfidf[np.array(kept)]).flatten()
            if sims.max() < threshold:
                kept.append(i)
        return [sentences[i] for i in kept]
    except ValueError:
        return sentences


# =====================================================
# 3. Sentence Role Classifier
# =====================================================
EFFICACY_KW     = {"%", "p=", "p =", "reduction", "improvement", "week",
                   "placebo", "trial", "rct", "significant", "mg", "daily", "marker"}
MECHANISM_KW    = {"mechanism", "pathway", "suppress", "cytokine",
                   "il-6", "inhibit", "confirmed", "assay", "signaling"}
SAFETY_KW       = {"tolerat", "adverse", "side effect", "safety", "resolved"}
CONFLICT_KW     = {"contrary", "however", "discrepan", "unlike",
                   "did not reach", "inconsistent"}
SYMPTOM_KW      = {"symptom", "sign", "present", "fever", "chill", "headache",
                   "myalgia", "nausea", "vomit", "diarrhea", "diarrhoea", "cough",
                   "fatigue", "pain", "anemia", "anaemia", "jaundice", "seizure",
                   "confusion", "respiratory", "characterize", "characterized",
                   "manifest", "complain", "feature", "clinical", "finding",
                   "complication", "severe", "mild", "acute", "chronic",
                   "neurolog", "cerebral", "organ failure", "distress"}
EPIDEMIOLOGY_KW = {"incidence", "prevalence", "mortality", "morbidity",
                   "case", "reported", "endemic", "outbreak", "burden",
                   "million", "billion", "deaths", "globally", "worldwide",
                   "estimated", "population", "region", "country", "countries"}

def classify_sentence(sentence: str) -> str:
    """
    Classifies a sentence into one of 7 roles.
    Order matters — more specific roles checked first.
    'other' is now a valid fallback included in the draft.
    """
    s = sentence.lower()
    if any(kw in s for kw in CONFLICT_KW):      return "conflict"
    if any(kw in s for kw in MECHANISM_KW):     return "mechanism"
    if any(kw in s for kw in EFFICACY_KW):      return "efficacy"
    if any(kw in s for kw in SYMPTOM_KW):       return "symptoms"
    if any(kw in s for kw in EPIDEMIOLOGY_KW):  return "epidemiology"
    if any(kw in s for kw in SAFETY_KW):        return "safety"
    return "other"


# =====================================================
# 4. Python-Assembled Structured Draft
# =====================================================
def build_structured_draft(query: str, all_sentences: list[str]) -> list[str]:
    """
    Classifies, ranks, and orders sentences.
    Returns an ordered LIST of sentences (not joined string)
    so the paraphraser can process them one at a time.
    """
    # All known roles including new symptom and epidemiology buckets
    all_roles = ["efficacy", "mechanism", "conflict", "symptoms",
                 "epidemiology", "safety", "other"]
    buckets   = {role: [] for role in all_roles}

    for s in all_sentences:
        buckets[classify_sentence(s)].append(s)

    def rank_bucket(sents):
        if len(sents) <= 1:
            return sents
        try:
            corpus = [query] + sents
            tfidf  = TfidfVectorizer(stop_words="english").fit_transform(corpus)
            scores = cosine_similarity(tfidf[0], tfidf[1:]).flatten()
            return [sents[i] for i in np.argsort(scores)[::-1]]
        except ValueError:
            return sents

    for role in buckets:
        buckets[role] = rank_bucket(buckets[role])

    # Detect the dominant intent of the query to adjust caps dynamically.
    # This prevents epidemiology sentences from crowding out symptom sentences
    # on symptom queries, and vice versa on incidence/burden queries.
    query_lower = query.lower()
    is_symptom_query     = any(kw in query_lower for kw in
                               {"symptom", "sign", "present", "feature",
                                "clinical", "manifest", "characterize"})
    is_efficacy_query    = any(kw in query_lower for kw in
                               {"efficacy", "effect", "outcome", "result",
                                "treatment", "therapy", "reduce", "improve"})
    is_epidemiology_query = any(kw in query_lower for kw in
                                {"incidence", "prevalence", "burden", "mortality",
                                 "how many", "cases", "deaths", "rate"})

    # Base caps — adjusted by query intent below
    role_caps = {
        "efficacy":     3,
        "mechanism":    2,
        "conflict":     2,
        "symptoms":     3,
        "epidemiology": 2,
        "safety":       1,
        "other":        2    # fallback — ensures answer is never empty
    }

    if is_symptom_query:
        role_caps["symptoms"]     = 4   # boost symptoms
        role_caps["epidemiology"] = 1   # suppress epi (just 1 for context)
        role_caps["efficacy"]     = 1   # suppress efficacy on symptom queries

    elif is_efficacy_query:
        role_caps["efficacy"]     = 4   # boost efficacy
        role_caps["symptoms"]     = 1   # suppress symptoms
        role_caps["epidemiology"] = 1

    elif is_epidemiology_query:
        role_caps["epidemiology"] = 4   # boost epidemiology
        role_caps["symptoms"]     = 1
        role_caps["efficacy"]     = 1

    # Ordering: direct answer roles first, context second, caveats last
    role_order = ["efficacy", "symptoms", "mechanism", "epidemiology",
                  "conflict", "safety", "other"]

    selected = []
    for role in role_order:
        selected.extend(buckets[role][:role_caps[role]])

    selected = selected[:MAX_ANSWER_SENTENCES]

    print(f"   📋 Draft sentences by role:")
    for s in selected:
        print(f"      [{classify_sentence(s):12s}] {s[:72]}...")

    return selected


# =====================================================
# 5. Sentence-by-Sentence Paraphrasing
#
#    Strategy: paraphrase ONE sentence at a time.
#    Each call is tiny (~30-60 tokens input) — well within
#    what Flan-T5 Large handles reliably.
#
#    Strict fallback per sentence:
#    - If the paraphrase drops any number → use original
#    - If the paraphrase is >2x longer → use original
#    - If the paraphrase is <50% of original length → use original
#    - If it echoes the prompt → use original
#
#    This guarantees no facts are ever lost. The worst case
#    is the original sentence appears unchanged.
# =====================================================
def paraphrase_sentence(sentence: str) -> str:
    """
    Paraphrases a single sentence using Flan-T5.
    Validates the output strictly — falls back to original if anything is wrong.
    """
    prompt = (
        f"Paraphrase the following scientific sentence. "
        f"Keep all numbers, percentages, and p-values exactly as they are. "
        f"Sentence: {sentence} "
        f"Paraphrase:"
    )

    inputs = tokenizer(
        prompt, return_tensors="pt",
        truncation=True, max_length=512
    ).to(DEVICE)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=80,
            min_new_tokens=10,
            num_beams=4,
            repetition_penalty=2.5,
            no_repeat_ngram_size=3,
            early_stopping=False
        )

    result = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    # Strip echoed labels
    result = re.sub(
        r'^(Paraphrase\s*:|Answer\s*:|Sentence\s*:)',
        '', result, flags=re.IGNORECASE
    ).strip()

    # Ensure it ends with punctuation
    if result and result[-1] not in '.!?':
        result += '.'

    original_words = len(sentence.split())
    result_words   = len(result.split())

    # Validation checks — fall back to original if any fail
    if not all_numbers_preserved(sentence, result):
        print(f"      ⚠️  Number dropped — using original")
        return sentence

    if result_words < original_words * 0.5:
        print(f"      ⚠️  Too short ({result_words} vs {original_words} words) — using original")
        return sentence

    if result_words > original_words * 2.5:
        print(f"      ⚠️  Too long ({result_words} vs {original_words} words) — using original")
        return sentence

    # If result is nearly identical to input (>90% word overlap), keep original
    orig_words   = set(sentence.lower().split())
    result_set   = set(result.lower().split())
    overlap      = len(orig_words & result_set) / max(len(orig_words), 1)
    if overlap > 0.90:
        print(f"      ⚠️  Too similar to input (overlap {overlap:.0%}) — using original")
        return sentence

    return result


def paraphrase_draft(sentences: list[str]) -> list[str]:
    """
    Paraphrases each sentence individually and returns the results.
    Prints which sentences were paraphrased vs kept as original.
    """
    print(f"   ✏️  Paraphrasing {len(sentences)} sentences individually...")
    results = []
    for i, sent in enumerate(sentences):
        paraphrased = paraphrase_sentence(sent)
        changed     = paraphrased.lower().strip() != sent.lower().strip()
        status      = "✓ paraphrased" if changed else "= original"
        print(f"      [{i+1}] {status}: {paraphrased[:70]}...")
        results.append(paraphrased)
    return results


# =====================================================
# 6. Transition Injector
#
#    Adds connective phrases between sentences based on
#    the role transition — no model needed, pure Python.
#
#    Transition map: (from_role, to_role) → prefix phrase
#    Only the FIRST word(s) of the next sentence are
#    replaced/prepended — the rest stays exactly as-is
#    so no facts are ever altered.
# =====================================================

# Maps (from_role, to_role) → transition prefix to prepend to the next sentence.
# "SAME" means the from_role equals the to_role.
TRANSITIONS = {
    # symptoms → other roles
    ("symptoms",     "symptoms"):      "Additionally,",
    ("symptoms",     "mechanism"):     "This is mediated by",
    ("symptoms",     "conflict"):      "However,",
    ("symptoms",     "epidemiology"):  "Globally,",
    ("symptoms",     "efficacy"):      "In clinical trials,",
    ("symptoms",     "safety"):        "Regarding safety,",
    ("symptoms",     "other"):         "Furthermore,",

    # efficacy → other roles
    ("efficacy",     "efficacy"):      "Furthermore,",
    ("efficacy",     "mechanism"):     "Mechanistically,",
    ("efficacy",     "conflict"):      "However,",
    ("efficacy",     "symptoms"):      "Clinically,",
    ("efficacy",     "epidemiology"):  "In terms of disease burden,",
    ("efficacy",     "safety"):        "Regarding tolerability,",

    # mechanism → other roles
    ("mechanism",    "mechanism"):     "Additionally,",
    ("mechanism",    "conflict"):      "However,",
    ("mechanism",    "efficacy"):      "In terms of efficacy,",
    ("mechanism",    "symptoms"):      "Clinically, this manifests as",
    ("mechanism",    "epidemiology"):  "On a global scale,",

    # conflict → other roles
    ("conflict",     "conflict"):      "Furthermore,",
    ("conflict",     "efficacy"):      "Despite this,",
    ("conflict",     "symptoms"):      "Clinically,",
    ("conflict",     "epidemiology"):  "Globally,",
    ("conflict",     "other"):         "Additionally,",

    # epidemiology → other roles
    ("epidemiology", "epidemiology"):  "Furthermore,",
    ("epidemiology", "symptoms"):      "Clinically, infected patients present with",
    ("epidemiology", "efficacy"):      "In clinical settings,",
    ("epidemiology", "mechanism"):     "The underlying mechanism involves",
    ("epidemiology", "conflict"):      "However,",

    # safety → other roles
    ("safety",       "other"):         "Additionally,",
    ("safety",       "efficacy"):      "In terms of efficacy,",
    ("safety",       "conflict"):      "However,",

    # other → anything
    ("other",        "symptoms"):      "Clinically,",
    ("other",        "efficacy"):      "In clinical trials,",
    ("other",        "mechanism"):     "Mechanistically,",
    ("other",        "conflict"):      "However,",
    ("other",        "epidemiology"):  "Globally,",
    ("other",        "other"):         "Additionally,",
}


def _strip_leading_connective(sentence: str) -> str:
    """
    Removes existing leading connective words from a sentence before
    injecting a new transition, to avoid doubling up.
    e.g. "However, malaria..." → "malaria..." if we're adding "However,"
    """
    # Common sentence starters that would clash with injected transitions
    connectives = r"^(However|Furthermore|Additionally|Moreover|Also|"                   r"Notably|Importantly|Clinically|Globally|Meanwhile|"                   r"Conversely|Nevertheless|In contrast|In addition|"                   r"On the other hand|In terms of|Regarding|Despite this)[,.]?\s*"
    return re.sub(connectives, "", sentence, flags=re.IGNORECASE).strip()


def inject_transitions(sentences: list[str]) -> list[str]:
    """
    Takes the ordered list of draft sentences and injects appropriate
    transition phrases between sentences based on their role transitions.

    Rules:
    - First sentence never gets a transition prefix
    - Transition is looked up from (prev_role, curr_role) pair
    - If no transition is defined for that pair, no prefix is added
    - The first word of the sentence is capitalised after injection
    - Existing leading connectives are stripped before injection
      to prevent doubling (e.g. "However, However,...")
    """
    if not sentences:
        return sentences

    result    = [sentences[0]]  # First sentence — no transition
    prev_role = classify_sentence(sentences[0])

    for sentence in sentences[1:]:
        curr_role  = classify_sentence(sentence)
        transition = TRANSITIONS.get((prev_role, curr_role), "")

        if transition:
            # Strip any existing leading connective from the sentence
            cleaned = _strip_leading_connective(sentence)
            # Lowercase the first word of the sentence body
            if cleaned:
                cleaned = cleaned[0].lower() + cleaned[1:]

            # Avoid duplicate trailing words that match the transition
            # e.g. "Globally, ...deaths globally." → remove trailing "globally"
            transition_word = transition.rstrip(",. ").lower()
            if cleaned.lower().endswith(transition_word + "."):
                cleaned = cleaned[:-(len(transition_word) + 1)].rstrip() + "."

            # Use "Notably" instead of "Additionally" for negative/absence sentences
            final_transition = transition
            if any(neg in cleaned.lower() for neg in
                   {"no ", "not ", "none ", "neither ", "without ", "absence"}):
                if transition in {"Additionally,", "Furthermore,"}:
                    final_transition = "Notably,"

            result.append(f"{final_transition} {cleaned}")
        else:
            result.append(sentence)

        prev_role = curr_role

    return result


# =====================================================
# 7. Optional: BERTScore Evaluation
# =====================================================
def evaluate_with_bertscore(generated_answer: str, source_texts: list[str]) -> dict:
    if not BERTSCORE_AVAILABLE:
        return {"error": "bert-score not installed. Run: pip install bert-score"}
    references = [" ".join(source_texts)]
    P, R, F1   = bert_score([generated_answer], references, lang="en", verbose=False)
    return {
        "bertscore_precision": round(P.mean().item(), 4),
        "bertscore_recall":    round(R.mean().item(), 4),
        "bertscore_f1":        round(F1.mean().item(), 4),
    }


# =====================================================
# 7. Integrated Entry Point
# =====================================================
def get_final_rag_answer(
    user_query: str,
    retrieved_results: list[dict],
    top_sentences: int = TOP_SENTENCES_PER_CHUNK,
    run_evaluation: bool = False,
    alpha: float = None        # BM25 vs semantic weight. None = auto-detect from query.
) -> dict:
    if not retrieved_results:
        return {"answer": "No sufficient evidence found.", "num_sources": 0}

    section_priority = {
        "Results": 0, "Discussion": 1, "Conclusion": 2,
        "Methods": 3, "Abstract": 4, "Introduction": 5
    }
    retrieved_results = sorted(
        retrieved_results,
        key=lambda x: section_priority.get(x.get("section", "General"), 6)
    )

    # Step 1: Auto-detect alpha from query intent if not explicitly set.
    #
    #   alpha controls the BM25 vs semantic balance:
    #     alpha=0.7 → keyword-heavy  (exact metrics: "mean HbA1c", "p=0.003")
    #     alpha=0.5 → balanced       (general clinical queries)
    #     alpha=0.3 → semantic-heavy (conceptual: "symptoms", "mechanism")
    #
    if alpha is None:
        q_lower = user_query.lower()
        if any(kw in q_lower for kw in
               {"mean", "average", "p=", "p <", "ci", "%" , "mg",
                "dose", "dosage", "hba1c", "mmol", "change in"}):
            alpha = 0.7   # metric query — favor exact keyword match
            print(f"   🎯 Query type: METRIC  → alpha={alpha} (keyword-heavy)")
        elif any(kw in q_lower for kw in
                 {"symptom", "sign", "present", "feature", "manifest",
                  "mechanism", "pathway", "cause", "effect", "why"}):
            alpha = 0.3   # conceptual query — favor semantic understanding
            print(f"   🎯 Query type: CONCEPT → alpha={alpha} (semantic-heavy)")
        else:
            alpha = 0.5   # balanced default
            print(f"   🎯 Query type: GENERAL → alpha={alpha} (balanced)")

    # Step 1: Extract
    print(f"🔍 Extracting top {top_sentences} sentences from {len(retrieved_results)} chunks...")
    all_extracted = []
    for res in retrieved_results:
        section = res.get("section", "General")
        sents   = extract_top_sentences(
                      user_query, res["text"],
                      top_n=top_sentences,
                      alpha=alpha
                  )
        all_extracted.extend(sents)
        if sents:
            print(f"   [{section}] {sents[0][:80]}...")

    if not all_extracted:
        return {"answer": "No relevant sentences found.", "num_sources": 0}

    # Step 2: Deduplicate
    unique = deduplicate_sentences(all_extracted)
    print(f"   ✅ {len(all_extracted)} → {len(unique)} sentences after deduplication")

    # Step 3: Build structured draft (returns ordered list)
    print(f"📋 Building structured draft...")
    draft_sentences = build_structured_draft(user_query, unique)
    draft           = " ".join(draft_sentences)

    if not draft.strip():
        return {"answer": "Could not assemble answer from evidence.", "num_sources": 0}

    # Step 4: Paraphrase sentence by sentence
    print(f"✨ Paraphrasing sentence by sentence...")
    paraphrased_sentences = paraphrase_draft(draft_sentences)

    # Step 5: Inject transitions between sentences based on role pairs
    print(f"🔗 Injecting transitions...")
    transitioned_sentences = inject_transitions(paraphrased_sentences)
    answer                 = " ".join(transitioned_sentences)

    print(f"✅ Done — {len(answer.split())} words.")

    result = {
        "answer":      answer,
        "num_sources": len(retrieved_results),
        "draft":       draft
    }

    if run_evaluation:
        scores               = evaluate_with_bertscore(answer, [draft])
        result["evaluation"] = scores
        print(f"📊 BERTScore F1: {scores.get('bertscore_f1', 'N/A')}")

    return result


# =====================================================
# Smoke Test
# =====================================================
if __name__ == "__main__":
    sample_results = [
        {
            "source":  "Smith et al. 2023",
            "section": "Results",
            "text": (
                "Patients receiving Drug X (50mg daily) showed a 42% reduction in "
                "inflammatory markers (p=0.003) over 12 weeks compared to placebo. "
                "Adverse events were mild and resolved without intervention. "
                "The drug was well tolerated across all age groups in the study cohort."
            )
        },
        {
            "source":  "Jones et al. 2022",
            "section": "Discussion",
            "text": (
                "The 20-week cohort demonstrated a 38% improvement (p=0.01), slightly "
                "lower than the 12-week trial, potentially due to patient attrition. "
                "Drug X's mechanism involves IL-6 pathway suppression. "
                "This suppression was confirmed via serum cytokine assays."
            )
        },
        {
            "source":  "Lee et al. 2024",
            "section": "Results",
            "text": (
                "Contrary to earlier findings, our RCT observed only a 15% reduction "
                "in the same markers (p=0.08), which did not reach statistical significance. "
                "Higher baseline BMI in our cohort may explain the discrepancy. "
                "Further stratified analysis by BMI subgroup is recommended."
            )
        }
    ]

    query  = "What is the clinical efficacy and mechanism of Drug X for reducing inflammation?"
    output = get_final_rag_answer(query, sample_results, top_sentences=3, run_evaluation=False)

    print("\n" + "=" * 60)
    print("STRUCTURED DRAFT (Python-assembled):")
    print("=" * 60)
    print(output["draft"])

    print("\n" + "=" * 60)
    print("FINAL ANSWER (sentence-by-sentence paraphrase):")
    print("=" * 60)
    print(output["answer"])
    print(f"\nSources used: {output['num_sources']}")