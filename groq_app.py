import csv
import json
from ddgs import DDGS
import os, io, tempfile, textwrap
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import List, Literal
import streamlit as st

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from pptx import Presentation as PptxPresentation
from youtube_transcript_api import YouTubeTranscriptApi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROVIDER = os.getenv("RAG_PROVIDER", "groq").strip().lower()
PROVIDERS = {
    "groq": {"label": "Groq", "key_env": "GROQ_API_KEY", "model_env": "GROQ_MODEL", "default_model": ""},
    "openai": {"label": "OpenAI", "key_env": "OPENAI_API_KEY", "model_env": "OPENAI_MODEL", "default_model": "gpt-4o-mini"},
    "gemini": {"label": "Google Gemini", "key_env": "GOOGLE_API_KEY", "model_env": "GEMINI_MODEL", "default_model": "gemini-3.8-flash"},
    "anthropic": {"label": "Anthropic", "key_env": "ANTHROPIC_API_KEY", "model_env": "ANTHROPIC_MODEL", "default_model": "claude-sonnet-4-20250514"},
}
if PROVIDER not in PROVIDERS:
    raise ValueError(f"Unsupported RAG_PROVIDER: {PROVIDER}")

def get_api_keys(runtime_key: str = "") -> List[str]:
    provider = PROVIDERS[PROVIDER]
    env_names = [provider["key_env"]]
    if PROVIDER == "gemini":
        env_names.append("GEMINI_API_KEY")
    keys = []
    if PROVIDER == "groq":
        keys.extend(key.strip() for key in os.getenv("GROQ_API_KEYS", "").split(",") if key.strip())
    for env_name in env_names:
        keys.extend(key.strip() for key in os.getenv(env_name, "").split(",") if key.strip())
    try:
        secret_keys = [st.secrets.get(env_name, "") for env_name in env_names]
    except (FileNotFoundError, KeyError):
        secret_keys = []
    keys = [key.strip() for key in secret_keys if key.strip()] + keys
    if runtime_key.strip():
        keys.insert(0, runtime_key.strip())
    return list(dict.fromkeys(keys))

API_KEYS = get_api_keys()

st.set_page_config(
    page_title=f"Multi-Format Information Retriever | {PROVIDERS[PROVIDER]['label']}",
    page_icon="🌌",
    layout="wide",
)

# ── Light theme ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

:root {
    --page: #F8FAFC;
    --sidebar: #F1F5F9;
    --surface: #FFFFFF;
    --line: #E2E8F0;
    --line-strong: #CBD5E1;
    --ink: #0F172A;
    --muted: #64748B;
    --accent: #2563EB;
    --accent-soft: #EFF6FF;
}

