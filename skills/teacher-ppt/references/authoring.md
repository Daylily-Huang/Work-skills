# 命令与数据字段

Python 3.10+ 标准库用于门禁、PPTX 部件组合和图表工作簿。无需安装 python-pptx、申请 API key 或启动额外模型服务。Windows 上实际渲染另需 PowerPoint 与 PowerShell；未探测到时使用已有的适用渲染器，不把“调用失败”写成“未安装”。

## 最短执行路径

从技能目录运行，任务记录放用户约定的持久目录；本机临时构建和编辑探针放 `D:/_scratch/<日期>-<任务名>/`，不能放技能目录或盘根。

```console
python -X utf8 scripts/teacher_ppt.py init <任务目录>
python -X utf8 scripts/teacher_ppt.py check <任务目录>
python -X utf8 scripts/teacher_ppt.py catalog --query 探究
python -X utf8 scripts/teacher_ppt.py catalog --template T17 --page 3
python -X utf8 scripts/teacher_ppt.py binding <任务目录>
python -X utf8 scripts/teacher_ppt.py record-review <任务目录> --kind content --input <实际内容判断.json>
python -X utf8 scripts/teacher_ppt.py build <任务目录> --scratch <本轮临时目录>
python -X utf8 scripts/teacher_ppt.py render <任务目录> --scratch <本轮临时目录>
python -X utf8 scripts/teacher_ppt.py record-review <任务目录> --kind visual --input <实际视觉判断.json>
python -X utf8 scripts/teacher_ppt.py finalize <任务目录> --output <最终PPTX路径>
```

`check` 只报告当前缺什么，不自动补需求、写教学内容或作出模型判断。`binding` 返回当前需求/计划哈希；它不表示用户已经批准。未请求审批时，无需增加批准步骤。

## brief.json

```json
{
  "schema_version": 1,
  "topic": "课题和范围",
  "audience": "年级与必要的学生基础",
  "purpose": "上新课/复习/习题讲评/说课等实际用途",
  "scope": "full_lesson",
  "extent": {"minutes": 40, "slides": 10},
  "constraints": {"textbook_required": false, "answers": "notes"},
  "required_points": [{"id": "p1", "text": "用户明确要讲的重点"}],
  "sources": [{"id": "s1", "kind": "file", "title": "老师提供的材料", "location": "材料.md"}],
  "ambiguities": [],
  "evidence": {"audience": "实际对话或材料依据"}
}
```

- `scope` 根据任务用 `full_lesson`、`segment` 或 `local_edit`；后者不强迫重新设计整课。“复习、讲评、说课”等课型写在 `purpose`，与整课/片段范围分开。
- `extent.minutes` 和 `extent.slides` 按实际需要填写一个或两个。整节课须有分钟；页数若已明确，脚本按精确页数检查。用户给范围时先在范围内提出合理页数，记录选择依据。
- 必讲点来自真实需求，不自行用默认清单替老师决定。教材对齐时设 `textbook_required: true`，另填 `textbook.edition/volume/unit`；版本、册次和具体范围要清楚。
- 重要歧义形如 `{ "id":"q1", "question":"问题", "impact":"material", "status":"open" }`。真实答复后记录 `status:"answered"`、`answer`、`evidence`；明确授权代选用 `delegated` 并记录授权。不能用空答案、等待超时或自己猜测关闭问题。
- 来源 `kind` 可为 `file`（本地路径会重算哈希）、`url`（记录实际核过的网页和定位/摘录）、`authored`（本任务原创例子/材料，写清内容和性质）。网页验证仍由模型实际执行，脚本不会联网核实 URL。
- 默认教师答案在备注；用户明确不要答案设 `answers:"omit"`。示意数据只在真实授权后设置 `allow_illustrative_data:true`，并在对应页标明“示例”。

## lesson.json

```json
{
  "brief_sha256": "binding命令返回的当前需求哈希",
  "emphasis": {"priorities": ["本课重点"], "sequence_reason": "针对实际学生与课型解释组织方式"},
  "objectives": [{"id": "g1", "text": "学生能完成的具体表现"}],
  "facts": [{"id": "f1", "claim": "实际要讲的关键事实", "source_ids": ["s1"], "verification": {"method": "原文核对/独立计算等", "detail": "具体定位或计算过程"}}],
  "activities": [{"id": "a1", "minutes": 5, "objective_ids": ["g1"], "slide_ids": ["slide1"], "student_action": "学生实际做什么", "evidence": "怎样看出学会了"}],
  "slides": [{
    "id": "slide1", "kind": "question", "intent": "本页教学用途",
    "template": "T17", "template_page": 3,
    "objective_ids": ["g1"], "point_ids": ["p1"], "fact_ids": ["f1"], "source_ids": ["s1"],
    "text": {"title": "换个角度", "text1": "本次真实问题", "text2": "本次材料", "text3": "简短学习提示"},
    "keep_text": {}, "tables": [], "charts": [],
    "teacher_guidance": "教师答案、解题依据或开放题评价要点",
    "teacher_notes": "需要时补充追问或活动组织"
  }]
}
```

