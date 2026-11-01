---

name: "work-report-ppt"

display_name: "工作汇报 PPT"

description: "把工作资料和数据组织成可编辑汇报PPT：严格澄清需求，核对口径、计算差距与变化，分开事实和假说，形成证据、行动及决策诉求，再逐页设计；严禁循环少量版式。"

description_zh: "严格澄清需求，组织汇报主线与证据、计算差距与变化、绑定分析数值后制作可编辑PPT；禁止循环版式。"

description_en: "Create editable work reports with clarified requirements, evidence-linked findings and actions, descriptive data analysis, and computed slide values; never recycle a small layout sequence."

version: "1.4.2"

author: "workskill contributors"

---

# 工作汇报 PPT

面向 WorkBuddy 工作用户。交付可打开、可编辑的 PPTX 与同版本预览，不能用提纲或整页贴图代替成品。资源入口是 `assets/gallery.html`；模板目录与输入说明见 @references/authoring.md。

**当前版本：v1.4.2。严格澄清需求 → 确定方案 → 组织汇报主线与数据分析 → 逐页计划并记录真实确认 → 制作 → 验收。v1.4 把结论的比较基准、范围、强度和前提写成结构化字段，页面消息必须从 `narrative.claims` 投影；行动与请求带前提、反例和备选；证据区分用户材料、外部材料、派生材料和模拟材料；生成前校验已审核计划的哈希；中文字体同时写入 latin/ea/cs，模拟声明对所有版式统一落页。保留30套参考模板、10配色与662项素材，禁止循环拼稿。客户端模型调用仍需单独验证。**

## 从澄清到逐页计划

1. **需求澄清是严格门禁。** 读取用户资料和已有稿，明确用途、受众、演讲时长／页数范围、核心结论、资料范围、内容限制和设计约束。已有信息直接沿用；任何模糊、缺失、矛盾或多种解释都必须向用户询问并等待明确答复，不论你认为影响大小。未答复前停留在澄清阶段，不擅自假设、默认、代填、写逐页计划或生成PPT；`--draft`也不能绕过。记录问题、真实回答与依据，不能把沉默或等待时间当作确认。保持旧稿和公司模板中的用户修改，局部修改不重做整稿。

2. **全部澄清后直接确定方案：场景 → 配色 → 基础模板／填充风格 → 素材。** 按已明确需求使用离线图库和用户资料；六场景、十配色、三十套六页模板、三十四类原生版式及通用／常用／特定素材供选择。用户已明确选择或委托你选择的部分不重复问，也不另加生图确认环节。授权代选只适用于已明确的设计选择，不能替代对用途、数据或结论歧义的询问。没有相关素材时可明确不使用。查网站、生图均不作为制作前置条件；只有用户另行要求时才执行，方法见 @references/design-references.md。

3. **先组织汇报主线和证据。** 围绕听众问题与希望支持的决定，选择目标、结果、差距、解释证据、行动和资源/决策请求；可合并或明确说明不适用，不固定成六页。发现分观察事实、待验证假说和材料支持的解释，并声明比较基准（预算/环比/同比/水平）与适用范围；页面核心信息必须引用 `narrative.claims` 的类型化结论，不能再写一份自由摘要。行动须有前提、反例和副作用；请求须有决策问题、至少两个选项及各自条件与后果。方法和字段见 @references/report-logic.md。
4. **有数据先核口径再计算。** 明确期间、单位、范围、指标定义、分母和唯一粒度，任何歧义必须先询问。按 @references/data-analysis.md 使用`analyze.py`计算目标差距、同比/环比、分组变化贡献和加权比率；需要做预算缺口归因时，先在合同声明固定顺序的目标差距桥接，桥接不闭合就拒绝出稿。数据质量阻断先解决，未计算或未支持的结论不填进模板。无数据的事实型进展按原始记录组织，不强塞指标。按实际版式只填写会显示的字段，不为通过校验编造无用图表和KPI；字段表见 @references/layout-inputs.md。
5. **逐页制定计划并记录真实确认后再制作。** 每页写明用途、一个核心信息（`message_claim_id`）、版式及选择理由、素材和来源。整套配色、字体、网格保持一致；每页构图根据实际信息关系选择。提纲必须由当前计划生成，包含实际页面内容、绑定数值、行动前提／反证／副作用及请求的备选方案；不能拿无关短文充当已审提纲。用户实际审阅提纲后，用`approve_plan.py`记录确认原文、计划哈希、页数和提纲哈希；计划任何改动都会使批准失效。模板只作基础样式与组件来源，不能按固定页序循环复制。

