# Rounds 索引

## 现行机制（主线，R568+）

R568 起 CC 直接编辑两机（R569 取消双机交替优化/只改对端机制）。
主线保留 R568+ 全部轮次记录，文件命名 `R<N>_<summary>.md`。

## 已归档：R1–R567

R568 之前是「双机交替优化」机制产物（HM1↔HM2 轮流改对端），R569 已废止。
这些早期记录整体移至 `_archive_pre_r568/`，仅供历史追溯，不再代表现行配置。
机制转换边界轮 R568（self-direct multi）/R569（cleanup）保留在主线。

## 其它子目录

- `_archive_nonstandard/` — 早期非标准命名轮次（mihomo-remove、partial-proxy）
- `openclaw_8round/` — openclaw 早期独立 8 轮（OC_R1–OC_R9）
- `references/` — 跨轮参考资料（如 r705 时区陷阱）
- `CLEANUP-*` / `ENG-*` — 一次性工程记录

## 查找

```bash
ls rounds/                       # 主线 R568+
ls rounds/_archive_pre_r568/ | grep R560   # 找某个早期轮次
git log --oneline -- rounds/_archive_pre_r568/R282_hm1_optimize_hm2.md  # 该轮提交历史
```
