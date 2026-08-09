# R0810: NVCF function_id 全量重查 + 链路定稿 (dsv4f0731 默认)

## 摘要

NVCF 模型/function_id 全量重查，确认了 4 个模型的可用性，并将 CC 自身链路
(`cc4101`) 与各 adapter 的默认兜底定稿到 `dsv4f0731`（0731 flash，专用 FID
`281478d0`，最稳最快）。本轮的实质改动已直接落到 HM1/HM2 的 `/opt/cc-infra`
live 配置并重启生效；本文档只做记录，不重复部署。

## 背景

COM 的上一轮工作（R-dsv4f 系列）围绕 `dsv4f_nv`（FID `52e1ddb6`）展开，但 NVCF
侧模型状态在 2026-08-07 前后发生了大的位移：

- `dsv4p` 于 **2026-08-07 EOL**（`ai-deepseek-v4-pro` 停服）。
- `kimi` 全链路不可用（k2.6 `f966661c` INACTIVE，k3 `3ea2c6ee` 全 404）。
- `dsv4f` 旧 FID `52e1ddb6` 已 INACTIVE → 404；新专用 FID
  `281478d0`（`ai-deepseek-v4-flash-0731`）ACTIVE，pexec model_id 需带 `-0731`
  后缀。
- `glm5_2` (`3b9748d8`) ACTIVE；`minimax` 最快但非默认。

## 改动（已部署到 live）

1. **nv_gw `config.py`** — 注册 `dsv4f0731_nv`（FID `281478d0`），pexec 走带
   `-0731` 后缀的 model_id，integrate 走普通 `deepseek-ai/deepseek-v4-flash`。
   注释已更新（R0810）：`dsv4f0731_nv` 最稳定，设为默认兜底。
2. **ms_gw `config.py`** — 注册 `dsv4f0731_ms` alias（与 `dsv4f_ms` 同后端，
   显式 0731 命名）。
3. **`cc4101` compose env**（HM1）：
   - `PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv`
   - `FALLBACK_UPSTREAM_MODEL=dsv4f0731_ms`
4. **HM2 `cc4101`** — `PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv`，fallback
   `glm5_2_ms`（HM2 与 HM1 的 fallback 不对称，沿用各自既有 ms_gw 配置）。

## 延迟实测（本轮）

| 模型 | 链路 | 结果 | 平均延迟 |
|---|---|---|---|
| dsv4f0731 (281478d0) | pexec | 5/5 | ~3.2s (ttfb 0.9–7.3s) |
| dsv4p | pexec | 5/5 | ~6.3s |
| glm5_2 | pexec | 3/5 | ~23.5s |
| minimax | pexec | — | 最快 |

dsv4f0731 不仅 SR 最稳，延迟也最低，故定为默认兜底。

## 验证

- [x] `nv_gw` / `ms_gw` `/health` 正常
- [x] `dsv4f0731_nv` / `dsv4f0731_ms` 在 live config 注册
- [x] `cc4101` primary/fallback 指向确认（HM1 + HM2）
- [x] 旧 `dsv4f_nv`（52e1ddb6）FID 404 已确认，不再作为默认

## 脚手架清理

本轮在 canonical repo 临时生成的快照
（`config_R0810.py`/`pexec_R0810.py`/`upstream_R0810.py`/`ms_config_R0810.py`/
`docker-compose.R0810.yml`）已随本 commit 删除——它们只是当时的 working copy，
live 改动直接落在 `/opt/cc-infra`，无需保留快照。

## 后续

- 两个主机 `ms_gw` fallback 不对称（HM1 `dsv4f0731_ms` vs HM2 `glm5_2_ms`），
  如需统一可在下轮对齐。
- `kimi_nv` 彻底不可用，保持注册但不作为任何 adapter 的 primary。