例子只说明字段，**不保证字段名与任一具体页一致**。必须先用 `catalog --template ... --page ...` 检查实际字段、表格、图表和 `visual_scene`/`avoid_for`。`catalog` 还会给出各文本框的 `width_pt`、`height_pt`、`max_chars_per_line` 与 `max_lines`，以及已有备注 `notes_text`；填写过长文本时脚本会在 `flags` 中标出 `text_capacity_risk`，应换更宽版式或精简文句。`T01`–`T12` 偏向说课教研（带顶部导航条），`T13`–`T20` 偏向一线课堂教学（含全页插画背景）。每页所有文字都需在 `text` 替换，或在 `keep_text` 以“字段:保留理由”明确保留；保留导航等家具是合理的，不能保留待填提示和超过 12 字的样例段落而不作说明。选择不同版式可调整页面容量；脚本不自动扩表或重排任意复杂对象。

普通页面 `kind` 用 `cover/goal/explain/question/exercise/activity/record/summary/divider` 等清楚名称（已校验 `cover/goal/explain/question/exercise/activity/record/summary/divider/review/edit`）。问题、习题页需要教师指导；封闭题是答案依据，开放题是可接受思路和评价要点。不要把隐藏备注当成学生已看见的内容。

表格按 `catalog` 返回的顺序显式填 `tables:[{"values":[["列1","列2"],["内容","内容"]]}]`，尺寸需一致。图表按返回顺序填：

```json
{"categories":["甲","乙"],"series":[{"name":"实际指标","values":[3,4]}],"source_id":"s1"}
```

系列数须与选定图表一致；分类数可变化。数值写回缓存和嵌入的 XLSX 工作簿。图表关系、单位和结论由模型对照来源核查。示意图表另设 `illustrative:true`，需要需求授权和页上短标记。脚本不从截图猜数值。

自有旧稿用 `source_deck:"实际源PPTX路径", source_slide:2` 替代模板两字段，先运行 `catalog --source-deck <路径> --page 2`；没有 `slot.*` 名称的文字使用 `shape.<对象id>`。计划应列出要保留的所有页面；未列页不会自动加入。`local_edit` 保留未改动页原样与既有备注：若省略 `teacher_notes` 或设置 `"keep_notes": true`，脚本自动保留源页既有备注（并在需要时增量附加 `teacher_guidance` 与 `来源`），避免误清空原备注；同时对二次导入的 `ppt/teacher/...` 共享母版与媒体去重，避免母版/资源膨胀。局部编辑不覆盖原稿；复杂动画、SmartArt 或格式异常应使用原生工具窄改并检查，不把包结构通过当作无损保证。

## 渲染与交付

`render` 在 PowerPoint 中导出逐页 PNG（并以相对路径记入 `render.json`）、检查文字/表格高度溢出，并实际修改文本、表格与（若含原生图表时的）嵌入图表工作簿副本、保存重开验证后自动清理探针文件，`render.json` 中会如实记录 `native_edit_probe` 与 `native_chart_edit_probe`。

没有本机 PowerPoint 时，使用确实可用的 Office/WPS、LibreOffice 或当前环境的演示文稿渲染工具，从**当前候选文件**产出完整逐页图片，再运行：

```console
python -X utf8 scripts/teacher_ppt.py register-render <任务目录> --engine <实际渲染器> --command-used "实际命令或工具调用" --images <第1页图片> <第2页图片>
```

该命令只验证文件/图片存在、页数和哈希绑定，不证明图片忠实于PPT，必须实际看图核对；此路径不声明原生编辑保存通过。没有任何可用渲染方式时停在待审稿，不能伪造渲染记录来正式交付。

`finalize` 会重算来源和模板、计划、候选与渲染图片的当前哈希，再检查两次模型判断。修改任一材料后重新检查相关阶段，不能直接把旧记录绑到新材料。最终 PPTX 与渲染记录对应，源计划和检查记录留在任务目录。

技术限制：本构建器保存原生部件及关联关系，不是任意演示文稿的通用排版引擎；它不会自动保证语义正确、自动生成高质量新构图，或证明学习效果。模板不足时按实际可用专业工具补充，仍遵守本技能的内容/版本/实际渲染边界。
