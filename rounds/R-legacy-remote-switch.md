# R-legacy-remote: HM2 cc2 settings.json 切到 40001

**日期**: 2026-08-01
**主机**: HM2
**铁律**: HM1 零改动

## 变更

HM2 `~/.claude/settings.json`:
- `ANTHROPIC_BASE_URL`: `http://127.0.0.1:4101` → `http://127.0.0.1:40001`
- `ANTHROPIC_API_KEY`: `cc4101-token` → `sk-litellm-local`
- `model`: `cc-glm5-2` → `glm5.2_cc`

备份: `~/.claude/settings.json.bak.R-legacy-remote`

## 不动的

- cc4101 容器 (port 4101) — 原模型链路保留, 未做任何改动
- nv_gw / ms_gw / 其他所有容器 — 不动

## 链路对比

切换前 (cc2):
  cc2 → 127.0.0.1:4101 (cc4101) → nv_gw:40006 → NVCF

切换后 (cc2):
  cc2 → 127.0.0.1:40001 (legacy_cc_1) → legacy_ms_litellm:4000 → ModelScope

## 验证

- HM2 本地:40001 health=ok
- E2E 非流式: model=glm5.2_cc, stop=max_tokens, tokens=17
- cc4101:4101 原链路 health=ok, 容器 Up 2 days 未动

## 回滚

改回 `~/.claude/settings.json.bak.R-legacy-remote` 即可.
