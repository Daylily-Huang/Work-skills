# 内容计划与资源选择

`assets/gallery.html` 为新版离线图库，支持场景、配色、模板、素材分层及搜索。旧版已被否定并撤回，新版按用户认可的三个方向重建30套，每套6页、主分析结构各不相同；对应结构化输入在`assets/template-plans/`，详见 @references/commercial-plans.md。颜色不计作新模板，SVG 与原生缓存不重复计数。以下旧版简化字段仍兼容；商业版式使用页面`data`字段。

## 计划字段

顶层：`title`、`tag`、可选 `font`、`design`、`narrative`、`slides`。路径相对于 JSON 所在目录。先澄清需求、确定方案，再组织汇报主线和数据分析、编制逐页计划；不再要求查设计网站或生图。主线/证据/行动结构见 @references/report-logic.md，数据合同与数值绑定见 @references/data-analysis.md。

`design.selection`：`scenario`、`palette`、`template`、`assets`。场景 ID 为 `business/proposal/training/research/marketing/project`；配色 `P1`–`P10`；整套模板 `T01`–`T30`；素材为目录中的实际 ID，无需素材时使用空数组。注意：生成器不打开 `templates/Txx.pptx`，模板选择只决定样式族和参考版式；30套是参考样例，不等于30种独立可生成设计。

`design.requirements`：`status: clarified`、`open_questions: []`、`conflicts: []`；`brief`和`evidence`分别包含`purpose/audience/duration_or_pages/key_message/source_scope/content_constraints/design_constraints`七个非空字符串字段，记录明确需求及真实对话／用户文件依据。无时长限制、不用素材、允许代选等也需有用户实际表述或明确资料依据，不能填默认值假装澄清。任何其他模糊项也必须放入`open_questions`，不以七个字段齐全掩盖未决问题。已解决问题可记入`resolved_questions: [{question,answer,evidence}]`，每项都必须有真实回答；缺失、冲突、未答复时先问用户并等待，草稿也不放行。脚本不能从自然语言中穷尽发现歧义，也不能证明记录真实，执行者必须核对对话。

不再需要`design.references`或`design.preview`；旧计划若保留这些历史字段，不参与放行。

`design.approval`：`mode: confirmed|delegated`、实际用户选择或委托原文`evidence`、`fields: [scenario,palette,template,assets]`。澄清时已明确的选择／委托直接沿用，不再等待额外小样批准。设计代选不能替代事实需求的澄清。程序只能检查记录完整，真实性由执行者据对话核实。

`plan_approval`不是计划里的字段，而是`prepared-plan.json.approval.json`旁车文件：用户实际审阅`outline.md`后运行`approve_plan.py`，记录`mode/evidence/plan_sha256/slide_count/reviewed_outline`。生成器强制校验该文件；计划或提纲任何改动都会使批准失效。不得把“没有反对”写成批准。

单页必填`layout`、`title`、`purpose`（该页用途）、`message_claim_id`（引用`narrative.claims`中的类型化核心信息）、`layout_reason`（此构图如何表达信息关系）；再用`finding_ids/action_ids/request_ids/evidence_ids`接入主线，定量页用`analysis_bindings`绑定实际计算。**页面不得再写`message`字段**：核心信息只维护一份，修改请改被引用的claim。`statement`另需`headline_claim_id`和`body_finding_ids`，正文由发现的文本、适用边界和验证方式拼接；`office_cover`需`headline_claim_id`，封面主结论由claim投影。`sources`为来源文字数组。用途、信息和理由用于逐页计划，不会自动挤进正文；渲染内容仍由相应版式字段提供。常见字段：

- `cover`：`subtitle`、`meta`。`statement`、`closing`、`image`、`office_cover` 的结论句不再手写：`statement`/`closing`/`image` 用 `headline_claim_id` 取 `narrative.claims`，`office_cover` 取到 `data.headline`；`closing` 正文由所引请求的 `decision_question` 与状态生成，不要再写 `body`。
- 多数信息结构：`items: [{title,body}]`。指标和报价可加 `value`；指标用 2–4 项，比较恰好两项，矩阵/SWOT 恰好四项，案例和知识示范三项。
- `bar/line`：`chart: {categories:[...],series:[{name,values:[...]}]}`；另有 `insight`、`unit`。必须有真实源数据，示例数不能进入正式业务稿。
- `table`：`columns`、`rows`、`note`；当前固定布局支持 2–6 列、1–7 数据行，单元格按 12pt 估行，装不下直接报错。只放普通数据表：带 `action_ids`/`request_ids` 的记录表必须改用 `office_actions`/`office_review`，由记录投影，不能在页面重写责任、期限和状态。
- `image`：`image`、`caption`、`body`；图片保持比例。`gallery.items` 各加 `image`；缺图只允许标明位置的模板草稿。
- `quote`：`quote`、`attribution`；引文必须有来源。
- 原生素材：`assets: [{id,box:[x,y,w,h]}]`，画布为 1280×720。先规划空位，不能覆盖文字和证据图；必须有对应原生缓存。

文本过长时生成器报错，改内容结构或拆页。它不做视觉意义上的自动优化，也不承诺保留第三方复杂母版。完整参数示例在 `examples/operating-review/deck-plan.json`。

## 禁止循环版式

字体、主色和网格可以统一，内容构图必须逐页服务于叙事，不能固定轮播三四种模板。`plan_gate.py`检查逐页计划；正文页同一构图连续三次，或2至4种构图按相同顺序连续重复两轮，会拒绝生成。检查时跳过封面、章节与结束页，跨章节插页也不能绕过；实际共用构图的`agenda/contents`、`swot/matrix`、`line/bar`按同类处理。规则不会要求每页完全不同；两页确有比较关系可沿用结构，仍须有独立内容计划。它只拦截明显循环，不能判断所有换色或图片变化是否具有真实设计差异，整套预览必须人工核查。

## 图库与许可

素材目录逐项含原始 SVG、来源 URL、固定提交、作者、许可证与 SHA256；原生缓存额外记录 DrawingML 的哈希。素材计数按唯一 ID 和独立 SVG 字节，不能把颜色变化或缓存重复计入。

参考资源来自用户指定 editable-research-ppt 的许可允许部分；保留 `reference-MIT-LICENSE.txt`、`reference-third-party-notices.md` 和素材各自许可。新增办公素材使用同一固定版本的 Lucide 原始 SVG。原生缓存是历史参考，不保证每个图在每种软件中均已测试。
