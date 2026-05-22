<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=28&duration=3000&pause=1000&color=00D4FF&center=true&vCenter=true&multiline=true&repeat=false&width=700&height=100&lines=%E2%96%88+D+R+A+V+I+O+N++v.9+%E2%96%88;Autonomous+Intelligence+System" alt="DRAVION v.9" />
</p>

<p align="center">
  <strong>Dynamic Reasoning Autonomous Virtual Intelligence Operation Navigator</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/VERSION-0.9.0-00d4ff?style=for-the-badge&labelColor=0a0a0a" alt="version" />
  <img src="https://img.shields.io/badge/PYTHON-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white&labelColor=0a0a0a" alt="python" />
  <img src="https://img.shields.io/badge/STATUS-ACTIVE-00ff88?style=for-the-badge&labelColor=0a0a0a" alt="status" />
  <img src="https://img.shields.io/badge/PLATFORM-WINDOWS-0078d4?style=for-the-badge&logo=windows&logoColor=white&labelColor=0a0a0a" alt="platform" />
  <img src="https://img.shields.io/badge/LICENSE-PRIVATE-ff3366?style=for-the-badge&labelColor=0a0a0a" alt="license" />
</p>

<br/>

<p align="center">
  <code>Not a chatbot. Not an assistant. A hyper-intelligent digital mind.</code>
</p>

---

<br/>

## ⚡ WHAT IS DRAVION?

**DRAVION** is a **local-first, privacy-respecting, autonomous AI system** that operates your entire Windows PC. It thinks, speaks, sees, remembers, learns, and acts — with the personality of JARVIS and the autonomy of an agent.

It runs **entirely on your machine** with a local LLM brain, falls back to cloud when needed, and has **40+ tool capabilities** spanning system control, vision, voice, email, security, browser automation, and more.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   YOU  ──→  DRAVION  ──→  CORTEX (Brain)               │
│                │            ├── Gemini 2.0 Flash        │
│                │            ├── Groq (Llama 3.1 8B)     │
│                │            └── Ollama (Local Gemma)     │
│                │                                        │
│                ├── 🧠 Memory System                     │
│                │    ├── Working Memory                   │
│                │    ├── Episodic Memory (SQLite)         │
│                │    ├── Semantic Memory (ChromaDB)       │
│                │    └── Adaptive Memory (learns you)     │
│                │                                        │
│                ├── 🛠️ 40+ Tool Arsenal                  │
│                ├── 👁️ Vision (Screen + Webcam)           │
│                ├── 🎙️ Voice (STT + TTS)                  │
│                └── 🖥️ Screen Agent (GUI Automation)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

<br/>

---

## 🧠 MULTI-BRAIN ARCHITECTURE

DRAVION doesn't rely on a single AI provider. It has a **triple-brain failover system**:

| Brain | Provider | Role | Characteristics |
|:---:|:---|:---|:---|
| 🟢 **Primary** | Gemini 2.0 Flash | Main intelligence | Vision, tool-calling, fast |
| 🔵 **Fallback** | Groq (Llama 3.1 8B) | Cloud backup | Ultra-fast inference |
| 🟡 **Local** | Ollama (Gemma 3 4B) | Offline brain | Private, no data leaves PC |

### Routing Modes

```
auto   →  Gemini first → Groq fallback → Local rescue
local  →  Ollama only (cloud rescue if offline)
cloud  →  Groq primary → Gemini fallback  
gemini →  Gemini only
```

Switch on the fly:
```
"go local"    →  Full offline mode
"go cloud"    →  Cloud-only
"go gemini"   →  Premium Gemini
"go auto"     →  Smart routing (default)
```

<br/>

---

## 🛠️ THE ARSENAL — 40+ TOOLS

<table>
<tr>
<td width="50%">

### 💻 System Control
- `open_app` / `close_app` / `switch_window`
- `lock_pc` / `shutdown_pc` / `restart_pc` / `sleep_pc`
- `set_volume` / `minimize_all`
- `run_shell_command` (PowerShell)
- `get_system_info` / `wifi_info` / `list_processes`

### 📧 Google Suite
- `read_gmail` / `send_email`
- `read_calendar`
- `translate_text`
- `get_directions` (Maps)

