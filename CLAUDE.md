# KnowledgeMap — CLAUDE.md

**This file is only a pointer. The single source of truth is [`AGENTS.md`](./AGENTS.md) —
read that file instead, and edit that file rather than this one.**

## Why

This file used to be a 291-line copy of `AGENTS.md`, kept in sync by hand. Both copies had
drifted from the code, and every correction had to be made twice. On 2026-09-20 the
duplication was removed and `AGENTS.md` was corrected against the actual source (design
tokens, router prefixes, the TradeSim isolation class, the build-verification status).

`AGENTS.md` is not a Claude-specific file, so both Claude Code and other agents read it
directly; nothing is lost by keeping this file short.

## What lives where

| File | Role |
|---|---|
| `AGENTS.md` | Repository layout, tech stack, design system, per-module docs, theme, `/vault`, development notes. **Edit this.** |
| `docs/1_前端界面背景与特效整理.txt` | Living register of background/animation effects |
| `docs/2_交易策略模块的完善.txt` | Historical archive — see the banner at its top for falsified claims |
| `docs/3_KnowledgeMap集成TradeSim正式迁移计划.txt` | Historical migration record — see the banner at its top for superseded claims |
| `docs/4_项目整理审计与清理计划.txt` | Frozen audit baseline and batch plan (do not edit) |
| `docs/5_清理执行日志与工作汇报.txt` | Live execution log |

## The three rules most likely to bite

1. **No authentication.** The backend binds `0.0.0.0:8010` with no auth; every `/api/...`
   route, including the paid LLM endpoints, is open to the local network. Bind `127.0.0.1`
   for local-only use.
2. **Do not delete the light theme.** `.theme-light` in `main.css` and `updateThemeClass()`
   in `Dashboard.vue` are unreachable at runtime but are retained deliberately — the nav
   theme button is a placeholder that only shows a "feature not implemented" toast.
3. **`npm run build` works now.** The old note claiming it had never been verified is
   obsolete; it was run successfully on 2026-09-20.
