# Turiya: Self-Evolving Neuro-Symbolic Swarm (SNS²F)

**Turiya** is a research-grade Cognitive Architecture that runs entirely on local hardware (CPU). Unlike standard LLM wrappers, Turiya is a **Stateful, Autonomous Entity** that builds its own world model, manages its own memory, and evolves over time.

![Status](https://img.shields.io/badge/Status-Operational-green)
![Architecture](https://img.shields.io/badge/Architecture-Neuro--Symbolic-blueviolet)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local-success)

## 🧠 The Architecture

Turiya rejects the "Black Box" approach of pure Deep Learning. Instead, it uses a **Meaning-First** architecture:

1.  **Perception (The Hunter):** An autonomous crawler that hunts for knowledge gaps on the web using `DuckDuckGo` and `BeautifulSoup`.
2.  **Memory (The Core):** A Hybrid Database (`SQLite`) combining:
    * **Vector Embeddings:** For semantic intuition.
    * **Knowledge Graph:** For precise logical deduction (Triples).
3.  **Reasoning (The Brain):** A Hybrid Engine combining:
    * **Symbolic Logic:** Uses `Spacy` for deterministic fact extraction.
    * **Neural Synthesis:** Uses `Phi-3 Mini` (via `llama.cpp`) for fluent communication.
    * **Tool Use:** Can write and execute Python code for math/logic.
4.  **Metacognition (The Soul):**
    * **Self-Model:** Aware of its own uptime, knowledge size, and capabilities.
    * **The Critic:** Self-corrects hallucinations before speaking.
    * **Sleep Cycle:** Prunes noise and generalizes concepts into higher-order abstractions.

## 🚀 Installation

Turiya requires **Python 3.10+** and a decent CPU. No GPU required.

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/Turiya.git](https://github.com/YOUR_USERNAME/Turiya.git)
    cd Turiya
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv .venv
    # Windows:
    .\.venv\Scripts\Activate.ps1
    # Mac/Linux:
    source .venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Language Engine:**
    ```bash
    python -m spacy download en_core_web_sm
    ```

5.  **First Run:**
    ```bash
    python main.py
    ```
    *Note: On the first run, Turiya will automatically download the Phi-3 GGUF model (~2.4GB). Please wait.*

## 🎮 Usage

### The Command Line Interface (CLI)
Run `python main.py` to enter the console.

* `/ask <question>` - Ask Turiya a question.
    * *Example:* `/ask Who is Alan Turing?`
    * *Example:* `/ask Calculate 50 * 50`
* `/start` - Wake up the Swarm. The Perception Agent will begin crawling the web to fill knowledge gaps.
* `/stop` - Pause the Swarm safely.
* `/sleep` - Trigger Memory Consolidation. The system prunes noise, merges duplicates, and forms new Concepts.
* `/trace` - View the step-by-step thought process of the last query.

### The Web Interface
Run `streamlit run app.py` for a modern chat interface.

### The Neural Dashboard
Run `streamlit run dashboard.py` to visualize the Knowledge Graph growing in real-time.

## 🧪 Cognitive Features

### 1. Autonomous Curiosity
If you ask Turiya about a topic it doesn't know, it won't hallucinate. It will say "I don't know," flag a **Knowledge Gap**, and immediately dispatch the Perception Agent to scrape Wikipedia and learn about it.

### 2. Meaning-First Logic
Turiya parses text into S-V-O triples (`Turing -> is -> Mathematician`). This allows it to perform multi-hop inference (`Turing -> Machine -> Computation`) that pure LLMs often struggle with.

### 3. Agentic Coding
Turiya detects math or logic problems, writes a Python script in a sandbox, executes it, and returns the exact result.

## 📂 Project Structure

* `sns2f_framework/`: Core engine code.
    * `agents/`: The autonomous workers (Reasoning, Perception, Learning).
    * `core/`: The nervous system (EventBus, LanguageEngine, GrammarLearner).
    * `memory/`: The Hybrid Database manager.
    * `reasoning/`: Higher-order thought (Inference, Generalizer, Critic).
    * `tools/`: Skill plugins (CodeExecutor).
* `data/`: Stores the SQLite DB and Models (Not synced to Git).

## 📜 License

MIT License. Built as a research prototype for Neuro-Symbolic AI.