**禁止循环模板：** 不得反复循环三四种版式拼满全稿，也不得只改标题、颜色、图片或数据就称为新设计。相邻页面和跨章节都要检查；插入章节页不能掩盖重复。确需连续展示同类数据时，根据比较、趋势、分解、证据等叙事关系重组页面，保持比较口径一致；不为凑数量生硬换花样。脚本拒绝明显循环，但改名、换色后仍实质同构的页面须在逐页及整套预览中人工核查，不能以脚本通过代替。

## 制作

**页面文案按 @references/slide-copy.md 写成业务汇报。** 标题说具体结果、问题或安排；正文用对象、事实和常用动词，删掉无信息的口号，不为凑三栏五步加内容。不要把内部核验过程和“不能保证／不构成因果／前提未核实前不执行”等固定自证段落放进正文。假说、待确认状态和会改变判断的范围条件必须简短说清；决策页保留实际条件、成本和风险，不能为自然语气改成无条件承诺。完整引用、验证方法、一般前提与反证留在提纲和演讲者备注。模拟声明与必要许可不删。出稿前逐句检查，脚本只约束固定投影行为，不保证全部文案没有AI味。

- 提供的新材料、关键原图和真实数据优先。标题、正文、自制流程和有数据支持的图表采用原生对象；图片内部文字和曲线不宣称可编辑。原图保留比例、单位、图例和含义，不能凭截图猜数据重画。

- 中文标题自然表达，用信息密度、图形关系、比例、对齐和排印形成层级。配色从用户参考中提取，再按可读性调整。渐变、阴影、立体台座、圆环、色块和卡片均可按参考与内容使用，不一概排斥，也不无关堆砌。不能把同一三栏结构换色当作三十套设计。

- `templates/T01.pptx` 到 `T30.pptx` 是新版六页合成参考模板，覆盖六类场景与30种不同主分析结构。**生成器实际不打开这些 pptx**：模板选择只决定三种样式族（`blue/black/red-commercial`）和参考版式，30套文件提供可查看的样例与组件来源，不代表30种可独立生成的视觉设计。按内容选页、组合和调整，不强制用完六页，不循环整套或其中三四页；所有示例数字与业务文字需要替换。蓝白甘特／泳道、黑红组合图表／看板、红金分层平台等字段与方法见 @references/commercial-plans.md。

- 素材先检索 `assets/media-library/catalog.json` 和图库，记录所用 ID 与许可；相关性不足再联网补充。通用／常用／特定是检索分层，不是科学证据等级。CC BY 素材保留可见署名；不能只靠隐藏备注。

- 生成器适合从内容计划新建原生文件；任意旧 PPT 的复杂图表、动画、SmartArt、公司母版修订应通过可用的原生 Office/WPS 工具做窄改并重开验证，不能假称本脚本可无损导入所有模板。

从本技能目录运行（先探测 Python 和依赖，确实缺失时才在明确的本地环境安装 `requirements.txt`）：

