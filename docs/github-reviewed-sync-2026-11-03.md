# GitHub 定时审查同步

日期：2026-11-03，马来西亚时间。

Tong 已授权定期推送。新增当前对话绑定的 heartbeat“Tong Quant GitHub 审查同步”
（tong-quant-github），每天 05:00，保存后回读确认 ACTIVE、时点及对话绑定正确。
原“Tong Quant 量化交易模型推进”的 02:00／03:00／04:00 与 prompt 不变。
使用应用 automation 工具创建／回读，没有手写定时配置。

## 边界

- 唯一远端 TONGResearch/tong-quant-framework，仅对当前对应分支非强制推送；
  审查完整待推送范围。远端分叉、权限／认证失败停止并通知。
- 授权完整审查工作包的提交与推送，不授权 git add .、重置、强推、自动变基、
  改远端或夹带用户改动。混杂范围不能分离时暂停。
- 已完成且可独立验证的工作切片也可同步，无需整个里程碑已经验收；不得据此
  修改 ready/not accepted、PIT、策略或交易验收结论。
- 精确候选提交树需在隔离环境通过 pytest、Ruff、mypy、diff、治理及独立审查；
  混合脏工作区的测试不能证明某个候选提交可靠。
- 排除凭据、.env、数据库、缓存、原文、日志、构建和 IDE 文件；不输出密钥、
  不在聊天索取密码、不绕过 SSH 主机校验。同步授权不是秘密发布授权。
- 仅成功同步、失败、新风险或需要操作时通知；无合格新提交／无变化保持安静。

## 核实

当前分支 codex/wp-launch-001-hardening；origin 为
git@github.com:TONGResearch/tong-quant-framework.git。
现有 SSH 的只读查询成功，使用 BatchMode 和严格主机验证，无密码／凭据输出。
查询时远端 6be0a842d997b7707b0d347b3206e6e003aac7fb 是本地
8794b572f27262d73abdb031103b3bd57035efd8 的祖先；本地领先一提交，未分叉。
后续混合未提交内容尚非可发布基线，本轮没有立即提交或推送。
定时运行须重新核对实时远端，不能依赖这份历史 SHA。

## 运行与恢复

这是 Codex 对话定时同步，不是系统常驻服务或云端全量备份。本地任务需电脑与
应用可用，继续遵守文件／网络权限；休眠、离线、认证或检查失败时不保证准点。
参见[官方定时任务说明](https://developers.openai.com/training/walkthroughs/scheduled-tasks)。
GitHub 仅接收审查代码；数据库和外部原文仍需独立加密备份、共保留与恢复演练。
克隆仓库不等于恢复完整研究数据、环境或凭据。代码同步不放行实盘或数据门槛。
