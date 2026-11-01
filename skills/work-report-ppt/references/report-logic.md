# 从资料组织成工作汇报

先执行SKILL的严格澄清门禁，任何模糊必须询问用户并等待答复。这里的字段由执行者依据真实对话和材料填写，不要求用户手写JSON；不为填字段而猜用途、结论、指标或责任。

## 听众问题与汇报主线

先明确“希望听众了解、决定或支持什么”，写`decision_goal/audience_question/key_claim_id`；核心信息由所引claim投影。澄清阶段的核心信息可表述为要回答的问题，分析之前不预设好看的结论。设计代选不等于代定事实。

六个角色可跨页、合并到同页或明确说明不适用，不是固定六页模板：

| 角色 | 回答的问题 |
|---|---|
| goal | 原目标或本次汇报要支持什么判断？依据在哪里？ |
| results | 实际完成什么，哪些只是计划？ |
| gap | 距目标、节点或比较基线差在哪里？ |
| reasons | 哪些解释受材料支持，哪些尚需验证？ |
| actions | 下一步做什么，由谁、何时、按什么标准验收？ |
| requests | 希望听众决定什么或提供什么支持？ |

经营复盘看目标与结构差距；项目汇报看节点、依赖、交付和阻塞；周月报看成果、未完成项和下一周期动作；方案提案看问题、选项、证据、风险及所需决定。按任务取舍，不给每类都硬塞同比环比或饼图。

先整理事实与来源，再形成发现。保留能改变听众判断的信息，合并支持同一结论的材料，删去重复过程和不能支持结论的装饰。每页突出一个核心信息；信息过多应拆分，不能缩字或循环三四种构图。

## 发现、证据和状态

`narrative.findings`每项含`id/text/kind/scope/comparisons/evidence_ids`：

- `observation`：事实或描述性比较，数值来自实际分析，不凭模板补数。
- `hypothesis`：待验证假说，必须有`validation`明确后续核什么材料/对照；页面使用简短“原因待核实”，正文也不能写成已证实原因。
- `explanation`：材料支持的解释，必须有原文来源、`support_notes/limits`；只有描述性数字不能放行。正文按材料支持范围表达，不统一加“含待核对解释”；全文记录保留于提纲和备注，执行者核对原文是否真支持该解释。

`comparisons`必须显式列出该结论使用的基准，取值`target/previous/year_ago/ytd_target/ytd_year_ago/level`；`scope`写清业务范围与期间。预算差、环比差、同比差不得混写。

`narrative.claims`是页面消息的唯一来源。每项含`id/text/finding_ids/comparisons/scope/strength`；`strength`为`descriptive/interpretive/conditional`。描述性结论只能引用观察事实，解释性结论必须引用带边界的解释，条件性结论必须有`conditions`和`falsifier`。结论文本出现“预算/目标/缺口”时必须有target基准，出现“环比/同比”时必须对应previous/year_ago。排除某因素对差距的贡献时，必须显式声明`exclusions`并引用`method_evidence_ids`中的桥接事实（`bridge.*`）；桥接存在或闭合都不证明被排除的项为零，更不证明因果；仍须逐项核对桥接项、期间、范围及残差。普通边界说明如“这不是因果证明”不属于排除性归因，不能因否定词误拦。

`narrative.evidence`两种类型：

1. `source`：`id/origin/purpose/file/sha256/lines:[起行,止行]/quote`，行号从1开始，引用确实存在于该UTF-8片段。`origin`为`user_supplied/external/derived/synthetic`，`purpose`为`content/approval/clarification`。Word/PDF等先保留原件并提取可核查文本；不能把二进制文件当文本引用。
2. `analysis`：`id/fact_id`，在`narrative.analysis`声明实际`file/sha256`。程序会重读原始表和合同，重算后与产物逐项对比，不只相信声明哈希。

解释必须有一条`origin=user_supplied|external`的原文来源；`derived`（自己整理/生成）和`synthetic`不能循环支撑解释。只有在顶层`demo: true`的合成演示中，`synthetic`可作为解释来源，并须在页面/说明中保留模拟标识。

## 行动、诉求与逐页闭环

行动含`id/text/finding_ids/owner/due/success_criteria/preconditions/falsifier/side_effects/status`，期限为有效ISO日期，状态`proposed|agreed`。责任建议要标“建议”，不能冒充已分派；`agreed`还须`agreement_evidence_ids`，且引用`origin=user_supplied`、`purpose=approval`的原文，数值事实和普通引用不能证明批准。请求含`id/text/finding_ids/decision_question/options/evidence_needed/status`；`options`至少两项，每项写`text/condition/consequence`，把“可能减亏”“必然翻转”改成有条件的选项，而不是承诺结果。

建议行动/请求用“待确认”及逐条状态表达，由`narrative.actions/requests`投影；不机械添加免责声明、流程箭头或核验卡。行动表列任务、责任、期限、交付结果与实际依赖/影响；完整反证记录保留于提纲和备注。决策卡保留各选项条件、后果及缺少的具体材料，不能因精简而隐去影响决定的风险。

无行动/请求时显式空列表及`actions_none_reason/requests_none_reason`。`coverage`含六个角色，各给`slides:[页号]`；省略则给`slides:[]/skip_reason/evidence_ids`。正文页须接入主线，发现、行动和请求须被页面引用，claim、finding、action、request 均不得留在分析稿之外。

单页除`purpose/title/layout_reason`，必须用`message_claim_id`引用类型化结论；`statement`另需`headline_claim_id/body_finding_ids`，`office_cover`、`closing`、`image`需`headline_claim_id`，页面不得再保留`message`。`closing`正文由所引请求的`decision_question`和状态生成，不再接受手写`body`；无请求时只显示结论句。带`action_ids`/`request_ids`的记录表必须用`office_actions`/`office_review`投影，普通`table`不能复述责任、期限和状态。结构检查只核对闭环；标题是否夸大、引用是否支持结论、未绑定文字数字是否正确，仍须逐条语义核对，并连看整套预览排除实质版式循环。

```console
python -X utf8 scripts/outline.py --input task/deck-plan.json --analysis task/analysis.json --output task/outline.md --plan-output task/prepared-plan.json
python -X utf8 scripts/approve_plan.py --plan task/prepared-plan.json --outline task/outline.md --mode confirmed --quote "用户确认原文" --confirm
python -X utf8 scripts/generate.py --input task/prepared-plan.json --output task/report.pptx
```

`--plan-output`放输入计划同目录以保留相对来源含义，不覆盖已有文件。`approve_plan.py`必须在用户真实审阅提纲后运行，记录计划与提纲哈希；任何改动都会使批准失效，生成器拒绝未批准或已改动的计划。无数值任务省略`--analysis`，仍做主线、证据与批准检查。`examples/operating-review/`与`examples/project-update/`是可跑通的 v1.4 合成示例；`examples/office-layout-showcase.json`只用于看`office_*`构图，没有`narrative`，不能进入生成链路。

### v1.4.1 执行细节

仅有分析事实支撑的finding，其比较基准会与fact_id的目标／环比／同比类型核对；人工填写comparisons不能把环比事实改成预算证据。涉及文字来源的解释及自然语言范围仍需语义审查。

批准器会重建完整审阅提纲并比对，拒绝无关或删节的提纲；生成API的doc也必须等于获批文件。行动按每行中文状态投影，混合状态分别计数。office_review最多3项请求、closing最多2项，超出先拆页，不截断。批准侧车和来源分类仍是执行者记录，无法证明真实对话或源材料真实性，不是身份鉴别机制。
