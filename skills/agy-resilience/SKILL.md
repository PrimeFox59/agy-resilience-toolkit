---
name: agy-resilience
description: >-
  Provides Google Antigravity CLI (agy) resilience tools: multi-account Google quota auto-fallback,
  model cascading, Hermes tri-node persistent memory sync, and Web UI with screenshot paste/vision.
  Use when encountering quota exhaustion, HTTP 429, switching Google accounts, checking model status,
  or launching the AGY web UI.
---

# Antigravity Resilience Toolkit

This skill enables seamless resilience and high-availability operations for Antigravity CLI (`agy`).

## 1. Multi-Account Google Quota Auto-Fallback

When an AGY session hits `Individual quota reached` or `429 Too Many Requests`:
- **Auto-fallback & resume last session:**
  `agya -c`
- **Check registered accounts:**
  `agy-account list`
- **Register a new Google account:**
  `agy-account add <account_name>`
- **Switch Google account:**
  `agy-account switch <account_name>`
- **Run command with automatic multi-account fallback:**
  `agya -p "<prompt>"`

## 2. Model Cascading & Health Checks

- **Check quota health across all available models:**
  `powershell agy-fallback.ps1 check`
- **Run with automatic model cascading (Gemini -> Claude -> GPT):**
  `powershell agy-fallback.ps1 -p "<prompt>"`

## 3. Web UI with Image Vision & Screenshot Paste

- **Launch Web UI:**
  `agya web`
  Provides browser interface at `http://127.0.0.1:4567` with:
  - Drag-and-drop & clipboard paste (`Ctrl+V`) for images/screenshots
  - Real-time SSE streaming & full conversation history import
  - One-click Google account switcher

## 4. Hermes Distributed Memory Sync

- **Push local memory to central hub:**
  `powershell -ExecutionPolicy Bypass -File memory_sync/sync-once.ps1 -Action push`
- **Pull memory from central hub:**
  `powershell -ExecutionPolicy Bypass -File memory_sync/sync-once.ps1 -Action pull`
