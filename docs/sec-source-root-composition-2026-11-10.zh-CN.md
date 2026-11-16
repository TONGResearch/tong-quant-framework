# 微软行情、财报与持仓的原文目录组合

日期：2026-11-10，马来西亚时间。WP-LAUNCH-001 只读增量，不接受整个工作包。

## 实际阻碍与修复

11月9日真实样例将Yahoo行情和新SEC目录/正文保存在不同数据库、不同原文根目录。
原来的单一 --artifact-root 无法在一次调用中分别核验它们；不能为了组合而复制原文、
改注册记录、猜目录或关闭哈希检查。

既有 inspect_global_technical.py 新增显式 --sec-artifact-root：

- 仅随完整SEC database/CIK/accession参数在US只读模式使用，不支持capture。
- 不选时原有单根行为和输出不变；同一数据库不接受矛盾的两个原文根。
- 分开的数据库可以各自使用明确原文根；SEC正文、ticker声明和精确期间共用选定SEC根。
- 原目录、批次、字节、来源标签与可用时间保持不变，没有搬移、覆盖或注册重绑定。
- 选错/缺失原文根、最新失败、未来或损坏来源保持拒绝，不回退到价格原文根或旧好数据。
- 单根/双根不是独立数据一致性或来源认证。两个数据库只共享分析时点，不声称跨库/跨文件原子快照。
- 输出sec_source_selection标明显式选择、是否同根和继续关闭的权限，不输出本地绝对路径。
  选择语义由US_SEC_SOURCE_ROOT_VERSION版本化；输入内容仍绑定原有证据及组合哈希。

## 组合哈希缺口

复核发现11月9日新增持仓备注时，代码先计算财报组合哈希，再追加holding_review。
组合哈希因而没有覆盖附加备注；没有持仓的旧组合不受影响，没有真实下单或收益错误证据。

现改为先构建持仓复核，再计算完整组合哈希，覆盖全部持仓备注、复核结果和选定来源。
新持仓组合使用EQUITY_HOLDING_DISPLAY_VERSION=equity-evidence-holding-display-v1，
保留旧文件/旧哈希，不静默重写。美股SEC和港马已审阅文件分支均补回归测试。
独立holding_review版本和技术/财务原公式不变；哈希不是凭据、源真伪认证或投资准入。

## 真实微软离线运行

在同一分析时点2026-11-09T20:44:15+00:00，原入口组合：

- 757条原生行情观测，最新仍为11月6日，不是当前盘口。
- 新SEC 10-Q正文、ticker声明与本期/去年同期10项精确期间检查。
- 所有者本地手工持仓备注及原来的亏损复核阈值；未记录账号或新增凭据。
- 持仓对照仍BLOCKED，因为价格早于观察；期限仍NOT_ESTIMATED，执行权限false。
- 10项期间检查仍OBSERVED_SUBSET_UNQUALIFIED，6项保留其他标签上下文未解析警告。
- fundamentals_status仍missing：它指独立的Yahoo原生年度数据，不代表SEC已知数值也缺失；
  不能拿SEC值静默填入原生字段、宣称会计映射完成或生成Financial分数。

两次完整JSON逐字一致，完整组合哈希重算通过，两份原数据库哈希均不变。
组合标识：f883bccdd984d62094c513de9dc0b9996d36b4ee122af412e2b49327a984f0a1。
忽略目录data/processed/msft-integrated-20261110-2iqbltmq/combined-evidence.json
保留完整结果，权限600；这是私有本地研究资料，不随Git同步或自动加密备份。
本轮没有新网络抓取。Markdown仍只覆盖已有展示部分；完整SEC期间与根选择需看JSON，
不能声称新增了完整中文基本面结论、正式ResearchReport或持仓决策界面。

在项目根目录，沿用原参数并明确添加：

```sh
--sec-database data/processed/msft-sec-20261109-xok7gp2w/snapshot.sqlite3 \
--sec-artifact-root data/processed/msft-sec-20261109-xok7gp2w/raw \
--sec-cik 0000789019 --sec-accession 0001193125-26-436133 \
--sec-identity --fundamentals --sector-profile nonfinancial \
--sec-period RevenueFromContractWithCustomerExcludingAssessedTax=2026-07-01/2026-09-30 \
--holding-context data/processed/msft-holding-review-20261109/holding.toml
```

这些参数是已留存样例，不保证换设备存在相同数据。仍需显式database/artifact-root/market/symbol/as-of。
实际退出码2表示未准入诊断，不是运行异常或投资/部署验收。

## 验证与下一项

新增17项测试：15项SEC来源选择/错误边界/完整持仓哈希/离线默认兼容，2项港马持仓组合哈希。
全量pytest：3846通过、6跳过，296.11秒；Ruff、mypy（315源文件）、治理（173项）、
git diff --check和新增文件空白检查通过。静态导入检查无新增交易/投资组合/通知依赖。
真实历史MSFT的无新选项SEC JSON与此前隔离候选脚本逐字一致，两份旧库均不变。
合成/网络跳过测试不认证数据真值或投资收益；混合工作区检查不代替独立候选树发布审查。

本轮仅移除已知的原文目录组合阻碍，并修复持仓组合内容核对缺口。下一项仍是微软会计/期间/股类
核验、明确可证伪论点条件与真实退出/补仓/持有窗口验证，不能继续以同屏代替决策链。
没有schema、依赖、默认开关、订单或券商改动；PIT UNSUITABLE、production NOT_READY保持。
不自动提交/推送，旧候选的独立审查和精确树检查不由混合工作区测试替代。
