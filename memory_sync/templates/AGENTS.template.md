# Mandatory Agent Execution Policies & Memory Rules

## 1. Hermes Memory Architecture Policy
- The agent operates with dual durable memory files:
  - User Persona & Preferences: `USER.md`
  - Technical & Project Knowledge: `MEMORY.md`
- When a user preference or identity detail is learned, immediately update `USER.md`.
- When a new technical pattern, bug resolution, or architecture decision is discovered, append to `MEMORY.md` under `Continuous Learning & Troubleshooting Log`.
- Always push updates to the central hub via sync scripts.

## 2. Token-Efficiency & Code Analysis Policy (CodeGraph First)
1. Step 1: CodeGraph Init (`codegraph init`)
2. Step 2: CodeGraph Sync (`codegraph sync`)
3. Step 3: CodeGraph Explore (`codegraph explore <query>`)
- Do not read entire large files into context or dump directories.
