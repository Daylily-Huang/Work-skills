# 实际判断与版本绑定

内容判断在构建前完成，视觉判断在看过实际候选渲染后完成。执行模型自己判断即可，普通课件不要求额外多代理。脚本不会调用模型或代填通过结果，也不能证明填写记录的人确实做过判断。

## 内容判断

重新读 `brief.json`、本课材料和 `lesson.json`。逐项用当前页面/题目/来源说明理由；有问题先修计划，再记录。

```json
{
  "reviewer": "model",
  "checks": {
    "focus_and_sequence": {"status": "pass", "reason": "说明本次重点和组织理由，并指出对应页面。"},
    "age_and_teaching": {"status": "pass", "reason": "核对学生基础、目标、活动和评价。"},
    "facts_and_answers": {"status": "pass", "reason": "指出实际核过的来源、计算或开放题判断依据。"},
    "language": {"status": "pass", "reason": "逐页检查短文字、明确判断及防御性/套话。"}
  },
  "flag_decisions": {},
  "findings": []
}
```

上面是字段说明，**不是可直接沿用的通过结论**。实际状态可为 `pass`、`needs_revision`、`not_applicable`；不适用必须说明原因。`binding` 命令返回的 `flags` 若非空，在 `flag_decisions` 中按提示 id 写具体判断和处理（例如 `defensive_copy`、`repeated_layout`（含相邻重复、非相邻重复及交替凑页）、`kept_long_template_text`、`text_capacity_risk`、`mixed_styles`）。语境合理的引用、同构练习可保留，长原文字或容量风险须结合渲染图核实是否截断或未改；不要为了消除提示改坏教学内容。

```console
python -X utf8 scripts/teacher_ppt.py record-review <任务目录> --kind content --input <实际内容判断.json>
```

命令只把已填写的判断绑定到当前需求、计划、来源文件和模板哈希。任何一项变化都会使旧记录失效。不能拿旧结论重新绑定新稿，而不检查变更影响。

## 视觉判断

实际看完逐页渲染与全稿缩略图，并读回文字/表格/图表对照计划。检查留白是否有效、图像是否自然、正文是否被图片或形状压住、标签是否越界、是否无意义重复。实际编辑后保存并重开可以支持对应对象的可编辑性声明，不等于所有软件都已验证。

视觉记录同样有 `reviewer`、`checks`、`findings`，`checks` 的键为：

- `readability_and_space`：字号、行距、换行、留白、遮挡。
- `illustration_integration`：边缘、底色、比例、位置、风格和图文联系。
- `layout_variety`：按内容组织、整体节奏、合理重复。
- `content_matches_plan`：实际文件没有漏内容、旧样例或错误图表。

每项填写 `status` 和对应页面的 `reason`，用 `record-review --kind visual` 绑定候选文件与逐页图片哈希。阻断项 `findings` 用 `severity: "blocking"`，解决后填 `status: "resolved"` 并说明修复；缺证不能写通过。改过候选文件必须重新渲染相关版本。

`finalize` 只做本地文件交付检查；不会联网发布、发送消息或授予其他权限。
