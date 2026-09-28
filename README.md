# 🔍 Multi-Format Information Retriever (Corrective RAG)

An advanced, production-grade retrieval framework built to parse, process, and query diverse document formats using **Corrective Retrieval-Augmented Generation (CRAG)** across multiple LLM backends.

---

## 💡 Importance of This Project

In traditional enterprise settings, knowledge is fragmented across multiple formats—PDF reports, Word documents, text logs, web pages, and CSVs. Standard LLMs suffer from context limits, hallucinations, and outdated information. 

This project solves critical information retrieval challenges by:
- **Eliminating Format Barriers**: Ingesting unstructured and structured files seamlessly without manual preprocessing.
- **Ensuring High Precision**: Using self-corrective retrieval mechanisms so the LLM receives only relevant context.
- **Reducing AI Hallucinations**: Grounding response generation strictly in retrieved document context and dynamic web searches.
- **Providing Multi-Provider Agnosticism**: Enabling seamless switching between OpenAI, Google Gemini, Anthropic, and Groq based on cost and privacy requirements.

---

## 🛠️ Deep Dive: Core Technologies

### 🦜🔗 LangChain
**What it is**: LangChain is an open-source framework designed to simplify the creation of applications using large language models (LLMs). It provides abstractions for document loaders, text splitters, vector stores, and chain orchestration.

**How it is used in this project**:
- Managing document loading pipelines (`PyPDFLoader`, `Docx2txtLoader`, `CSVLoader`, `TextLoader`).
- Chunking large texts using `RecursiveCharacterTextSplitter`.
- Constructing dynamic prompt templates and chaining retrieval logic with vector stores and LLM generators.

**Dependencies used**:
- `langchain`
- `langchain-community`
- `langchain-core`
- `langchain-text-splitters`

