---
name: github-ready
description: Use this skill whenever the user wants to clean up, tidy, or prepare a code project before pushing it to GitHub, making a repo public, or sharing code externally. Covers scanning for leaked secrets/API keys, removing debug code and dead code, writing a proper .gitignore, adding a minimal README, and a final safety check before the first commit. Trigger this for phrases like "upload to GitHub", "push to GitHub", "open source this", "clean up my project", "prepare this repo", even if the user doesn't explicitly ask for a checklist.
---

# GitHub Ready

Goal: make a project **safe and presentable** for GitHub without changing how it works. Tidy, not rewrite — don't refactor logic, rename working functions, or restructure folders that already work unless asked separately.

## 1. Security scan (always first)

Not optional, even for small personal projects — a leaked key on a public repo gets scraped by bots within minutes.

- Search the whole project for hardcoded secrets:
  ```
  grep -rniE "(api[_-]?key|secret|token|password|bearer)\s*=\s*['\"]" --include=*.{js,ts,jsx,tsx,py,json} .
  ```
  For more rigor, run `gitleaks detect` or `truffleHog` if available.
- Check for `.env` / `.env.local` files. Confirm they're in `.gitignore` and were never committed: `git log --all --full-history -- .env`.
- If `.env` exists, create `.env.example` next to it with the same variable names and placeholder values, e.g. `GEMINI_API_KEY=your_key_here`.
- If a secret was already committed in an earlier commit, flag it to the user directly — it needs history rewriting (`git filter-repo` or BFG Repo-Cleaner) plus rotating the key, not just a new commit on top.

## 2. Clean up the code

- Remove commented-out dead code and leftover debug prints (`console.log`, `print()`) not meant to stay.
- Remove unused files, imports, and variables.
- Match existing formatting/linting — use the project's configured formatter if there is one, don't introduce a new one.

## 3. Write or update `.gitignore`

Base it on what's actually in the project. Typical entries for a Bun/Node + Python mix:

```
node_modules/
__pycache__/
*.pyc
.venv/
venv/
.env
.env.local
.DS_Store
Thumbs.db
.vscode/
.idea/
dist/
build/
```

Don't ignore lockfiles (`bun.lockb`, `package-lock.json`, `requirements.txt`) — those should stay committed.

## 4. Minimal README

If there's no README, add a short one covering:
- What the project does (2-3 sentences)
- How to install/run it
- Required environment variables (reference `.env.example`, never restate real values)

Skip badges, contribution guides, or CI setup unless asked — the goal is a repo that makes sense to open, not a polished OSS template.

## 5. Final check before the first push

- Run the project once after cleanup to confirm nothing broke.
- `git status` and review the file list — nothing sensitive should be staged.
- On a fresh repo, confirm `.gitignore` is in place *before* the first `git add`.