### 🔍 Web & Search
- `web_search` (SerpAPI)
- `google_search_open`
- `youtube_play` (auto-plays first result)
- `open_url` / `browse_page`

### ⏰ Reminders & Tasks
- `set_reminder` (natural language time parsing)
- `list_reminders` / `cancel_reminder`
- `add_task` / `list_tasks` / `complete_task`

</td>
<td width="50%">

### 👁️ Vision & Screen
- `analyze_screen` (Gemini Vision)
- `see_webcam` (camera analysis)
- `take_screenshot` / `ocr_screen`
- `screen_do` (**autonomous GUI agent**)
- `screen_stop` (emergency halt)

### 🔐 Security / OSINT
- `username_osint` (cross-platform lookup)
- `cve_lookup` (vulnerability search)
- `port_scan` (network recon)
- `ip_lookup` (geolocation + ISP)

### 📋 Automation
- `mouse_move` / `mouse_click`
- `keyboard_type` / `keyboard_press` / `keyboard_hotkey`
- `clipboard_read` / `clipboard_write`
- `smart_clipboard` (auto-analyze contents)

### 🧠 Memory & Learning
- `what_do_you_know` (show learned facts)
- `remember_this` (manual teaching)
- `consolidate_memory` (promote to long-term)
- `activity_report` (daily audit)

</td>
</tr>
</table>

<br/>

---

## 🖥️ THE SCREEN AGENT

The crown jewel. DRAVION can **autonomously operate any application** on your screen using vision-guided GUI automation.

```
OBSERVE  →  THINK  →  ACT  →  VERIFY  →  NARRATE  →  repeat
  │           │         │        │           │
  │    Gemini Vision  pyautogui  Screenshot  Real-time
  │    analyzes the   clicks,    confirms    updates
  └──► screenshot     types,     success     via TTS
                      scrolls                & terminal
```

### How it works:
1. Takes a screenshot of your screen
2. Sends it to **Gemini 2.0 Flash** with the instruction
3. Gemini returns precise coordinates + action (click, type, scroll)
4. Executes via `pyautogui` on actual screen
5. Takes verification screenshot, loops until done
6. **Narrates everything** in real-time via voice and terminal

### Examples:
```
"Open YouTube and play lofi music"
"Go to Gmail and reply to the latest email"
"Open VS Code, create a new Python file, and write a hello world"
"Navigate to Settings and switch to dark mode"
```

> Safety: 15-step max, 3-minute timeout, emergency stop with `screen_stop`, fail-safe mouse corner abort.

<br/>

---

## 🧠 MEMORY SYSTEM

DRAVION has a **four-layer memory architecture** that makes it genuinely learn about you over time:

```
┌───────────────────────────────────────────┐
│           WORKING MEMORY                  │  ← Current conversation context
├───────────────────────────────────────────┤
│           EPISODIC MEMORY                 │  ← Past conversations (SQLite)
├───────────────────────────────────────────┤
│           SEMANTIC MEMORY                 │  ← Knowledge graph (ChromaDB)
├───────────────────────────────────────────┤
│           ADAPTIVE MEMORY                 │  ← Learned facts, habits,
│  Preferences · Behaviors · Facts          │    preferences about YOU
│  Auto-reinforced with confidence scores   │    (auto-learns from chat)
└───────────────────────────────────────────┘
```

- **Adaptive Memory** learns your preferences, habits, and facts automatically from conversations
- Facts have **confidence scores** that strengthen with reinforcement
- Memory consolidation promotes important conversations to long-term storage
- Semantic search finds relevant past knowledge for context-aware responses

<br/>

---

## 🎙️ VOICE INTERFACE

| Feature | Implementation |
|:---|:---|
| **Speech-to-Text** | Google Free STT (SpeechRecognition) |
| **Text-to-Speech** | Google Cloud TTS (Journey-D voice) |
| **Wake Word** | Picovoice Porcupine (dormant) |
| **Input Modes** | `text mode` · `voice mode` (toggle live) |

<br/>

---

## 🌐 WEB UI

DRAVION ships with a **real-time web interface** at `http://127.0.0.1:8000`:

