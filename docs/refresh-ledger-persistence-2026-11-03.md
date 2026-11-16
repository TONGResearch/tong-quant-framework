# 数据更新持久账本与原子留存关联

日期：2026-11-03。WP-LAUNCH-001，ready / not accepted。

## 实现

新增 migration 0011_refresh_ledger，schema 0.8.3；framework 仍为 0.8.0。
两张表 refresh_jobs／refresh_attempts 保存幂等任务、固定计划／预算、连续代次、
公开 nonce、租约、阶段、时间、内容哈希、批次引用和有界错误码。
三条索引含每任务仅一条 RUNNING 的部分唯一索引；六个触发器保护任务身份、
尝试身份／终态／历史及关联批次不可改。batch 外键禁止引用不存在或删除的批次。

SQLiteRefreshRepository 复用 SQLiteStore 的连接与 BEGIN IMMEDIATE 事务，不建立
旁路库，不调用 initialize，不联网。缺失库不创建；旧 schema 要求显式迁移。
只读仓库可重建账本，不能领取或更新。通用存储新增连接借用边界，专用仓库拥有 SQL。

```text
离线计划 -> 校验／登记 -> 事务领取并保存尝试（先于网络）
  -> 有界捕获（本轮尚无 worker）-> 保存 RETAINING 与实际捕获内容哈希
  -> ingest(..., refresh_lease=...) -> batch／证据／原文登记／尝试关联同事务提交
  -> reconciliation_required（不是数据准入或成功检查点）
```

不带 refresh_lease 的旧调用保持原行为，不自动获得 pre-fetch 审计。
新路径须先持久领取、捕获一次，再用返回该捕获结果的适配器留存；不能重新下载
却沿用旧哈希／时钟。普通 adapter.fetch 仍可能联网。原 Provider 接口不变。

## 并发、关联与恢复

- 领取在写锁内重读时钟、状态、预算、历史连续性和 row_version。CAS 失败者不领取。
  更新从最新存储值重建，绑定 job／generation／worker／nonce；拒绝过期写入。
- 已知临时 fetch 失败有限退避；权限／接口不支持停止重试。留存失败、租约过期
  持久进入待对账，不盲目创建新代次。clock 仍是主机时钟信任边界。
- 关联核对 scope、提供商、窗口、请求类型／版本、内容哈希与真实捕获时间。
  A 股 DailyBarRequest 与捕获后空参数的证据请求分开；美／港／马保留 Yahoo 契约。
  路由可转换不代表 BSE 真实覆盖、上市／状态／价格基础或独立校准。
- 关联只能借用留存方事务；关联失败／过期时 batch 和证据一起回滚。提交后调用者
  中断，精确关联仍可重建，不能用证券／时间范围猜测是否已写入。
- observed_unqualified／partial_unqualified 只表示有内容保留。无数据、提供商不可用、
  权限失败、解析失败分开；新 insufficient_data／provider_unavailable 码对应尝试
  v2-retention-codes。没有捕获不造哈希；解码内容哈希不证明上游 wire bytes。

## 验证与迁移

测试仅用临时 SQLite、独立子进程、合成捕获和假提供商。覆盖并发只领取一次、
领取后进程退出、过期／重试预算、三市场价格／失败快照、财务权限、A 股空结果、
关联故障／过期回滚、提交后中断／重启、外键、历史不可改、只读与旧库隔离升级。
新增 **36 项**；定向 **129 项通过**；全量 **3185 通过、6 跳过**，162.98 秒。
Ruff、mypy（302 文件）、治理（153 项）、git diff --check 通过。跳过项为可选
真实联网测试；不构成真实市场数据覆盖、部署、候选提交树或策略验收。
本轮依赖／凭据与新增文件清单复核未发现新增真实秘密、数据库或原文入库到 Git；
不等于完整旧脏工作区的保密认证。原文库 SHA-256 保持
ce1e3ae4c2b97bb52733cd35724189ab80d2360ec62e3b5d3f38cf6ea506da13；
价格／原生财务库保持 0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087。

旧 0010 的定义哈希固定为
b8a416cc3683a6f4031db9781b643369f4459e167a20c1d4dbdec6629c965bf6。
旧迁移 checksum 与 SCHEMA 基线文本不变。新 DDL 在事务内运行，避免半升级；
新物理指纹独立记录。备份／恢复测试覆盖新增表和旧路径。旧库测试构造器须一并
移除挂在旧 ingestion 表上的新增触发器，不能把含新残留的库误标成旧版本。

**用户现有证据库未升级。** 任何显式 initialize 都可能升级 schema；不得直接
用旧采集初始化命令指向原库试验。先加密备份，在隔离恢复副本审查迁移和原文
共保留，再决定升级目标。版本变化不能自动继承旧配置／schema 绑定的验证。

## 余下工作

尚无一次性 worker、自动采集定时器、完整对账核验／恢复 API、成功数据检查点或
研究刷新服务。待对账状态不会自行成为成功。跨进程原文登记／回滚清理竞争仍需
专项验收；数据库原子性不是文件系统事务，也不证明加密异机恢复已完成。

PIT UNSUITABLE，production NOT_READY，R1–R6 partial，执行／通知 disabled。
未改 Portfolio／Execution／Broker／Paper 功能；通知仅更新 schema 版本断言。
未提交／推送混合工作区。[未来定时审查同步](github-reviewed-sync-2026-11-03.md)
与数据采集／交易部署完全分开。
