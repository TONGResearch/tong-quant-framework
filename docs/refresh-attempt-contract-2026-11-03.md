# 采集尝试与恢复状态契约

日期：2026-11-03。WP-LAUNCH-001，ready / not accepted。

同日后续[持久账本与原子关联](refresh-ledger-persistence-2026-11-03.md)已实现；
本文件保留 v1 纯规则交付记录。当前尝试模型为 v2-retention-codes，schema 0.8.3，
原证据库未升级。规则层仍无 I/O；持久仓库在独立模块，完整 worker／核验仍未部署。

## 已实现：无 I/O 的可执行规则

data.refresh_attempts 提供不可变的 RefreshAttemptPolicy、RefreshLease 和 RefreshAttempt，
以及创建、进入留存、报告留存、失败与过期转换。它们是供未来仓库使用的值与规则，
不是正在运行的采集器或持久任务队列；没有网络、SQLite、时钟自动读取、调度器或 AI。

```text
RUNNING / FETCHING
  -> 明确发生的临时采集失败 -> 有限退避重试时点
  -> 权限／契约／未知内部失败 -> 无自动重试
  -> RUNNING / RETAINING -> DATA_RETAINED 或 FAILURE_SNAPSHOT_RETAINED
  -> 任一阶段租约过期，或留存阶段失败 -> 必须先对账
```

所有 DATA_RETAINED、FAILURE_SNAPSHOT_RETAINED、RETENTION_FAILED、LEASE_EXPIRED
均标 reconciliation_required。**没有完成检查点、数据准入或研究授权 API。**
留存结果目前只是调用者声明的 batch 引用，必须由未来仓库核实真实记录及原文。
COMPLETED 的旧 ingestion batch 不能独自证明真实数据可用。

## 时间、归属与失败规则

- 所有时间归一为 UTC 实际时点；拒绝无时区、时钟回退、混用 DST 两个同名时刻。
  租约到期瞬间起不再允许归属进程补写。留存开始时间须在有效租约内且持续保留。
- 归属绑定 job_id、generation、worker_id 和公开随机 nonce；任一不符即拒绝当前
  值上的更新，终态不能再次修改。nonce 是公开并发隔离标识，不是账户凭据。
- 默认预算三次、租约 60 秒、初始退避 5 秒、退避上限 300 秒；严格整数且有资源
  上界。它们仅是未启用的代码默认值，不修改项目配置或启动任务。
- 仅在 FETCHING 阶段明确报告的 timeout、network_unavailable、rate_limited
  有有界退避时点。权限、接口不支持、解析异常、内部错误不自动重试。
  租约消失可能发生在数据提交之后，因此即使当时记录仍是 FETCHING，也不猜
  “一定未提交”；过期统一进入待对账。留存失败无论错误类别均不盲目重跑。
- 未记录响应时 captured_payload_hash／batch 为 None，不制造零哈希或异常文本哈希。
  进入留存须显式给出捕获内容的格式有效哈希；它可对应解码／转换后的快照，
  **不是自动证明上游 HTTP 原始响应**。代码不验证对应字节或原文真实性。
- 错误只接受有界枚举，无原始异常／URL／令牌内容字段；标识和版本严格校验。
  类型／结构约束不能识别每个任意裸字符串秘密，调用者不得放入任何真实凭据。

## 并发与持久性的限制

纯函数只能针对传入的当前值校验，不能知道调用者是否持有数据库最新状态，
不能认证时间、任务身份或输入哈希。两个进程仍可能各自对旧副本完成计算。
未来 SQLite 仓库必须用事务内的代次／版本 CAS、随机 nonce、唯一键与真实时钟
检查，原子地领取和保存，拒绝落后进程的提交；不能把本模块当成并发领取锁。
代次连续性、任务幂等、租约所有权、预算固定与重试历史由持久仓库负责。

既有 ProviderNeutralIngestionService **仍未持久记录 pre-fetch 尝试**；本轮没有
给它接入假账本，没有复用 write_canonical 做调度回调，也没有安装任何更新服务。
具体迁移／原子关联要求见[账本方案](proposals/data-refresh-ledger-v1.zh-CN.md)。

## 验证与版本

新增 57 项测试：有效与非法转换、不同任务／代次／进程／nonce、租约边界、时钟
回退／UTC／DST、重试预算与封顶、未知提交恢复、失败快照、原始字段／凭据型
文本拒绝及无 I/O／无交易依赖。既有计划与模块边界测试继续运行。
合计定向 **139 项通过**；全量 **3149 通过、6 跳过**，142.24 秒。Ruff、mypy
（301 文件）、治理（151 项）及 git diff --check 通过。六个跳过项为可选真实
联网测试；测试不证明持久恢复、并发领取或真实提供商可用性。

新增源码／测试／文档的依赖与凭据型输入边界已复核，没有新增真实凭据或本地
数据库／缓存／原文文件；这不是完整旧脏工作区的保密／发布认证。
价格／原生财务样本库哈希保持
0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087；
原文样本库保持 ce1e3ae4c2b97bb52733cd35724189ab80d2360ec62e3b5d3f38cf6ea506da13。

新增 DATA_REFRESH_ATTEMPT_VERSION=data-refresh-attempt-v1；framework 0.8.0、
schema 0.8.2、迁移头 0010_portfolio_evidence_lineage、计划 v2、Financial 和默认
配置不变。没有新表、迁移登记、用户数据、原文、网络采集或交易层改动。

下一步：审查并在测试数据库实现专用账本迁移／仓库，验证并发 CAS、事务内证据
关联和提交后恢复，然后才接一次性受控采集。定时部署和研究准入仍单独核验。
PIT UNSUITABLE、production NOT_READY、R1–R6 partial、执行／通知关闭均不变。
无需 Tong 提供密码；本轮不提交、不推送，不代表跨设备可恢复基线已完成。
