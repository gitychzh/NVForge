# Hermes 双机交替优化 - 自动化流

## 核心逻辑

1. **HM1每5分钟**: `git fetch → git reset --hard origin/main`
2. **检查最新commit作者**: 
   - 如果是 `opc_uname` (自己) → 不触发
   - 如果是 `opc2_uname` (HM2) → **轮到HM1了** → 执行优化
3. **HM1执行优化**: 分析HM2日志 → 修改HM2 docker-compose.yml → 重启容器 → 记录到GitHub
4. **HM1提交记录**: commit author=opc_uname, 最后一行="轮到 HM2 优化 HM1"
5. **HM2每5分钟**: `git fetch → git reset --hard origin/main`
6. **检查最新commit作者**:
   - 如果是 `opc2_uname` (自己) → 不触发
   - 如果是 `opc_uname` (HM1) → **轮到HM2了** → 执行优化

## 实现方式

**方案**: 每台机器用 systemd user timer 替换 cron (避免物竞天择)

HM1的Hermes cron (已部署) → 当走到exit=3时，通知Hermes执行优化
HM2的cron (已部署) → 当走到exit=3时，触发Hermes执行优化

## 当前状态

- R1: HM1→HM2 已完成
- R2: HM2→HM1 等待HM2执行
- cron: 双方都每5分钟轮询
- 检测逻辑: 已验证通过