🔗 [LangChain Official Documentation](https://python.langchain.com/)

---

### 🤗 Hugging Face
**What it is**: Hugging Face is an open-source platform and community providing pre-trained deep learning models, datasets, and machine learning utilities, famous for its `transformers` and `sentence-transformers` libraries.

**How it is used in this project**:
- Generating high-dimensional vector embeddings locally using open-source models like `sentence-transformers/all-MiniLM-L6-v2`.
- Running embedding pipelines locally without incurring external API costs or data privacy overheads.

**Dependencies used**:
- `transformers`
- `sentence-transformers`
- `huggingface-hub`

🔗 [Hugging Face Official Documentation](https://huggingface.co/docs)

---

### 👑 Streamlit
**What it is**: Streamlit is a faster way to build and share data apps. It turns Python scripts into interactive web applications in minutes without requiring web development experience (HTML/CSS/JS).

**How it is used in this project**:
- Serving as the interactive user interface for file uploads, vector indexing status, prompt execution, and dynamic LLM provider selection.
- Rendering rich markdown responses, source document citations, and real-time execution logs.

**Dependencies used**:
- `streamlit`

🔗 [Streamlit Official Documentation](https://docs.streamlit.io/)

---

## 🧰 Complete Tech Stack Used

| Category | Technology / Library | Purpose |
| :--- | :--- | :--- |
| **Frontend / UI** | Streamlit | Web interface for multi-file uploading & interactive Q&A |
| **Orchestration** | LangChain | RAG pipeline, chain execution, prompt engineering |
| **Embeddings** | Hugging Face Sentence-Transformers | Local vector embeddings generation |
| **Vector Database** | FAISS / ChromaDB | Fast similarity search and dense vector storage |
| **LLM Backends** | OpenAI, Google Gemini, Anthropic, Groq | Generative response synthesis |
| **Document Loaders** | PyPDF, docx2txt, Pandas | Parsing PDF, DOCX, TXT, and CSV file structures |
| **Search Fallback** | Tavily / DuckDuckGo Search API | External web search augmentation for CRAG |

---

## 🧠 Not Just Standard RAG: This is Corrective RAG (CRAG)

### How CRAG Beats Standard RAG
Standard RAG blindly passes top-$k$ retrieved vector matches directly to the LLM. If the vector store returns low-quality or irrelevant chunks, standard RAG forces the LLM to hallucinate or generate inaccurate answers.

**Corrective RAG (CRAG)** fixes this by adding a **Retrieval Evaluator**:
1. **Evaluates Relevance**: A evaluator evaluates the confidence score of retrieved document chunks against the user query.
2. **Corrects & Triggers Fallback**:
   - **Correct**: If retrieved documents are highly relevant, it extracts key knowledge and passes it to the generator.
   - **Incorrect / Ambiguous**: If retrieved documents are insufficient or irrelevant, CRAG dynamically triggers an **external web search** (e.g., via Tavily or DuckDuckGo) to retrieve up-to-date, accurate knowledge.
3. **Refines Context**: Filters out noise before final response generation.

```mermaid
---
config:
  theme: base
  themeVariables:
    lineColor: "#0f172a"
    textColor: "#0f172a"
    edgeLabelBackground: "#ffffff"
    fontSize: "14px"
---
flowchart TB
    %% Standard RAG Flow %%
    subgraph Standard_RAG [" STANDARD RAG WORKFLOW "]
        direction LR
        A1["👤 User Query"] ==> B1["🔍 FAISS Retrieval"]
        B1 ==> C1["📄 Retrieved Documents"]
        C1 ==> D1["🤖 Direct LLM Generation"]
        D1 ==> E1["⚠️ Problem: Risk of Hallucination<br/>& Outdated Answers"]
    end

    %% CRAG Flow %%
    subgraph CRAG [" CORRECTIVE RAG (CRAG) WORKFLOW "]
        direction LR
        A2["👤 User Query"] ==> B2["🔍 FAISS Retrieval"]
        B2 ==> C2(("⚖️ Retrieval<br/>Evaluator"))
        
        C2 ==> Path1["🟢 Accurate"] ==> D2["Knowledge Refinement<br/>• Strip & Decompose<br/>• Filter & Recompose"]
        C2 ==> Path2["🟡 Ambiguous"] ==> E2["Knowledge Searching<br/>• Query Rewrite<br/>• Web Search Fallback"]
        C2 ==> Path3["🔴 Incorrect"] ==> E2
        
        D2 ==> F2["✅ Refined Context"]
        E2 ==> F2
        F2 ==> G2["🎯 High-Precision<br/>Generation"]
    end

    %% Force Equal Box Width Alignment %%
    E1 ~~~ G2

    %% Subgraph Box Backgrounds %%
    style Standard_RAG fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1
    style CRAG fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d

    %% Standard RAG Node Colors %%
    style A1 fill:#ffffff,stroke:#0f172a,stroke-width:1.5px,color:#0f172a
    style B1 fill:#ffffff,stroke:#0f172a,stroke-width:1.5px,color:#0f172a
    style C1 fill:#ffffff,stroke:#0f172a,stroke-width:1.5px,color:#0f172a
    style D1 fill:#ffffff,stroke:#0f172a,stroke-width:1.5px,color:#0f172a
    style E1 fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#9f1239

    %% CRAG Node & Decision Badge Colors %%
    style A2 fill:#ffffff,stroke:#0f172a,stroke-width:1.5px,color:#0f172a
    style B2 fill:#ffffff,stroke:#0f172a,stroke-width:1.5px,color:#0f172a
    style C2 fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    
    style Path1 fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d
    style Path2 fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    style Path3 fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#9f1239

    style D2 fill:#ffffff,stroke:#16a34a,stroke-width:2px,color:#14532d
    style E2 fill:#ffffff,stroke:#e11d48,stroke-width:2px,color:#9f1239
    style F2 fill:#ffffff,stroke:#059669,stroke-width:2px,color:#065f46
    style G2 fill:#dcfce7,stroke:#16a34a,stroke-width:2.5px,color:#14532d

    %% Explicit Arrow Visibility & Color Fixes %%
    linkStyle default stroke:#0f172a,stroke-width:2.5px,fill:none;
    linkStyle 0,1,2,3 stroke:#0284c7,stroke-width:2.5px;
    linkStyle 4,5 stroke:#0f172a,stroke-width:2.5px;
    linkStyle 6,7 stroke:#16a34a,stroke-width:2.5px;
    linkStyle 8,9,10 stroke:#e11d48,stroke-width:2.5px;
    linkStyle 11,12,13 stroke:#059669,stroke-width:2.5px;
