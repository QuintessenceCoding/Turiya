# Turiya: Self-Evolving Neuro-Symbolic Swarm (SNS²F)

### A Local, Autonomous Cognitive Architecture Inspired by Human Intelligence

![Status](https://img.shields.io/badge/Status-Operational-green)
![Architecture](https://img.shields.io/badge/Architecture-Neuro--Symbolic-blueviolet)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local-success)

## 🧠 Overview

**Turiya** is not a typical AI chatbot. It is a stateful, self-evolving cognitive system combining:

* **Symbolic Reasoning** (Knowledge Graphs, Logic)
* **Neural Understanding** (Embeddings + Phi-3 Mini)
* **Autonomous Learning** (Web Crawler + Curiosity Engine)
* **Cognitive Evolution** (Sleep, Abstraction, Hebbian Reinforcement)

Turiya learns continuously, forms its own world model, corrects contradictions, and evolves its internal knowledge structure — all running locally on your CPU.

This project demonstrates how to build an explainable, self-growing, and hardware-efficient intelligent system without relying on cloud APIs.

---

## ⚡ Highlights

### 🔍 Learning
* **Autonomous Web Crawling:** Automatically hunts for information to fill knowledge gaps.
* **Immune System:** Filters low-quality sources (ads, spam) to keep the knowledge base clean.
* **Continuous Ingestion:** Text $\to$ Embedding $\to$ Fact Extraction pipeline.

### 🧠 Reasoning
* **Deterministic Extraction:** Uses Spacy to extract Subject-Verb-Object triples.
* **Symbolic Inference:** Walks the Knowledge Graph to find hidden connections.
* **Code Execution:** Detects math/logic problems and writes Python code to solve them.
* **Neural Synthesis:** Uses `Phi-3 Mini` to generate fluent, grounded responses.

### 🧬 Cognitive Evolution
* **Hebbian Weighting:** Memories strengthen when used ("neurons that fire together, wire together").
* **Forgetting & Pruning:** Unused memories decay and are removed during sleep cycles.
* **Generalization:** Automatically clusters facts to create abstract Super-Concepts (e.g., "Carnivore").
* **Self-Modeling:** Turiya maintains a self-concept and knows its own stats.
* **Truth Arbitration:** A "Judge" module detects contradictions and resolves truth based on source confidence.

### 🔒 Privacy
* **100% Local:** No external API calls (OpenAI/Anthropic). No data leaves your machine.

---

## 🚀 Installation

**Requirements:** Python 3.10+ and a decent CPU. No GPU necessary.

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/Turiya.git](https://github.com/YOUR_USERNAME/Turiya.git)
    cd Turiya
    ```

2.  **Create a virtual environment**
    ```bash
    python -m venv .venv
    # Windows:
    .\.venv\Scripts\activate
    # Mac/Linux:
    source .venv/bin/activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install SpaCy language model**
    ```bash
    python -m spacy download en_core_web_sm
    ```

5.  **First Run**
    ```bash
    python main.py
    ```
    *Note: On first launch, Turiya automatically downloads the Phi-3 Mini GGUF model (~2.4GB).*

---

## 🎮 Usage

### Core Commands (CLI)

| Command | Description |
| :--- | :--- |
| `/ask <question>` | Ask Turiya anything. (Triggers Retrieval & Thinking) |
| `/start` | Activate autonomous crawling (Perception Agent). |
| `/stop` | Pause crawling safely (Finish current digestion). |
| `/set mode [mode]`| Change crawler safety (`strict`, `safe`, `open`). |
| `/sleep` | Trigger memory consolidation (Abstraction, Pruning). |
| `/trace` | Show step-by-step reasoning for the last query. |
| `/flush` | Clear the crawler frontier queue. |
| `/quit` | Exit the system. |

### Safety Modes
* **`strict`**: Wikipedia, .edu, .gov sites only. (High Trust).
* **`safe`**: Blocks social media & low-quality sources. (Balanced).
* **`open`**: Full internet crawling with basic blacklist protection. (Maximum Reach).

### Web Interfaces

**Chat Interface:**
```bash
streamlit run app.py
```
Knowledge Graph Dashboard:

```bash

streamlit run dashboard.py
```
### 🧠 Architecture
```bash
+-----------------------------+
|         Orchestrator        |
|        (EventBus)           |
+-----------------------------+
       |         |         |
       v         v         v
  Reasoning   Perception   Learning
    Agent       Agent        Agent
       |           |            |
       +---------- Memory ------+
                    |
              Sleep / Judge

```
**🐾 1. Perception Agent — The Hunter**
An autonomous, stateful web crawler.

Hunts for **Knowledge Gaps** identified by the Brain.

Manages a frontier queue and interest_queue.

Uses an **Immune System** to block ads, login walls, and binary files.

**💾 2. Memory Manager — The Hybrid Core**
**Vector Store (Neural Intuition):** Embeds every text chunk into 384-dimensional vectors for semantic search.

**Knowledge Graph (Symbolic Logic):** Stores facts as (Subject, Predicate, Object) triples for precise deduction.

**Hebbian Learning:** Facts gain weight when used; weak facts decay.

**🧠 3. Reasoning Agent — The Brain**
**Intent Detection:** Uses Regex + SpaCy to determine user intent.

**Planning:** Breaks complex queries ("Tell me about X") into sub-steps.

**Truth Arbitration:** The Judge compares new facts against old ones to resolve conflicts.

***Generation:*** Uses Phi-3 Mini to synthesize fluent answers rooted in retrieved facts.

**Tool Use:** Writes and executes Python code for math/logic problems.

### 🧬 4. Cognitive Evolution
**💤 Sleep Cycle**
When you run /sleep:

**Deduplication:** Merges identical facts.

**Forgetting:** Prunes noise and unused memories.

**Generalization:** Looks for patterns (e.g., items sharing properties) and creates abstract Super-Concepts.

**🔍 Contradiction Resolution**
When a new fact conflicts with an old one:

1. Check supporting evidence.

2. Ask Phi-3 to judge validity.

3. Keep the stronger fact or adjust confidence scores.

**🎯 Intrinsic Motivation (Curiosity)**
If the system is idle, it prioritizes learning about topics with:

Low connectivity (Lonely Nodes).

High uncertainty.

Low confidence scores.

### 📂 Project Structure
```bash

sns2f_framework/
│
├── agents/        # Reasoning, Perception, Learning Agents
├── core/          # EventBus, Language Engine, Trace Manager
├── memory/        # Hybrid Memory System (LTM/STM)
├── reasoning/     # Higher-order cognition (Judge, Generalizer, Planner)
├── skills/        # Agentic tool plugins
├── tools/         # Code execution sandbox
└── app.py         # Web UI
```
### ⚠️ Limitations
Even advanced systems have constraints:

1. Parser Bottleneck: SpaCy rules may miss complex or poetic sentence structures.

2. Latency: Crawling + Extraction + Synthesis takes time (10–30 seconds) on a local CPU.

3. Memory Cap: Database size is capped at 500MB (configurable) to prevent disk bloat.

4. Single Node: Runs on one machine; no distributed crawling.

### 🛣️ Future Work
 Neural Triple Extractor (Transformer-based parsing).

 Graph-based Reinforcement Learning for curiosity strategy.

 Speech I/O integration (Whisper/TTS).

 Distributed multi-node crawling.

### 🧘 Ethical & Safety Notice
Turiya autonomously crawls the public web. Please use responsibly.

Respect robots.txt (configurable).

Comply with local data laws.

Disclaimer: This project is a research prototype, not a commercial product.

### 📜 License
MIT License. Built as a research experiment in Neuro-Symbolic AI.