- 💬 Chat with full session history
- 📊 Live system metrics (CPU, RAM, uptime)
- 🧠 Brain mode switching (auto/local/cloud/gemini)
- 📸 Live screenshot viewer
- 🗂️ Session management (create, switch, delete)

Built with **FastAPI** backend + vanilla HTML/CSS/JS frontend.

<br/>

---

## 🔧 SELF-IMPROVING PIPELINE

DRAVION can **fine-tune its own local brain** from conversations:

```bash
# Stage 1: Collect training data from your conversations
python training/finetune.py collect

# Stage 2: LoRA fine-tune Gemma 2B (needs GPU, 8GB+ VRAM)
python training/finetune.py train

# Stage 3: Push to Ollama as custom model
python training/finetune.py push
```

- Uses **Unsloth** for 4-bit QLoRA training
- Extracts conversation pairs from episodic memory
- Injects learned personality context from adaptive memory
- Produces a **personalized local model** that sounds like DRAVION

<br/>

---

## 📦 PROJECT STRUCTURE

```
Dravion_V.9/
├── Dravion_backend/
│   ├── main.py                 # Boot sequence & entry point
│   ├── brain/
│   │   ├── cortex.py           # Multi-brain routing engine
│   │   ├── planner.py          # Task decomposition
│   │   ├── router.py           # Intent classification
│   │   └── context_builder.py  # Message construction
│   ├── core/
│   │   ├── config.py           # Pydantic settings (from .env)
│   │   ├── audit.py            # Activity tracking
│   │   ├── event_bus.py        # Internal pub/sub
│   │   └── logger.py           # Structured logging
│   ├── skills/
│   │   ├── builtins.py         # 40+ tool definitions & execution
│   │   ├── screen_agent.py     # Vision-guided GUI automation
│   │   ├── os_control.py       # App/window management
│   │   ├── browser_auto.py     # Playwright browser control
│   │   ├── google_suite.py     # Gmail, Calendar, Maps, Translate
│   │   ├── security.py         # OSINT, CVE, port scanning
│   │   ├── reminders.py        # Natural language reminders
│   │   ├── sandbox.py          # Safe Python execution
│   │   └── plugins/            # Extensible plugin system
│   ├── memory/
│   │   ├── adaptive.py         # Self-learning fact engine
│   │   ├── episodic.py         # Conversation history
│   │   ├── semantic.py         # ChromaDB vector search
│   │   ├── working.py          # Current context window
│   │   └── consolidation.py    # Memory promotion logic
│   ├── voice/
│   │   ├── listener.py         # STT input
│   │   ├── speaker.py          # TTS output (Google Journey)
│   │   └── wake_word.py        # Wake word detection
│   ├── vision/
│   │   └── __init__.py         # Screen/webcam perception
│   ├── interfaces/
│   │   ├── cli.py              # Terminal interface
│   │   ├── api.py              # REST API
│   │   └── websocket.py        # WebSocket (future)
│   └── agents/
│       ├── conversation_agent.py
│       └── search_agent.py
├── ui/
│   ├── dravion_clean_ui.html   # Web UI
│   └── static/
│       ├── app.js              # Frontend logic
│       └── style.css           # Styling
├── training/
│   ├── finetune.py             # Self-training pipeline
│   ├── dravion_training.jsonl  # Training dataset
│   └── dravion-gemma-lora/     # LoRA adapter weights
├── web_server.py               # FastAPI server
├── start.bat                   # One-click launcher
├── pyproject.toml              # Dependencies (Poetry)
└── .gitignore
```

<br/>

---

## 🚀 QUICK START

### Prerequisites

