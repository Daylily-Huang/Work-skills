# 工作汇报的描述性数据分析

对已澄清口径的规范长表做可重复计算，不猜原始表含义，不自动证明原因、显著性、预测或改善动作有效。

## 先明确口径与输入

确认期间是否完整/同观察窗口、定义与方向、范围与单位、唯一粒度、目标依据、能否加总、分子分母及所需比较。任何模糊必须询问并等待答复。去重用户数可能跨地区重复，存量不能跨期随意相加；不能因列都是数字就选`additive`。币种、退款、含税范围、整月对部分月、样本变化都要核实，不自动换算。

原件只读，另存规范分析表。支持显式编码/分隔符的CSV、行对象列表JSON、指定工作表的XLSX。不自动识别宽表、多行合并表头或旧XLS，先按确认的含义整理。XLSX所选字段有公式/错误会拒绝；不能假设缓存新鲜，应确认计算后导出值，不修改用户原工作簿。

合同例子：`examples/operating-review/analysis-contract.json`。字段：

- `design.requirements`为真实严格澄清记录，不复制合成记录处理业务。
- `scope/scope_evidence`与`comparability:{status:confirmed,window_basis,evidence}`明确范围和窗口。程序核对声明和行范围，不能自动证明原始日期或样本完整。
- `periods:{current,previous,year_ago}`给明确标签；不比较时用`null`并在`period_notes`给用户明确的省略依据，不自动猜月份。
- `dimensions`为已确认分组或显式空数组；`row_key`为确认粒度上的唯一键；`coverage_policy:require_same_groups`。重复、缺失、单位/范围冲突、未声明期间、分组覆盖不齐都会阻断，不自动去重、补零、插值或丢行。新增/消失组先核实；用户确认应为零后提供明确零记录。
- `input:{file,format,columns}`映射规范字段到原表。每行有`id/metric/period/unit/scope`及维度；可加总指标有`value`，比率有`numerator/denominator`。CSV给`encoding/delimiter`；XLSX给`sheet/formula_policy:reject`。
- `metrics`给唯一ID、名称、定义及依据、单位、`kind`、`direction:higher|lower|neutral`、目标及依据。无目标用`target:null/target_note`，不能默认0。当前支持`additive`与无量纲分数`ratio`；后者单位为`ratio`，0.30表示30%，并明确`ratio_bounds:zero_to_one|nonnegative`。
- `bridges`可选，用于**目标差距的固定顺序算术桥接**。每项声明`id/result_metric/components`；`result_metric`必须是有目标的可加总指标。组件只支持三种公式：
  - `gap_times_target_rate`：`(driver.current-driver.target) * rate.target`，用于收入规模等“量差×目标率”；
  - `rate_gap_times_current_level`：`(rate.current-rate.target) * level.current`，用于贡献率等“率差×实际规模”；
  - `target_minus_current`：`driver.target-driver.current`，用于费用类反向差距。
  组件`driver_metric/rate_metric/level_metric`必须已在`metrics`声明且有目标。程序检查各组件之和与`result.target_gap`闭合；不闭合即拒绝，不输出部分归因。产出`bridge.<id>.<component>`、`bridge.<id>.gap`、`bridge.<id>.closure`事实。桥接是算术分解，不证明因果；排除性结论必须引用桥接事实。

## 公式与边界

| 分析 | 规则与边界 |
|---|---|
| 汇总 | 可加总值相加；比率为总分子/总分母，不平均百分比；输入负金额保留 |
| 目标差距 | 实际−目标，按高优/低优给还需改善量；低优的实际/目标不能叫达成率，中性指标不代判好坏 |
| 相对变化 | (本期−比较期)/正基数；零/负基数不报普通增长率，保留差额，不静默改除绝对值 |
| 比率变化 | 30%到35%是5个百分点，相对变化约16.67%；不能混用 |
| 比率目标差 | 用`target_gap_percentage_points`等`pp`事实；30%距35%是5个百分点，不是还差5%的相对差 |
| 分组贡献 | 分组变化额/总净变化额，并核对加总闭合；允许负份额及超过100%，净变化为0时份额不可计算；算术构成不证明原因 |
| 目标差距桥接 | 按合同声明顺序计算量差×目标率、率差×实际规模、费用目标−实际；合计必须等于目标差距，残差不为零即阻断；不是因果分解 |
| 比率分组 | 各组按本组分子/分母计算，尚无比率结构/组内效应贡献拆解，组比率差不能直接相加 |
| 无定义项 | `value:null/status:not_computable/reason`，不编成0/无穷，不能绑定成图表数字 |

用Decimal在50位上下文运算，结果为十进制字符串；图表转换为有限浮点数，显示字段按显式小数位四舍五入，保留分析原值。输入仅限支持范围内的规范有限数字，不接收`1,000`、`35%`、币种文本、NaN/Infinity，不自动猜千分位或小数点。

```console
python -X utf8 scripts/analyze.py --config task/analysis-contract.json --output task/analysis.json
```

输出保留源表/合同路径及SHA256、问题、计算事实、原记录ID、公式和分组明细。质量问题保存诊断并退出2，`status:needs_clarification`且无可用事实；只用于向用户解释需要澄清的项。单项数学无定义会明确空值，不冒称算出结果。已有输出不覆盖。

## 从分析绑定到PPT

`outline.py --analysis`绑定结果并输出审阅计划，`generate.py`再制作。每次重读原表与合同重算并对比结果；旧数据、旧目标、篡改结果即使更新声明哈希也拒绝。

```json
[
  {"path":"items.0.value","fact_id":"sales.current","format":"text","decimals":0,"append_unit":true},
  {"path":"items.1.value","fact_id":"sales.actual_to_target","format":"percent","decimals":0},
  {"path":"chart.series.0.values","fact_ids":["sales.previous.region.0.delta","sales.previous.region.1.delta","sales.previous.region.2.delta"],"format":"number"}
]
```

`number`用于图表，`text`用于数字显示，`percent`仅接受`ratio`事实，`pp`仅接受百分点事实。显示格式显式给0–6位小数。目标只允许支持的图表序列、指标值、财务分解/漏斗值及记分卡进度，不执行表达式；重复/重叠绑定拒绝。

已识别图表和KPI必须绑定，不能删绑定后手填模板数值；绘制时按计算结果重新赋值，原计划不改。普通正文、表格文字、图片内数字、甘特日期和其他未接入自绘字段仍须逐项对照原件，不能宣传所有数字自动核实。按信息关系选图表，正负贡献避免饼图；绘图不代替论证。
