# Tong Quant V0.8 Architecture and Code Audit

审查日期：2026-08-21

审查基线：`8409def` 加当前未提交的数据质量、Tushare 诊断和多数据源文档改动。

## 结论

Tong Quant 已经具备清晰的研究平台分层、可解释领域模型、PIT 时间边界、
Historical Replay、事务化 Research/Validation 写入、研究型 Portfolio/Risk 工件、
失效关闭的 Execution 防线和加固后的 Notification Outbox。静态导入图不存在顶层包循环。

当前成熟度的主要限制不是架构缺失，而是历史数据证据不足。现有 PIT Readiness 仍为
`UNSUITABLE`，因此框架适合继续做数据工程、前向研究和受警告约束的分析，不适合形成
可信历史收益结论，也不应进入 Paper Trading 或 Execution 开发。

## 本次已修复

### 1. 数据摄取写入缺少统一事务边界

过去一个 ingestion 可能先写入 Instrument、Bar 或 PIT 事件，再在写 raw fingerprint、
ingestion batch 或 warning 时失败，形成没有完整审计链的半完成数据。

现在每个 ingestion 的领域数据、原始指纹、批次记录和可用性警告在同一个
`SQLiteStore.transaction()` 内提交。新增失败注入测试证明审计写入失败时所有相关记录
都会回滚。网络请求和 provider 调用仍发生在事务开始前，避免长期占用 SQLite 写锁。

### 2. Tushare 能力报告持久化凭据指纹

能力报告曾保存 token 长度和四字符掩码前缀。它们不是完整凭据，但违反了项目中
“能力状态可以持久化、凭据特征不可持久化”的更严格规则。

现在报告只保存 `configured`、环境状态和 credential source，不再保存 token 长度、
前缀或指纹；现有生成报告中的相关字段也已移除。

### 3. 架构边界测试过度依赖字符串搜索

原测试可能漏掉别名导入，也可能因注释或普通文本误报。边界测试现使用 Python AST
检查真实 import，并新增顶层 package 循环依赖检测。

## 主要未解决问题

| 优先级 | 问题 | 影响 | 建议退出条件 |
|---|---|---|---|
| P0 | PIT 数据集整体仍为 `UNSUITABLE` | Historical Replay 可以运行，但样本质量不足以支持可靠结论 | 核心数据集至少达到 `CAUTION`，关键样本达到 `USABLE`，并有真实跨源一致性证据 |
| P0 | 公司行为与严格 PIT 复权因子不完整 | 不能安全使用前复权/后复权价格做历史验证 | 建立带公告时间、除权日、版本与 source hash 的 adjustment-factor ledger |
| P1 | `DataIngestionPipeline` 直接依赖 `AkShareAdapter`，并内置 AKShare 限制说明 | 多数据源校准独立，但摄取层尚未真正 provider-independent | 拆分通用 ingestion orchestration、dataset capability protocol 和 provider-specific jobs |
| P1 | `SCHEMA` 大字符串与 migration ledger 同时拥有 schema 变更能力 | 新鲜数据库与升级数据库可能通过不同路径得到结构，增加漂移风险 | 建立不可变 baseline migration；所有后续 DDL 仅经 migration 执行并做 schema fingerprint 校验 |
| P1 | 大多数分析表没有数据库外键 | repository bug 可形成 orphan rows，重建报告时才暴露 | 先运行 orphan audit，再分批 table rebuild 加 FK 和级联策略 |
| P1 | `data/storage/sqlite.py` 超过四千行 | owner 边界模糊，修改冲突和回归范围持续扩大 | 按 data、research、validation、portfolio、notification repository 拆分，保留统一 transaction manager |
| P1 | SQLite 并发策略未经过压力测试 | ingestion、notification worker 和分析写入并发时可能出现 lock contention | 明确 busy timeout、单 writer 策略并加入多进程/多连接并发测试 |
| P1 | Runtime Framework Snapshot 仍有 caller-supplied 字段 | Git/config/version 记录可能与真实运行环境不一致 | 用单一 snapshot factory 从运行环境采集并校验所有版本和 config hash |
| P1 | Live provider contract tests 默认跳过且无定时 CI | AKShare/Yahoo/Finnhub/Massive API 漂移可能长期不被发现 | 建立无凭据泄漏的定时 capability/column contract job，失败只降级 trust，不自动修正数据 |
| P2 | 生成报告与代码基线存在未提交漂移 | 无法从 commit 单独重建“当时的 readiness 结论” | 将报告 manifest、query scope、代码 commit 和数据库 snapshot hash 一起冻结 |
| P2 | 没有 coverage 门槛、PIT property tests 与 migration fuzz tests | 边缘时间戳、修订和升级路径仍可能漏测 | 先对 data/replay/storage 设置分模块 coverage 基线，再加入性质测试 |
| P2 | Notification 为 at-least-once | provider 已发送但本地确认前崩溃时可能重复通知 | 支持 provider idempotency key 或 delivery reconciliation；保持默认 disabled |

