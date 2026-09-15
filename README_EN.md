# InsightEngine - AI Cross-Channel Progressive Insight Extractor

[English Documentation](README_EN.md) | [中文文档](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![LLM: Multi_Provider](https://img.shields.io/badge/LLM-Multi--Provider--Failover-green.svg)](https://platform.openai.com/)

**InsightEngine** is an overarching AI-driven intellectual synthesis engine designed for computer architecture researchers and system engineers.
It aggregates passive information streams from three disparate pipelines:
1. **Academic Paper Alerts** (arXiv / Google Scholar / Technical Mail)
2. **Personal Thoughts & Article Bookmarks** (Obsidian Vault inbox / Quick Memos)
3. **Social Dynamics** (Zhihu expert timelines & high-value discussions)

By instilling **core computer architecture research philosophies and design checklists**, it conducts **multi-source progressive thinking and cross-pollination**. Adhering strictly to a **"high bar, zero noise"** principle, it delivers notifications directly to your phone via Enterprise WeChat (Agent 1000005) only when a truly profound, paradigm-shifting insight is distilled (depth score $\ge 80$), and automatically appends it to your Obsidian Vault.

---

## ✨ Key Features

- 🧠 **Cross-Source Progressive Thinking & Cross-Pollination**:
  - Breaks information silos by cross-referencing top-tier papers, industry discussions, and personal notes.
  - E.g., synthesizes a CXL near-memory paper with a PIM industrial bottleneck discussion and personal notes on PagedAttention hardware MMUs to propose novel architectural hypotheses.
- 🎯 **Four Classical Insight Modalities**:
  - **Pattern A [Sharp Question]**: Formulates critical research questions exploring boundaries (e.g., *Under identical semantic output, can dedicated ASIC logic pre-form address streams at lower resource overheads to improve DRAM service efficiency?*).
  - **Pattern B [First-Principle Realization]**: Explores fundamentals, such as Computation-for-Bandwidth (using a tiny 2% on-chip ASIC decoder to bypass off-chip bandwidth walls), and black-box vs. white-box modeling.
  - **Pattern C [Paradigm Shift]**: Discovers research frontiers emerging as classic assumptions collapse (dense static GEMM grids, flat SRAM-DRAM hierarchies, 2D planar silicon).
  - **Pattern D [Root-Cause "Why"]**: Pierces through superficial facades to reveal fundamental physical truths (e.g., *AXI/CHI are just apples; the mutual information of metadata and payload is universal gravitation*).
- 🛡️ **Dual-LLM Failover & Hot-Switching (High Availability)**:
  - Built-in Primary and Secondary automatic failover. Seamlessly falls back to the secondary provider upon timeout or error.
  - Hot-switch providers on the fly in WeChat via `/llm secondary` or update keys with `/setkey <Key>`.
- 🍪 **Crawler Health Detection & In-Chat Cookie Hot-Reloading**:
  - Proactively alerts WeChat when social crawler credentials expire.
  - Update Zhihu cookies directly by replying `/cookie <new_cookie>` in WeChat without SSHing into the server.
- 📝 **Automated Obsidian Vault Archiving**:
  - Formats accepted insights into Obsidian Callout markdown notes, automatically appended to `00-Inbox/WeChat_Insights.md`.

---

## 🏗️ Architecture

```
[ Stream 1: Papers & Alerts ]     [ Stream 2: Notes & Bookmarks ]     [ Stream 3: Tech Discussions ]
      (mail_assist.db)                   (inbox.db)                         (social_radar.db)
             │                                   │                                  │
             └───────────────────────────────────┼──────────────────────────────────┘
                                                 ▼
                        ┌────────────────────────────────────────┐
                        │ 1. Unified Knowledge Hub               │
                        │    - Extracts incremental 48-72h data  │
                        │    - Standardizes SourceKnowledgeItem  │
                        └────────────────────────┬───────────────┘
                                                 ▼
                        ┌────────────────────────────────────────┐
                        │ 2. Progressive Reflection Agent        │
                        │    - Ingests Architecture Philosophy   │
                        │    - Dual-LLM Failover (Gemini / DS)   │
                        │    - Formulates 4 Insight Patterns     │
                        └────────────────────────┬───────────────┘
                                                 ▼
                        ┌────────────────────────────────────────┐
                        │ 3. High Bar Filter (Zero Noise)        │
                        │    - Score ≥ 80 to pass                │
                        │    - Strict silence otherwise          │
                        └────────────────────────┬───────────────┘
                                                 ▼
                        ┌────────────────────────────────────────┐
                        │ 4. WeChat Push & Obsidian Archive      │
                        │    - Markdown + Personal Native Card   │
                        │    - Appends to Obsidian Vault         │
                        └────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/Bowen-0x00/insight-engine.git
cd insight-engine

pip install -r requirements.txt
```

### 2. Configure Credentials
```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` to specify WeCom credentials (Agent 1000005), primary and secondary LLM keys, and database paths.

### 3. Run & Verify
```bash
# 1. Test WeChat push channel
python run.py --test-wechat

# 2. Run a single cross-channel synthesis
python run.py --once

# 3. Start 24/7 continuous daemon (polls every 6 hours)
python run.py
```

---

## 💬 WeChat Command Cheatsheet

Send the following commands directly inside the WeChat conversation:

| Command | Description | Example |
| :--- | :--- | :--- |
| **`/insight`** | Immediately triggers a cross-channel synthesis | `/insight` |
| **`/status`** | Checks health of databases and LLM channels | `/status` |
| **`/llm <name>`** | Switches active LLM provider (`primary` / `secondary`) | `/llm secondary` |
| **`/setkey <Key>`**| Updates the active provider's API key | `/setkey sk-xxx` |
| **`/testllm`** | Tests LLM connectivity and latency | `/testllm` |
| **`/cookie <Cookie>`**| Hot-updates Zhihu crawler cookies from WeChat | `/cookie _xsrf=...` |
| **`/score <N>`** | Modifies the insight threshold (default 80) | `/score 85` |
| **`/help`** | Displays command help menu | `/help` |

---

## 📂 Repository Structure

```
insight_extractor/
├── config/
│   ├── config.example.yaml          # Configuration template
│   └── architecture_philosophy.yaml # Research philosophy & design checklist
├── engine/
│   ├── knowledge_hub.py             # Cross-database knowledge aggregator
│   ├── insight_agent.py             # Progressive thinking & insight extractor
│   ├── notifier.py                  # Dual-channel WeChat notifier
│   ├── command_receiver.py          # In-chat interactive controller
│   ├── storage.py                   # SQLite insight archive & deduplication
│   └── service.py                   # Orchestration service & command listener
├── deploy/
│   └── insight_extractor.service    # Linux Systemd unit file
├── tests/
│   └── test_insight.py              # Automated test suite
├── run.py                           # CLI entrypoint
├── sync_to_aliyun.py                # Local to Aliyun sync script
├── sync_to_aliyun.bat               # Windows batch script
├── requirements.txt                 # Dependencies
├── LICENSE                          # MIT License
└── README.md
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