```console

python -X utf8 scripts/environment.py

python -X utf8 scripts/design_gate.py task/design-selection.json
python -X utf8 scripts/analyze.py --config task/analysis-contract.json --output task/analysis.json

python -X utf8 scripts/outline.py --input task/deck-plan.json --analysis task/analysis.json --output task/outline.md --plan-output task/prepared-plan.json

python -X utf8 scripts/approve_plan.py --plan task/prepared-plan.json --outline task/outline.md --mode confirmed --quote "用户确认原文" --confirm

python -X utf8 scripts/generate.py --input task/prepared-plan.json --output output/my-presentation.pptx

python -X utf8 scripts/audit.py output/my-presentation.pptx --expected-font "Microsoft YaHei" --disclosure "模拟数据"

```

先将所需示例复制到明确的任务目录，再替换为真实资料与对话依据；上面`task/`是任务路径，不是随包业务数据。无定量数据时省略`analyze.py`及`--analysis`，仍运行主线与证据检查。`examples/operating-review/`和`examples/project-update/`为明确标注的合成演示，真实业务不得沿用它们的澄清/授权记录。

`examples/design-selection.json` 是待澄清的字段示例，必须换成真实需求、依据及方案记录，无需网站或生图字段。`examples/operating-review/`与`examples/project-update/`已是 v1.4 结构，可按上面命令直接跑通（前者需先用本目录 `analysis-contract.json` 生成 `analysis.json`，再以 `--analysis` 绑定）；它们仍是合成数据，只作结构与写法参考。`examples/office-layout-showcase.json` 是六页共用一组数据的版式样张，只用于看 `office_*` 构图，没有 `narrative`，不能通过提纲或生成门禁。正式稿和`--draft`都检查需求、逐页计划与计划批准，草稿标记不能绕过门禁；字段和检查范围见 @references/authoring.md。

原生素材可由页面 `assets` 字段插入，或单独运行：

```console

python -X utf8 scripts/assets.py search 项目

python -X utf8 scripts/assets.py insert --source output/base.pptx --config placements.json --output output/with-assets.pptx --report output/insert-report.json

```

有原生缓存的素材可以作为原生组插入。缓存的历史逐项编辑标记来自参考库，不等于本次 WorkBuddy 验收。其余 SVG 用原件或明确的 PNG 后备，不能称为内部可编辑。新素材与整套稿必须按实际工具验证。

## 检查与交付

1. 核对需求是否确实全部澄清、汇报主线、事实与假说、行动状态、逐页计划、内容、数字、单位、来源及选定方案；绑定过的图表/指标取值来自重新核算的分析结果，未绑定的正文数字及自然语言结论仍须逐项对照。检查整套缩略图与逐页预览，排除少量版式循环和换色伪装。自动门禁只检查记录及明显重复，自动审计只检查结构和越界，都不证明事实或语义正确。

2. 实际打开 PPTX 并渲染逐页检查字号、换行、图表、留白、对齐和素材比例；有 PowerPoint 时可用随包 `render_powerpoint.ps1 -ExpectedFont "Microsoft YaHei"`。字体分标题/正文两款时传逗号分隔列表（如 `"Noto Sans SC,Noto Serif SC"`）。生成阶段报文本超框时，先用 `PPT_TEXT_REPORT=1 python scripts/generate.py ...` 一次列出全部超框位置再统一改，不要逐个试错。`quality_ok` 只是技术完整性（能打开、无溢出、无低于11pt正文/12pt表格、编辑保存通过），不是视觉或语义通过；报告的 `technical_integrity_ok`、`presentation_quality_ok` 与 `semantic_validation=not_performed` 必须分开表述；其中 `presentation_quality_ok` 只代表字号、字体及几何检查，视觉判断仍须逐页目视，不能等同设计认可。修改后以最终文件重新检查，不复用旧版本预览。

3. 对代表页做编辑、保存、重开：文字、形状和图表可编辑才写相应结论。脚本审计不能代替这一检查。

4. 交付 PPTX、必要预览与源计划。没有渲染环境时标“视觉未验证”，不声称跨 Windows/WPS/macOS 一致。

5. 只清理本次生成的中间稿、失败渲染和临时 profile；保留用户资料、选定素材、提示词、来源、成品和必要验证证据。所有临时目录显式放在本任务指定文件夹内，不写盘根。

