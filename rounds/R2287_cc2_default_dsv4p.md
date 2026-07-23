# R2287 (2026-07-23): cc2 默认模型 glm5_2_nv → dsv4p_nv + dsv4p/pexec 真直连测试

## 摘要

裸测 3 模型 × 2 主机 × 4 配置（integrate/pexec × 直连/5US-IP）发现 glm5.2 当日系统挂窗
全 0%，dsv4p 4 配置全 80-100%。据此把 cc2 默认模型从 glm5_2_nv 改为 dsv4p_nv（HM2 cc4101
env 单点改动），端到端验证通过。同时做 dsv4p/pexec 真直连测试（不经 mihomo，host 直出
中国移动），两台都 100%。

## 数据（改前必有数据）

### 3 模型 × 2 主机 × 4 配置 裸测（N=2/key=10 请求/配置，2026-07-23 05:17Z）

| 模型/配置 | HM1 SR | HM1 avg | HM2 SR | HM2 avg |
|---|---|---|---|---|
| dsv4p / integ 直连 | 100%(10/10) | 2.07s | 100%(10/10) | 1.98s |
| dsv4p / integ 5US-IP | 90% | 3.00s | 100% | 3.30s |
| dsv4p / pexec 直连 | 100% | 1.19s | 100% | 2.51s |
| dsv4p / pexec 5US-IP | 90% | 2.57s | 80% | 2.67s |
| minimax / integ 直连 | 70% | 7.42s | 80% | 0.98s |
| minimax / integ 5US-IP | 80% | 4.84s | 100% | 3.36s |
| minimax / pexec 直连 | 80% | 1.52s | 80% | 3.92s |
| minimax / pexec 5US-IP | 80% | 3.64s | 70% | 2.40s |
| glm5.2 / integ 直连 | 0%(全超时) | - | 0%(全超时) | - |
| glm5.2 / integ 5US-IP | 0%(全429) | - | 0%(全429) | - |
| glm5.2 / pexec 直连 | 0%(全超时) | - | 0%(全超时) | - |
| glm5.2 / pexec 5US-IP | 0%(全429) | - | 10%(1/10) | 10.60s |

**结论**：glm5.2 当日两台机器 4 配置全 0%（直连 15s 超时=NVCF 挂窗，5US-IP 全 429=account
限流），是 cc2 fallback 主来源；dsv4p 4 配置全 80-100%，是现成替代。

### 429 抓包

所有 429 响应体统一 `{"status":429,"title":"Too Many Requests"}`，无任何 ratelimit/retry/quota/limit
响应头。NVCF 不在 429 里暴露具体配额数字（如"1000条/天"）。

## 改动

### 1. cc2 默认模型改 dsv4p_nv（HM2 only）

`/opt/cc-infra/docker-compose.yml` 第 209 行 cc4101 服务块：

```diff
-    - PRIMARY_UPSTREAM_MODEL=glm5_2_nv
+    - PRIMARY_UPSTREAM_MODEL=dsv4p_nv  # R2287: glm5_2_nv->dsv4p_nv...
```

备份：`docker-compose.yml.bak.R_dsv4p_default_20260723`。

机制：cc4101 `config.py` MODEL_MAP 所有条目（含 claude-* 前端名）都映射到 `PRIMARY_UPSTREAM_MODEL`
**变量**（非硬编码 glm5_2_nv），故改 env 一处，cc2 settings.json 的 `model: cc-glm5-2` 自动路由到
dsv4p_nv。不需改 cc2 settings 或 nv_gw。`FALLBACK_UPSTREAM_MODEL=glm5_2_ms`（ms_gw 备用）保持不变。

重启：`docker compose up -d cc4101`（env 变更，recreate）。

### 2. dsv4p/pexec 真直连测试（不改配置，纯观测）

不经 mihomo，host 直出。HM1/HM2 host 真直连出口**同为** `183.211.0.66`（中国移动上海，AS56046）。

| 主机 | 出口IP | SR | avg |
|---|---|---|---|
| HM1 | 183.211.0.66 | 100%(15/15) | 1.47s |
| HM2 | 183.211.0.66 | 100%(15/15) | 1.27s |

dsv4p/pexec 从中国移动直连两台都 100%，延迟 0.5-1.5s 为主。

## 重大认知更新

**HM1/HM2 host 真直连出口是同一个中国移动 IP `183.211.0.66`。** 推翻旧认知"HM1=日本IP/HM2=
中国移动"——那个区分只在 mihomo 代理出口层成立（HM1 7880→103.62.49.138，HM2 7900-7904→美国独立
IP）。两台 host 层裸直连是同一个中国移动出口。

**"直连 NVCF = 100% timeout"的旧结论是 glm5.2 挂窗造成的，对 dsv4p 不成立。** dsv4p/pexec 从
中国移动直连完全可用，无需 mihomo。

## 验证（改后必有验证）

- `docker exec cc4101 env | grep PRIMARY_UPSTREAM_MODEL` → `dsv4p_nv` ✓
- `docker ps --filter name=cc4101` → Up ✓
- 端到端：`curl POST http://127.0.0.1:4101/v1/messages` (model=cc-glm5-2) → 返回 `model:dsv4p_nv`，
  content "Hello"，200 ✓
- dsv4p/pexec 真直连：两台 100% ✓

## 回滚

```bash
ssh -p 222 opc2_uname@100.109.57.26
cd /opt/cc-infra
sed -i 's/PRIMARY_UPSTREAM_MODEL=dsv4p_nv.*/PRIMARY_UPSTREAM_MODEL=glm5_2_nv/' docker-compose.yml
docker compose up -d cc4101
```

## 参数表

| 参数 | 旧值 | 新值 | 位置 |
|---|---|---|---|
| PRIMARY_UPSTREAM_MODEL (cc4101) | glm5_2_nv | dsv4p_nv | docker-compose.yml L209 (HM2) |

## 注意

- cc2 自优化 CLAUDE.md/STATE 大量假设 glm5_2_nv 链路（正反馈数据源会变），但用户明确指令改默认。
- dsv4p 裸测也有少量 429/超时（80-90% 档），但 nv_gw tier 重试链会救回（DB 近 30min dsv4p_nv
  24 请求 21 OK=87.5%），cc4101 fallback 走 ms_gw glm5_2_ms 兜底。
- 铁律：只改 HM2，不碰 nv_gw/ms_gw 源码。