## 模块边界审查

- `domain` 和 `core` 保持轻量，没有 provider 或 SQLite 依赖。
- `screening` 不拥有研究结果模型；`research.models.ResearchReport` 仍是唯一正式报告。
- `risk` 不依赖 `portfolio`；`portfolio` 只消费通用风险输入。
- `validation` 与 `notifications` 均无 Execution、Broker、Order、Trade、Fill 或 Paper Trading 导入。
- Notification 的四类上游 concrete model fan-in 当前可接受；模型开始独立演化前应引入稳定的
  read-only artifact envelope。
- Execution 仍是隔离且默认 disabled 的骨架，本次未修改任何交易路径。

## 数据与 PIT 审查

- `available_at <= as_of` 在主要查询与 replay 路径中被显式执行。
- Strict PIT 模式拒绝 provider-adjusted bars，Historical Replay 使用 `Adjustment.NONE`。
- 低 trust、provider limitation、缺失数据和退市/ST/停牌信息不会被 replay 静默删除。
- AKShare 当前快照不能被当作历史状态区间；CSI 成分股响应不能被当作完整 entry/exit ledger。
- Tushare 当前限制是账户权限，不是实现缺陷；它应继续作为可选 calibration provider。
- 新 provider 必须逐 dataset 评估 Trust、Coverage、AvailabilityPrecision、HistoricalContinuity
  与 CrossProviderConsistency。provider 品牌或付费状态不自动提高信任等级。

## 建议路线

1. 先冻结本次 hardening，并清理/归档当前未提交的 Phase III evidence。
2. 完成 schema baseline migration、schema fingerprint 和 orphan audit。
3. 抽离 provider-neutral ingestion contracts，再实现 Yahoo/CNInfo；Massive 与 Finnhub 只按
   已验证 dataset capability 接入。
4. 建立定时 provider contract monitoring 和历史连续性仪表板。
5. 只有当核心 replay 数据至少达到 `CAUTION` 且关键输入有双源证据后，才评审
   Paper Trading architecture；继续禁止 Execution 和 Broker 开发。

## 成熟度评估

| 领域 | 评级 | 说明 |
|---|---|---|
| 架构 | Strong prototype | 分层清晰、无静态循环、关键边界有自动化测试 |
| 数据工程 | Developing | 审计链更可靠，但 provider-neutral ingestion 与 schema 演进仍需加固 |
| PIT 数据 | Not ready | 当前证据等级仍不足 |
| Research | Conditional | 可用于前向研究，必须携带 trust/readiness 警告 |
| Validation | Mechanically ready, evidence blocked | 引擎和 replay 已有，输入质量阻断可信结论 |
| Portfolio/Risk | Research artifact only | 不能解释为建议、分配或执行指令 |
| Notification | Hardened disabled baseline | 架构可用，真实交付运维仍未证明 |
| Production | Not ready | 数据、迁移、并发、监控与运维控制尚未达标 |
