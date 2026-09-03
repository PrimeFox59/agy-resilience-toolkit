# MEMORY.md — Durable Technical & Project Memory (Hermes Layer)

## 1. System & Environment Context
- **Operating System:** Windows / Linux / macOS.
- **Node Identifier:** [MC18 / DEV20 / VPS / Local].
- **Core CLI Tools:** `agy`, `codegraph`, `python`, `node`, `git`.

## 2. Core Operational Workflows & Policies

### A. Code Analysis: CodeGraph First (Init -> Sync -> Explore)
- Before analyzing codebase, run `codegraph init` and `codegraph sync`.
- Explore symbols via `codegraph explore <query>` for token efficiency.
- Prohibit dumping large files into context blindly.

### B. Memory Synchronization Across Tri-Node Cluster
- Keep `USER.md`, `MEMORY.md`, and `AGENTS.md` synchronized across all nodes.
- Run `powershell -ExecutionPolicy Bypass -File scripts\sync-once.ps1 -Action push` after updating memory.

## 3. Continuous Learning & Troubleshooting Log
*(AI autonomously appends persistent technical lessons, tricky bugs, and environment fixes here)*

- **[YYYY-MM-DD] System Initialized:** Configured persistent Hermes memory layer and auto-fallback engine.
