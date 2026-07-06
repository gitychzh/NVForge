# R786: HM2 compose NVU_KEY 改 .env 引用 (消除硬编码字符错误隐患)

## 摘要

R785 发现 K3 403 根因是 `docker-compose.yml` 第54行硬编码 `NVU_KEY3` 有 1 字符录入错误 (v→b)。
`.env` 里 K3 一直是正确值, 但 compose 硬编码覆盖了 `.env`, 所以正确值没生效。

R786 把 compose 里 5 行硬编码 `NVU_KEYx=<完整key>` 改成 `NVU_KEYx=${NVU_KEYx}` 引用 `.env`,
让 key 字符的唯一真相源 (single source of truth) 是 `.env` 文件, 不再有硬编码副本,
从根本上杜绝 "compose 里打错 1 字符" 的隐患。

## 改前数据 (铁律)

- `.env` (557 字节, 2026-07-02 创建) 5 个 key 都是正确值 (K3 = `...MXv_HZry`)
- `docker-compose.yml` 第52-56行硬编码 5 个 key (K3 已在 R785 修好为 `...MXv_HZry`)
- 两份副本字符一致 (R785 修好后), 但维护两份 = 未来再打错 1 字符的隐患仍在
- docker compose 默认自动读同目录 `.env` 做变量插值 (`${VAR}` 语法), 无需 `env_file:` 指令

## 改动

### `/opt/cc-infra/docker-compose.yml` 第52-56行
```yaml
# 改前 (硬编码, R785 修好的 K3)
- NVU_KEY1=nvapi-ADdBJRa0...X_YAlO
- NVU_KEY2=nvapi-Oi2S0DK-...yu6O
- NVU_KEY3=nvapi-BNzNJtED...MXv_HZry
- NVU_KEY4=nvapi-1gFJdRLa...x29O
- NVU_KEY5=nvapi-VsVTxqE_...3swt

# 改后 (引用 .env)
- NVU_KEY1=${NVU_KEY1}
- NVU_KEY2=${NVU_KEY2}
- NVU_KEY3=${NVU_KEY3}
- NVU_KEY4=${NVU_KEY4}
- NVU_KEY5=${NVU_KEY5}
```
backup: docker-compose.yml.bak.R786_env_ref

`.env` 文件本身不动 (5 个 key 已是正确值)。compose 用 `${VAR}` 插值语法, docker compose
启动时自动从 `.env` 读取赋值。

## 验证 (铁律: 改后必有验证)

### 1. `docker compose config` 插值正确
```
NVU_KEY1: nvapi-ADdBJRa0...X_YAlO   ← 跟 .env 一致
NVU_KEY2: nvapi-Oi2S0DK-...yu6O
NVU_KEY3: nvapi-BNzNJtED...MXv_HZry  ← 位置65=v (正确)
NVU_KEY4: nvapi-1gFJdRLa...x29O
NVU_KEY5: nvapi-VsVTxqE_...3swt
```

### 2. 容器内 env 跟 .env 一致
```
docker exec nv_gw env | grep NVU_KEY3
→ NVU_KEY3=nvapi-BNzNJtED...MXv_HZry  (位置65=v, 正确)
docker exec nv_gw env | grep NVU_KEY1
→ NVU_KEY1=nvapi-ADdBJRa0...X_YAlO   (跟 .env 一致)
```

### 3. 端到端 8 个 kimi 请求
```
200 200 200 200 200 200 200 200  (8/8 成功)
```

### 4. DB 确认 K3 (key_idx=2) 仍 200
```
nv_key_idx | egress_route | egress_ip      | status | duration_ms
     2     | mihomo-7896  | 134.195.101.195| 200    | 841    ← K3 仍正常
     0     | mihomo-7894  | 134.195.101.193| 200    | 824
     4     | mihomo-7899  | 134.195.101.180| 200    | 839
     3     | mihomo-7897  | 103.62.49.162  | 200    | 2124
     1     | direct       | 218.93.250.242 | 200    | 4975
```
全 5 key 200, K3 仍 841ms 正常。

## 设计要点

- **single source of truth**: key 字符只在 `.env` 里一份, compose 只引用变量名, 不可能再打错字符
- **不删 `.env`, 不加 `env_file:`**: docker compose 默认读 `.env` 做 `${VAR}` 插值, `env_file:` 是另一种机制 (把文件作为容器 env 注入, 不做插值), 两者不要混用
- **`.env` 不入 git**: `.env` 在 `.gitignore` 里 (含 secret), compose 引用 `${NVU_KEYx}` 不泄露 key
- **HM1 不同步**: HM1 用户明确暂不动; HM1 的 compose 仍是硬编码, 等用户允许再改

## 回滚
```bash
cd /opt/cc-infra && cp docker-compose.yml.bak.R786_env_ref docker-compose.yml
docker compose up -d nv_gw
```

## 相关
- R785 (commit 8ee1e40): K3 typo 根因修复
- R784 (commit d28e195): per-key IP A/B + DB egress_ip (A/B 配置继续跑, 用数据验证 IP 是否影响稳定性)
