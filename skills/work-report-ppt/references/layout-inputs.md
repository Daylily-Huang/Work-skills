# office_* 按实际内容填写

普通页不再要求 items/steps/metrics/rows/headers/chart 六类占位数据。只提供本构图实际显示的字段；表中字段位于data下，标题及message_claim_id仍在页面层。

| 版式 | 必需字段 |
|---|---|
| office_cover | headline subtitle steps meta items |
| office_summary | metrics chart items |
| office_scorecard | items metrics score_progress headers rows |
| office_gantt | steps schedule milestones progress_label progress |
| office_swimlane | steps items lane_tasks |
| office_milestone | steps items headers rows |
| office_house | headline items footer_message |
| office_wbs | headline items footer_message |
| office_org | headline items footer_message |
| office_six_pillars | headline items footer_message |
| office_resource | headers rows allocation_chart items |
| office_delivery | metrics headers rows donut steps |
| office_customer | items segment_chart headers rows |
| office_risk | matrix_title items headers rows footer_message |
| office_quadrant | matrix_title items headers rows footer_message |
| office_roadmap | periods items roadmap_cells |
| office_sop | steps items headers rows |
| office_portfolio | items project_status |
| office_growth | metrics chart headers rows steps side_metrics |
| office_retention | donut headline subtitle metrics headers rows items |
| office_training | donut headline subtitle metrics headers rows items |
| office_sales | metrics comparison_chart ranking_chart |
| office_finance | metrics waterfall allocation_chart headers rows |
| office_funnel | funnel items headers rows |
| office_channel | ranking_chart headers rows items |
| office_supplychain | items headline |
| office_talent_rings | items talent_nodes |
| office_pyramid | items footer_message pyramid_caption |
| office_tiers | items tier_titles tier_labels footer_message |
| office_wings | headline tier_labels items tier_titles footer_message |
| office_u_stages | items |
| office_value_chain | steps items footer_message |
| office_before_after | compare_titles items |
| office_cycle | items headline |
| office_actions | headers rows |
| office_review | items |

封面例外：blue/red使用items，black使用metrics，不要求另一类占位；headline由headline_claim_id投影。office_actions和office_review的data由行动／请求记录生成，执行者不手写第二份责任、日期和状态。

容量由layout_contract.py校验；超限拆页。已渲染的图表/KPI仍须绑定分析事实，最小字段不等于允许随便填数。部分旧模板计划保留完整演示数据，只作参考，不复制成真实事实。

字体大小：内部Canvas历史size输入采用96dpi像素，落到PowerPoint时最低为实际11pt；表格12pt。最低字号只是技术下限，25分钟投屏等场景仍应加大重点正文，按实际预览取舍与拆页。

## 正文的排版节奏（行距、段距、字号）

`scripts/generate.py` 顶部三个常量决定所有正文的呼吸感，改这两处即可全局调整，不必逐页改坐标：

| 常量 | 当前值 | 含义 |
|---|---|---|
| `BODY_LEADING` | 1.62 | 行高 ÷ 字号。中文低于 1.45 就会显挤，1.6–1.75 是舒适区 |
| `PARA_GAP` | 0.46 | 段后间距 ÷ 字号。多段正文才起作用 |
| `BOX_TOLERANCE` | 6 | 允许的估算误差（像素）；调大会放过临界溢出，调小会误杀 |

`Canvas.text()` 按这三个值同时做两件事：写入 `line_spacing`／`space_after`，并以同一公式校验文本框装不装得下。**两者必须同源**——只改渲染、不改校验，就会出现"生成通过但 PowerPoint 里溢出"；只改校验、不改渲染，就是白白多出空白。

换行估算由 `_char_width()` 和 `_wrapped_lines()` 逐字模拟：CJK 记 1 em，拉丁与数字记 0.56 em。**不要退回"每行字符数 = 宽度 ÷ (字号 × 0.58)"那种平均估法**，它把中文每行容量高估近一倍，校验通过而实际溢出。

正文基准字号（96dpi 像素，乘 0.75 得 pt）：statement 与 metrics 的说明 20、comparison 与 risks 21、timeline 22、closing 23；基础表格 15pt、商业布局表格 13pt。加大正文时同步加大容器高度，或删字拆页，不要靠压字号塞内容。

## 渲染层的分工

版式分两族，但页面家具只有一份实现：

| 文件 | 负责 | 改什么来这里 |
|---|---|---|
| `scripts/chrome.py` | 页眉 `header()`、数据表格 `data_table()` | 改页眉结构、表格样式、单元格边距、行高与容量算法 |
| `scripts/generate.py` | 基础布局（封面、结论、指标、对比、风险、时间线、收尾等）与 `build()` | 改这些版式的内容编排 |
| `scripts/commercial_layouts.py` | 34 类 `office_*` 商业版式 | 改商业模板的图形组织 |

`commercial_layouts.frame()` 和 `table()` 都是对 `chrome.py` 的薄封装，只传字号差异（商业表格 13pt，报告表格 15pt）。**不要在任一布局文件里另写页眉或建表代码**——那正是之前两套实现漂移的原因。改配色仍只动 `assets/palettes.json`，改字体只动计划里的 `font`／`display_font`。

文案呈现见slide-copy.md：行动/请求的固定五步及三张核验卡不再自动生成；显式手写的旧参考版式仍可带可选steps/items。完整前提、反证和来源留在提纲/备注，正文保留真实依赖与风险。
