<h1 align="center">教学课件 PPT（teacher-ppt）</h1>

<p align="center">
  先澄清关键教学边界，再组织目标、活动与真实材料，最后原生构建并逐页渲染。<br>
  专用于小学、初高中优先、大学兼容的一线课堂教学、复习讲评与说课教研。
</p>

<p align="center">
  <code>v1.0.2 (trial)</code>　·　Python 3.10+ (零第三方依赖)　·　PowerPoint / WPS
</p>

<p align="center">
  <img src="assets/previews/T16.png" width="48%" alt="立体几何课堂（T16）">
  <img src="assets/previews/T19.png" width="48%" alt="珊瑚蓝白讨论（T19）">
</p>

<p align="center">
  <sub>随包 20 套六页轻量自然模板（120 页），全部文字框、原生表格与原生图表工作簿均可在 PowerPoint / WPS 中直接编辑。</sub>
</p>

---

## 模板体系（20 套 · 120 页）

| 分组 | 模板编号 | 定位与结构特点 | 选型与避坑 |
| --- | --- | --- | --- |
| **说课与教研** | `T01`–`T10` | 带顶部说课导航条、三联学情原生图表（`T01`/`T02`/`T06`/`T07`/`T09`/`T10`）、黑板板书框（`T03`）与 7×1 课程表格（`T04`/`T05`） | 适合说课稿、教研汇报与多图表学情分析 |
| **国风语文说课** | `T11`–`T12` | 青绿书卷 / 水墨竹影底图与语文说课导航页 | 适合语文、古诗文、历史与传统文化说课 |
| **一线课堂教学** | `T13`–`T20` | 浅底全幅水彩/纸艺/手绘插画背景，配少字留白文本框与 4×3 原生观察记录表，支持多色封面标题保真 | 选版前须核对 `catalog.json` 中的 `visual_scene` 与 `avoid_for`（例如几何画本 `T17` 不用于纯生活叙事阅读，固定几何教具 `T16` 专用于立体图形主题） |

浏览所有 20 套总览可直接在浏览器打开 [`assets/gallery.html`](assets/gallery.html)。

## 核心工作流与质量门禁

1. **需求澄清门禁（`init` / `check`）**：缺失课时或重要歧义未取得 `answer` + `evidence` 时拒绝进入规划，返回 `needs_clarification`。
2. **目录与容量检视（`catalog`）**：按学段（`小学`/`初中`/`高中`/`大学`）、学科、课型（`新授`/`复习`/`讲评`/`说课`）或组件（`表格`/`图表`）筛选模板，并返回各文本框 `width_pt`、`height_pt`、`max_chars_per_line`、`max_lines` 及现有 `notes_text`。
3. **教学与合规门禁（`binding` / `record-review --kind content`）**：强制必讲点覆盖、活动与目标关联、整节课活动时长不少于半课时、事实来源绑定、问题/习题页 `teacher_guidance`、全库 324 处方括号与非括号占位词拦截，并对相邻/非相邻/交替重复版式、超容风险、混搭超 2 套风格与长原字保留输出提示交由模型裁决。
4. **原生组合与二次改稿（`build`）**：直接拷贝完整 OOXML 关系图保留多色字体、表格与嵌入 XLSX 图表工作簿，并在 `local_edit`（`source_deck`）模式下对嵌套 `ppt/teacher/...` 母版与媒体去重、裁剪孤儿部件，按需保留源页既有教师备注（省略 `teacher_notes` 或设置 `keep_notes: true`）。
5. **实机渲染与编辑探针（`render` / `record-review --kind visual` / `finalize`）**：通过 `scripts/render_powerpoint.ps1` 逐页导出 PNG、检测文本与表格高度溢出，并对文本框、表格与（存在图表时的）内嵌工作簿执行修改—保存—重开可编辑探针，校验视觉检查记录后方允许交付成稿。

## 常用 CLI 命令

本技能全部脚本仅依赖 Python 3.10+ 标准库与 Windows PowerShell（调用本机 PowerPoint 渲染），无需额外安装 pip 依赖：

```console
# 1. 按学段、学科或组件筛选模板，查看单页精确字段与容量
python -B scripts/teacher_ppt.py catalog --query "初中 语文 讨论"
python -B scripts/teacher_ppt.py catalog --template T19 --page 3

# 2. 初始化任务并检查需求澄清状态
python -B scripts/teacher_ppt.py init path/to/job
python -B scripts/teacher_ppt.py check path/to/job

# 3. 绑定内容审查、构建候选 PPTX 并实机渲染检查
python -B scripts/teacher_ppt.py record-review path/to/job --kind content --input path/to/content-review.json
python -B scripts/teacher_ppt.py build path/to/job
python -B scripts/teacher_ppt.py render path/to/job --scratch D:/_scratch/job-render

# 4. 目视确认渲染图后绑定视觉审查并输出终稿
python -B scripts/teacher_ppt.py record-review path/to/job --kind visual --input path/to/visual-review.json
python -B scripts/teacher_ppt.py finalize path/to/job --output path/to/final.pptx
```

更多说明见：[`SKILL.md`](SKILL.md)、[`references/teaching.md`](references/teaching.md)、[`references/authoring.md`](references/authoring.md) 与 [`references/review.md`](references/review.md)。

## 许可与溯源

- 技能脚本与文档遵循仓库根目录 [MIT 协议](../../LICENSE)。
- 随包模板衍生底图、65 项开放 SVG 图标及第三方许可全文逐项记录于 [`references/template-provenance.json`](references/template-provenance.json) 与 [`assets/licenses/`](assets/licenses/)。