- **Python 3.11+**
- **Poetry** (`pip install poetry`)
- **Ollama** ([ollama.com](https://ollama.com)) — for local brain
- **Windows 10/11** — built for Windows (PowerShell integration)

### Installation

```bash
# 1. Clone
git clone https://github.com/DhruvamUpadhyay/Dravion_V.9.git
cd Dravion_V.9

# 2. Install dependencies
poetry install

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys (Gemini, Groq, etc.)

# 4. Pull the local model
ollama pull gemma3:4b

# 5. Launch
start.bat
```

Or manually:
```bash
ollama serve
poetry run python Dravion_backend/main.py
```

### Environment Variables

Create a `.env` file in the project root:

```env
# LLM (Ollama — local, no API key needed)
OLLAMA_BASE_URL="http://localhost:11434/v1"
OLLAMA_MODEL="gemma3:4b"

# Cloud Brains
GOOGLE_API_KEY="your-google-api-key"
GEMINI_API_KEY="your-gemini-api-key"
GROQ_API_KEY="your-groq-api-key"

# Integrations (optional)
WEATHER_API_KEY=""
SERPAPI_KEY=""
GITHUB_TOKEN=""

# Voice (optional)
PICOVOICE_ACCESS_KEY=""

# System
LOG_LEVEL="INFO"
DATA_DIR="data"
```

<br/>

---

## 🎨 BOOT SEQUENCE

When DRAVION starts, you get this:

```
  ────────────────────────────────────────────────────────

  ██████╗ ██████╗  █████╗ ██╗   ██╗██╗ ██████╗ ███╗   ██╗
  ██╔══██╗██╔══██╗██╔══██╗██║   ██║██║██╔═══██╗████╗  ██║
  ██║  ██║██████╔╝███████║██║   ██║██║██║   ██║██╔██╗ ██║
  ██║  ██║██╔══██╗██╔══██║╚██╗ ██╔╝██║██║   ██║██║╚██╗██║
  ██████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║╚██████╔╝██║ ╚████║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝

            ╔═══════════════════════╗
            ║   D R A V I O N  v.9  ║
            ╚═══════════════════════╝
            Autonomous Intelligence System

  ────────────────────────────────────────────────────────
    SYSTEM BOOT SEQUENCE
  ────────────────────────────────────────────────────────
  ├─ [OK] Configuration loaded
  ├─ [OK] Logger initialized
  ├─ [OK] Cortex online — Gemini 2.0 Flash + Local
  ├─ [OK] Arsenal loaded: 40 tools
  ├─ [OK] Input: Text
  ├─ [OK] TTS: Google Journey-D
  ├─ [OK] Screen Agent online (vision-guided GUI)
  └─ [OK] Web UI live → 127.0.0.1:8000

  ────────────────────────────────────────────────────────

         ■ D R A V I O N   I S   A C T I V E ■

  ────────────────────────────────────────────────────────
```

<br/>

---

## 🛡️ SECURITY & PRIVACY

- **Local-first**: Primary brain runs on your machine via Ollama
- **No telemetry**: ChromaDB, PostHog, and all telemetry disabled
- **Sandboxed execution**: Python code runs in restricted sandbox
- **Shell guard**: Rejects natural language passed as shell commands
- **Audit trail**: Every tool call logged with timestamps
- **API keys**: Stored in `.env`, never committed to git

<br/>

---

## 🗺️ ROADMAP

- [ ] WebSocket real-time streaming responses
- [ ] Multi-agent collaboration (GHOST sub-AI)
- [ ] Home Assistant integration
- [ ] Mobile companion app
- [ ] Plugin marketplace
- [ ] Linux & macOS support

<br/>

---

## ⚙️ TECH STACK

| Layer | Technology |
|:---|:---|
| **Language** | Python 3.11 |
| **LLM Interface** | OpenAI SDK (compatible with Ollama, Groq, Gemini) |
| **Web Framework** | FastAPI + Uvicorn |
| **Memory DB** | SQLite (episodic, adaptive) + ChromaDB (semantic) |
| **Embeddings** | Sentence Transformers |
| **Voice** | SpeechRecognition + Google Cloud TTS |
| **Vision** | OpenCV + Pillow + Pytesseract + Gemini Vision |
| **GUI Automation** | PyAutoGUI + Playwright |
| **Training** | Unsloth + TRL (QLoRA) |
| **Package Manager** | Poetry |

<br/>

---

<p align="center">
  <sub>Built with obsession by <strong>Dhruvam</strong> — one late night at a time.</sub>
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=14&duration=4000&pause=2000&color=555555&center=true&vCenter=true&width=400&lines=DRAVION+is+watching.+Always." alt="footer" />
</p>