.stApp,
[data-testid="stAppViewContainer"] {
    background: var(--page);
    color: var(--ink);
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
section[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] > div { background: var(--sidebar); }
main .block-container {
    max-width: 1040px;
    padding-top: 1.6rem;
    padding-bottom: 4rem;
}
h1, h2, h3, h4, h5, h6 {
    color: var(--ink) !important;
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    letter-spacing: 0;
}
h1 { color: var(--ink) !important; font-size: 1.25rem; }
section[data-testid="stSidebar"] h1 {
    margin: 0.15rem 0 0.35rem;
    font-family: 'Manrope', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    line-height: 1.15;
}
p, label, [data-testid="stMarkdownContainer"] { color: var(--ink); }
[data-testid="stCaptionContainer"] { color: var(--muted); }
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p,
.stApp label { color: var(--ink) !important; }
hr { border-color: var(--line); }

.rail-eyebrow, .workspace-eyebrow, .workspace-status-label,
.empty-kicker, .rail-section-label {
    color: #64748B;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.rail-eyebrow { margin: 0.35rem 0 0.4rem; }
.rail-intro {
    margin: 0 0 1.25rem;
    color: #64748B;
    font-size: 0.88rem;
    line-height: 1.5;
}
.rail-section-label {
    margin: 1.25rem 0 0.6rem;
    padding-top: 0.85rem;
    border-top: 1px solid #DCE3EC;
}
.rail-key-note { margin: -0.25rem 0 0.25rem; color: #64748B; font-size: 0.76rem; }
.workspace-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    padding: 0.55rem 0 1.35rem;
    border-bottom: 1px solid var(--line);
}
.workspace-eyebrow { margin-bottom: 0.45rem; }
.workspace-eyebrow span { color: #CBD5E1; padding: 0 0.35rem; }
.workspace-title {
    margin: 0;
    color: #0F172A !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    line-height: 1.12 !important;
    letter-spacing: 0 !important;
}
.workspace-subtitle { margin: 0.45rem 0 0; color: #64748B; font-size: 0.92rem; }
.workspace-status {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding: 0.65rem 0.8rem;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    background: #FFFFFF;
    white-space: nowrap;
}
.status-light { width: 0.5rem; height: 0.5rem; border-radius: 50%; background: #10B981; }
.workspace-status-label { display: block; margin-bottom: 0.12rem; font-size: 0.6rem; }
.workspace-status strong { color: #0F172A; font-size: 0.82rem; font-weight: 700; }
.status-count { padding-left: 0.85rem; border-left: 1px solid #E2E8F0; color: #64748B; font-size: 0.78rem; }
.status-count strong { display: block; color: #0F172A; font-size: 1rem; }
.conversation-empty {
    display: flex;
    align-items: center;
    gap: 1rem;
    min-height: 35vh;
    padding: 1.75rem 0;
    border-bottom: 1px solid #E2E8F0;
}
.empty-index {
    display: grid;
    width: 2.75rem;
    height: 2.75rem;
    place-items: center;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
    background: #EFF6FF;
    color: #2563EB;
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
}
.empty-kicker { margin: 0 0 0.25rem; }
.conversation-empty h2 { margin: 0; color: #0F172A; font-size: 1.05rem; font-weight: 700; }
.conversation-empty p:last-child { margin: 0.3rem 0 0; color: #64748B; font-size: 0.86rem; }
@media (max-width: 700px) {
    main .block-container { padding: 1.1rem 1rem 5rem; }
    .workspace-head { align-items: flex-start; flex-direction: column; gap: 0.9rem; }
    .workspace-title { font-size: 1.8rem; }
    .workspace-status { align-self: stretch; justify-content: flex-start; }
    .conversation-empty { min-height: 28vh; }
}

div.stButton > button {
    min-height: 2.75rem;
    border: 1px solid var(--accent);
    border-radius: 10px;
    background: var(--accent);
    color: #FFFFFF;
    font-weight: 700;
    transition: background 150ms ease, box-shadow 150ms ease, transform 150ms ease;
}
div.stButton > button:hover {
    border-color: #1D4ED8;
    background: #1D4ED8;
    color: #FFFFFF;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    transform: translateY(-1px);
}
div.stButton > button:focus-visible {
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.22);
}

input, textarea,
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {
    border-color: var(--line-strong) !important;
    border-radius: 10px !important;
    background: var(--surface) !important;
    color: var(--ink) !important;
}
input::placeholder, textarea::placeholder { color: #94A3B8 !important; }
input:focus, textarea:focus,
[data-baseweb="input"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12) !important;
}

[data-testid="stFileUploader"] section {
    border: 1px dashed var(--line-strong);
    border-radius: 12px;
    background: var(--surface);
}
[data-testid="stFileUploader"],
div[data-testid="stFileUploader"],
section[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
}
section[data-testid="stFileUploaderDropzone"] {
    border: 1px dashed #CBD5E1 !important;
    border-radius: 12px;
}
[data-testid="stFileUploaderDropzone"] button {
    border: 1px solid #BFDBFE !important;
    border-radius: 8px !important;
    background: #EFF6FF !important;
    color: #1D4ED8 !important;
    box-shadow: none !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    border-color: #93C5FD !important;
    background: #DBEAFE !important;
    color: #1D4ED8 !important;
}
[data-testid="stFileUploaderDropzone"] button svg {
    color: #2563EB !important;
    stroke: #2563EB !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: var(--accent);
    background: #F8FBFF;
}
.stApp [data-testid="stFileUploader"] small,
.stApp [data-testid="stFileUploader"] span { color: var(--muted) !important; }
[data-testid="stUploadedFile"],
[data-testid="stFileUploaderFile"] {
    border: 1px solid #93C5FD !important;
    border-radius: 10px;
    background: #EFF6FF !important;
    color: #0F172A !important;
}
[data-testid="stUploadedFile"] *,
[data-testid="stFileUploaderFile"] * { color: #0F172A !important; }

[data-testid="stChatMessage"] {
    margin: 0.85rem 0;
    padding: 1.1rem 1.25rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--surface);
    box-shadow: 0 2px 4px rgba(15, 23, 42, 0.05);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    width: fit-content;
    max-width: 86%;
    margin-left: auto;
    margin-right: 0;
    border: 1px solid #7DD3FC;
    background: #E0F2FE;
    box-shadow: none;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    max-width: 94%;
    margin-left: 0;
    margin-right: auto;
    border: 1px solid #E2E8F0;
    background: var(--surface);
    box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.05);
}
[data-testid="stChatMessage"] p { color: var(--ink); }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p { color: #0369A1; }
[data-testid="chatAvatarIcon-user"],
[data-testid="chatAvatarIcon-assistant"] {
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    border-radius: 50%;
    color: #FFFFFF !important;
}
[data-testid="chatAvatarIcon-user"] { background: #0284C7 !important; }
[data-testid="chatAvatarIcon-assistant"] { background: #059669 !important; }
[data-testid="chatAvatarIcon-user"] svg,
[data-testid="chatAvatarIcon-assistant"] svg { color: #FFFFFF !important; stroke: #FFFFFF !important; }
[data-testid="stBottom"],
[data-testid="stAppScrollToBottomContainer"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div,
[data-testid="stBottomBlockContainer"] {
    background: #F8FAFC !important;
}
[data-testid="stChatInput"] {
    border: 0;
    border-radius: 24px;
    background: transparent;
    box-shadow: none;
}
[data-testid="stChatInput"] > div {
    padding: 6px 8px !important;
    border: 1px solid #94A3B8 !important;
    border-radius: 28px !important;
    background: #CBD5E1 !important;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.1) !important;
    transition: border-color 150ms ease, box-shadow 150ms ease;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #93C5FD !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14) !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: transparent;
    box-shadow: none;
}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] [contenteditable="true"] {
    border: 1px solid #CBD5E1 !important;
    border-radius: 24px !important;
    background: #FFFFFF !important;
    color: #0F172A !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 16px !important;
    line-height: 1.5 !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #94A3B8 !important; }
[data-testid="stChatInput"]:focus-within textarea,
[data-testid="stChatInput"]:focus-within [contenteditable="true"] {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
}
[data-testid="stChatInput"] button {
    border: 0 !important;
    border-radius: 50% !important;
    background: #2563EB !important;
    color: #FFFFFF !important;
}
[data-testid="stChatInput"] button svg { color: #FFFFFF !important; stroke: #FFFFFF !important; }
[data-testid="stStatusWidget"] {
    border: 1px solid #BFDBFE;
    border-radius: 10px;
    background: #F8FBFF;
    color: var(--ink);
}
[data-testid="stAlert"] { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──
for key, default in [("messages", []), ("retriever", None), ("indexed", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helper utilities ──
def extract_youtube_id(url: str) -> str | None:
    import re
    for p in [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})"]:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def load_pptx(file_bytes: bytes) -> str:
    prs = PptxPresentation(io.BytesIO(file_bytes))
    return "\n".join(shape.text_frame.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame)

def load_youtube_transcript(url: str) -> str:
    vid_id = extract_youtube_id(url)
    if not vid_id: raise ValueError(f"Could not extract video ID from: {url}")
    transcript = YouTubeTranscriptApi().fetch(vid_id)
    return " ".join(snippet.text for snippet in transcript)

def load_pdf(file_path: str) -> List[Document]:
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    return [Document(page_content=page.extract_text() or "", metadata={"source": file_path}) for page in reader.pages]

def load_csv(file_path: str) -> List[Document]:
    with open(file_path, newline="", encoding="utf-8-sig") as file:
        rows = [", ".join(f"{key}: {value}" for key, value in row.items()) for row in csv.DictReader(file)]
    return [Document(page_content=row, metadata={"source": file_path}) for row in rows]

class _HTMLTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data: str):
        if data.strip():
            self.text.append(data.strip())

def load_web_page(url: str) -> List[Document]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DocumentRetriever/1.0)"})
    with urlopen(request, timeout=20) as response:
        parser = _HTMLTextParser()
        parser.feed(response.read().decode("utf-8", errors="replace"))
    return [Document(page_content=" ".join(parser.text), metadata={"source": url})]

class CharacterTextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: List[Document]) -> List[Document]:
        chunks = []
        step = self.chunk_size - self.chunk_overlap
        for document in documents:
            text = document.page_content
            for start in range(0, len(text), step):
                content = text[start:start + self.chunk_size]
                if content.strip():
                    chunks.append(Document(page_content=content, metadata=document.metadata))
        return chunks

class TfidfRetriever:
    def __init__(self, documents: List[Document], top_k: int = 3):
        self.documents = documents
        self.top_k = top_k
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.document_vectors = self.vectorizer.fit_transform(document.page_content for document in documents)

    def invoke(self, query: str) -> List[Document]:
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.document_vectors).ravel()
        best_indexes = scores.argsort()[::-1][:self.top_k]
        return [self.documents[index] for index in best_indexes]

# ── Ingestion pipeline ──
def ingest_all(uploaded_files, web_url: str, yt_url: str):
    splitter = CharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    all_docs: List[Document] = []
    source_errors: List[str] = []

    for uf in uploaded_files:
        suffix = os.path.splitext(uf.name)[-1].lower()
        raw = uf.read()
        if suffix == ".pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            all_docs.extend(splitter.split_documents(load_pdf(tmp_path)))
            os.unlink(tmp_path)
        elif suffix == ".csv":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            all_docs.extend(splitter.split_documents(load_csv(tmp_path)))
            os.unlink(tmp_path)
        elif suffix in (".ppt", ".pptx"):
            all_docs.extend(splitter.split_documents([Document(page_content=load_pptx(raw), metadata={"source": uf.name})]))

    if web_url.strip():
        try:
            all_docs.extend(splitter.split_documents(load_web_page(web_url.strip())))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            source_errors.append(f"Web URL was skipped: {exc}")
    if yt_url.strip():
        try:
            transcript = load_youtube_transcript(yt_url.strip())
            all_docs.extend(splitter.split_documents([Document(page_content=transcript, metadata={"source": yt_url.strip()})]))
        except Exception as exc:
            source_errors.append(f"YouTube URL was skipped: {exc}")

    if not all_docs:
        raise ValueError("No documents were loaded. Please provide at least one source.")

    return TfidfRetriever(all_docs, top_k=3), len(all_docs), source_errors

# ── Graph Definitions ──
class GraphState(TypedDict):
    question: str
    documents: List[Document]
    eval_result: str
    generation: str

class RelevanceScore(BaseModel):
    binary_score: Literal["correct", "ambiguous", "incorrect"] = Field(..., description="correct = direct/complete info; ambiguous = partial info; incorrect = off-topic.")

def get_groq_model(api_key: str) -> str:
    configured_model = os.getenv(PROVIDERS["groq"]["model_env"], "").strip()
    if configured_model:
        return configured_model

    request = Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            available = {item["id"] for item in json.load(response).get("data", [])}
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError("Groq rejected this API key. Generate a new key and enter it in the sidebar.") from exc
        raise RuntimeError(f"Groq model lookup failed with HTTP {exc.code}.") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Groq to discover available models: {exc.reason}") from exc

    preferred = [
        "llama-4-scout-17b-16e-instruct",
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-20b",
        "qwen/qwen3-32b",
    ]
    for model in preferred:
        if model in available:
            return model
    if available:
        return sorted(available)[0]
    raise RuntimeError("Groq returned no usable models for this API key.")

def create_provider_model(api_key: str, model: str):
    if PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, temperature=0, groq_api_key=api_key)
    if PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0, api_key=api_key)
    if PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, temperature=0, google_api_key=api_key)
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=model, temperature=0, anthropic_api_key=api_key)

def make_graph(retriever, status_container=None):
    provider = PROVIDERS[PROVIDER]
    api_keys = get_api_keys(st.session_state.get(f"{PROVIDER}_api_key", ""))
    if not api_keys:
        raise RuntimeError(f"No {provider['label']} API key configured. Enter a key in the sidebar or set {provider['key_env']} and restart Streamlit.")

    model = get_groq_model(api_keys[0]) if PROVIDER == "groq" else (
        os.getenv(provider["model_env"], "").strip() or provider["default_model"]
    )
    base_llms = [create_provider_model(key, model) for key in api_keys]
    generator_llm = base_llms[0].with_fallbacks(base_llms[1:])
    eval_llms = [llm.with_structured_output(RelevanceScore) for llm in base_llms]
    evaluator_llm = eval_llms[0].with_fallbacks(eval_llms[1:])

    evaluator_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert relevance grader. Given context and question, decide if context is: 'correct' (complete info), 'ambiguous' (partial info), or 'incorrect' (off-topic). Return ONLY the structured score."),
        ("human", "User question: {question}\n\nRetrieved context:\n{context}")
    ])
    evaluator_chain = evaluator_prompt | evaluator_llm

    generator_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Answer the question using ONLY the provided context. Be concise, well-structured, and cite key facts from the context. If the context is insufficient, say so honestly."),
        ("human", "Context:\n{context}\n\nQuestion: {question}")
    ])
    generator_chain = generator_prompt | generator_llm

    def retrieve_node(state: GraphState) -> GraphState:
        if status_container: status_container.update(label="🔍 **Step 1 — Retrieving documents…**", state="running")
        return {**state, "documents": retriever.invoke(state["question"])}

    def evaluate_node(state: GraphState) -> GraphState:
        if status_container: status_container.update(label="🧠 **Step 2 — Evaluating relevance…**", state="running")
        ctx = "\n\n".join(d.page_content for d in state["documents"])
        score: RelevanceScore = evaluator_chain.invoke({"question": state["question"], "context": ctx})
        return {**state, "eval_result": score.binary_score}

    def web_search_node(state: GraphState) -> GraphState:
        if status_container: status_container.update(label="🌐 **Step 3 — Web search triggered (fallback)…**", state="running")
        search_results = DDGS().text(state["question"], max_results=5)
        search_content = "\n\n".join(
            "\n".join(
                f"{label}: {result[key]}"
                for label, key in (("Title", "title"), ("URL", "href"), ("Snippet", "body"))
                if result.get(key)
            )
            for result in search_results
        ) or "No web search results were returned."
        web_doc = Document(page_content=search_content, metadata={"source": "DuckDuckGo"})
        return {**state, "documents": [web_doc] if state["eval_result"] == "incorrect" else state["documents"] + [web_doc]}

    def response_text(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_blocks = []
            for block in content:
                if isinstance(block, str):
                    text_blocks.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    text_blocks.append(block["text"])
                else:
                    text = getattr(block, "text", None)
                    if isinstance(text, str):
                        text_blocks.append(text)
            return "\n".join(text_blocks)
        return ""

    def generate_node(state: GraphState) -> GraphState:
        if status_container: status_container.update(label=f"✍️ **Step {'3' if state['eval_result']=='correct' else '4'} — Generating answer…**", state="running")
        ctx = "\n\n".join(d.page_content for d in state["documents"])
        answer = generator_chain.invoke({"question": state["question"], "context": ctx})
        return {**state, "generation": response_text(answer.content)}

    workflow = StateGraph(GraphState)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("generate", generate_node)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "evaluate")
    workflow.add_conditional_edges("evaluate", lambda state: "generate" if state["eval_result"] == "correct" else "web_search", {"generate": "generate", "web_search": "web_search"})
    workflow.add_edge("web_search", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()

# ── Sidebar UI ──
with st.sidebar:
    st.markdown('<div class="rail-eyebrow">SOURCE LIBRARY</div>', unsafe_allow_html=True)
    st.title("Sources")
    st.markdown('<div class="rail-intro">Build a focused collection for this conversation.</div>', unsafe_allow_html=True)
    st.markdown('<div class="rail-section-label">Provider access</div>', unsafe_allow_html=True)

    st.text_input(
        f"{PROVIDERS[PROVIDER]['label']} API key",
        type="password",
        key=f"{PROVIDER}_api_key",
        help="Used only for this Streamlit session and not saved to source code.",
    )
    st.markdown('<div class="rail-key-note">Session-only key</div>', unsafe_allow_html=True)
    st.markdown('<div class="rail-section-label">Add material</div>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("Files", type=["pdf", "pptx", "ppt", "csv"], accept_multiple_files=True)
    web_url = st.text_input("Web page", placeholder="https://example.com/article")
    yt_url = st.text_input("YouTube video", placeholder="https://www.youtube.com/watch?v=...")
    
    if st.button("Index sources", use_container_width=True):
        if not uploaded_files and not web_url.strip() and not yt_url.strip():
            st.error("Please provide at least one document or URL.")
        else:
            with st.spinner("Indexing documents…"):
                try:
                    retriever, n_chunks, source_errors = ingest_all(uploaded_files, web_url, yt_url)
                    st.session_state["retriever"] = retriever
                    st.session_state["indexed"] = True
                    st.success(f"✅ Indexed **{n_chunks}** chunks successfully!")
                    for source_error in source_errors:
                        st.warning(source_error)
                except Exception as exc:
                    st.error(f"Indexing failed: {exc}")

    if st.session_state["indexed"]:
        st.success("Source library is ready.")
    else:
        st.info("No sources indexed yet.")

# ── Main UI ──
chunk_count = len(st.session_state["retriever"].documents) if st.session_state["retriever"] else 0
library_status = "Ready" if st.session_state["indexed"] else "Empty"
st.markdown(f"""
<header class="workspace-head">
    <div>
        <div class="workspace-eyebrow">RESEARCH WORKSPACE <span>/</span> {PROVIDERS[PROVIDER]['label'].upper()}</div>
        <h1 class="workspace-title">Source Desk</h1>
        <p class="workspace-subtitle">A focused workspace for questions grounded in your sources.</p>
    </div>
    <div class="workspace-status">
        <span class="status-light"></span>
        <div><span class="workspace-status-label">LIBRARY</span><strong>{library_status}</strong></div>
        <div class="status-count"><strong>{chunk_count}</strong>passages</div>
    </div>
</header>
""", unsafe_allow_html=True)

if not st.session_state["messages"]:
    st.markdown("""
    <section class="conversation-empty">
        <span class="empty-index">01</span>
        <div>
            <p class="empty-kicker">CONVERSATION</p>
            <h2>A clear space for your next question.</h2>
            <p>Questions and grounded answers will collect here.</p>
        </div>
    </section>
    """, unsafe_allow_html=True)

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_question = st.chat_input("Ask a question about your documents…")

if user_question:
    if not st.session_state["indexed"] or st.session_state["retriever"] is None:
        st.warning("⚠️ Please index at least one document or URL using the sidebar.")
        st.stop()

    st.session_state["messages"].append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.status("Processing your query…", expanded=True) as status:
            try:
                graph = make_graph(st.session_state["retriever"], status)
                final_state = graph.invoke({"question": user_question, "documents": [], "eval_result": "", "generation": ""})
            except Exception as e:
                status.update(label="❌ Error processing query", state="error")
                st.error(f"Pipeline failed: {e}")
                st.stop()
            
            eval_result = final_state.get("eval_result", "unknown").upper()
            badge_map = {
                "CORRECT": ("✅", "#38bdf8", "Documents were **relevant** — used directly."),
                "AMBIGUOUS": ("⚠️", "#f59e0b", "Documents were **partially relevant** — web search combined."),
                "INCORRECT": ("❌", "#ef4444", "Documents were **irrelevant** — replaced by web search."),
            }
            icon, color, note = badge_map.get(eval_result, ("❓", "#6b7280", f"Evaluation result: {eval_result}"))

            st.markdown(f"**Evaluator decision:** {icon} <span style='color:{color};font-weight:bold'>{eval_result}</span>", unsafe_allow_html=True)
            st.caption(note)

            status.update(label="✨ Analysis complete!", state="complete", expanded=False)

        answer = final_state.get("generation", "_No answer generated._")
        st.markdown(answer)
    st.session_state["messages"].append({"role": "assistant", "content": answer})
