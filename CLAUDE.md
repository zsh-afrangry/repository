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
| `docs/5_清理执行日志与工作汇报.txt` | Conclusions + the A/B/C decision sheet (it used to be the log too) |
| `docs/6_当前状态与待决策.txt` | ⭐ **Read this first** — short current state + the open choices. Rewritten in place, never appended. |
| `docs/7_工作记录（时间线）.txt` | The full chronological log (was `docs/5` §2). Append here; read it by section number. |

## The three rules most likely to bite

1. **No authentication, and the backend now binds `127.0.0.1:8010`** (changed 2026-09-20 from
   `0.0.0.0`; a phone on the same network therefore can no longer reach it). The port is still
   configurable via `KM_BACKEND_PORT`, the **host is hard-coded on purpose** — if this is ever
   exposed beyond this machine, add an API-key dependency first rather than putting `0.0.0.0`
   back.
2. **Do not delete the light theme.** `.theme-light` in `main.css` and `updateThemeClass()`
   in `Dashboard.vue` are unreachable at runtime but are retained deliberately — the nav
   theme button is a placeholder that only shows a "feature not implemented" toast (now
   positioned centre-upper, `top: 20%`, by owner request).
3. **`npm run build` works now.** The old note claiming it had never been verified is
   obsolete; it was run successfully on 2026-09-20.
