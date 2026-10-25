---
name: steven-opl
version: 0.2.0
description: 将维修经验、故障判断、易错点、维修窍门或装配注意整理为可追溯的 TPM OPL 一点课；当用户明确说“steven-opl”“按 Steven OPL 流程”，或要求带来源追溯、内容审批和图文排版审批的 OPL 时使用。执行单点范围闸门、动态补问、图片用途确认、raw→draft→approved 内容冻结、render-plan 排版冻结及模板契约校验；标准 Word 模板支持动态教学行和一行多图，培训记录保持空白。
---

# Steven OPL

把用户材料整理为“一张课只讲一个点”的 OPL。事实可追溯，未知不编造；内容和图文映射分别确认后才生成 Word。

## 强制原则

1. 先定单点：仅选故障判断、易错点、维修窍门、装配注意或改善案例中的一个主题；多主题先拆分。
2. 先问图片：按接收顺序编号；先询问每张图是什么、有什么作用，不主动识图/OCR/猜用途。发送顺序不等于作业顺序。
3. 每轮只补 1～3 个关键缺口，不把采集清单机械地当问卷。
4. 事实状态分为 `user_confirmed`、`user_stated`、`assistant_suggested`、`derived`、`unknown`、`conflict`；建议和推测不得写成事实。
5. 内容采用 `raw.json → draft.json → approved.json`；排版采用 `render-plan.json → approved-render-plan.json`。两个批准缺一不可。
6. 内容确认覆盖标题、对象/前提、目标、关键要点、易错点、安全、验收、图片用途、未知与限制；排版确认覆盖每行标题/文字、图片清单和图文对应。
7. 图片原文件不可改；工作副本按 EXIF 规范化为用户原始显示方向，只等比缩放和格式转换，不自动旋转、镜像、裁剪。
8. 模板源文件只读使用；只编辑任务工作副本。失败不得覆盖模板或上一个合格成品。
9. 培训记录表始终保持空白，不填写培训日期、讲师或受培训者。
10. 不把恢复正常自动写成根因已证实，也不把建议、待实施或待验证写成已取得成效。

## 工作流

### 1. 建立任务与采集

为每次任务生成稳定 `task_id`，在 `work/<task_id>/` 保存中间数据和附件工作副本。按 [采集规则](references/collection.md) 采集材料。脚本只能读取显式输入，不能假设自动访问聊天历史。

可将导出的消息和附件规范化为 `raw.json`：

```sh
python3 scripts/ingest_chat.py --input chat.json --task-id <task_id> --output work/<task_id>/raw.json
```

### 2. 单点范围闸门

按 [内容规则](references/content-rules.md) 判断课型和主题。完整维修时间线只作为素材；若不能归纳成一个标题、一个学习目标和一个验收焦点，应选题、拆课或分流到维修记录 Skill。

### 3. 内容草案与来源校验

运行 `scripts/distill.py` 生成无推断骨架，再依据用户材料填写。`source_index` 必须登记消息、附件、图片和规则来源；采用图片必须记录路径、原文件 SHA-256、显示尺寸、用途和确认状态。

```sh
python3 scripts/validate_data.py work/<task_id>/draft.json
```

展示完整内容草案。用户明确批准当前版本后冻结：

```sh
python3 scripts/approve.py --draft work/<task_id>/draft.json \
  --source-ref <approval-message-id> --output work/<task_id>/approved.json
```

### 4. 生成并确认图文排版计划

`approved.json` 只表达“教什么”，不直接决定 Word 格位。先生成 `render-plan.json`：

```sh
python3 scripts/build_render_plan.py --approved work/<task_id>/approved.json \
  --plan-id <plan_id> --output work/<task_id>/render-plan.json
```

检查并向用户展示每个教学行：标题、文字、引用内容、图片编号和图片侧。标准模板允许 1～6 行；一行可放 0～4 张同用途图片：

- 无图行：合并为整行文字；
- 有图行：第 1/3/5 行图片在左，第 2/4/6 行图片在右；
- 超过 6 行时先检查是否已经超出单点范围，不得静默丢内容或图片。

用户确认图文映射后冻结：

```sh
python3 scripts/approve_render_plan.py --plan work/<task_id>/render-plan.json \
  --approved work/<task_id>/approved.json --source-ref <approval-message-id> \
  --output work/<task_id>/approved-render-plan.json
```

内容、图片文件、模板版本或排版计划发生实质变化时，对应批准失效。

### 5. 生成 Word

标准模板位于 `assets/templates/steven-opl-standard/1.1.0/`：

- `source-template.docx`：用户原始空模板，只读留存；
- `template.docx`：生成母版；
- `contract.json`：动态教学行、样式、图片容量和培训记录留空契约。

组别和工序动态填写；模板类别按课型固定映射：故障判断→问题，改善案例→改善案例，其余→基础知识。

```sh
python3 scripts/fill_word_opl.py \
  --approved work/<task_id>/approved.json \
  --plan work/<task_id>/approved-render-plan.json \
  --template assets/templates/steven-opl-standard/1.1.0/template.docx \
  --contract assets/templates/steven-opl-standard/1.1.0/contract.json \
  --output work/<task_id>/candidate.docx \
  --trace work/<task_id>/render-trace.json
```

### 6. 分层验收

运行通用输出校验和模板专用布局校验：

```sh
python3 scripts/validate_output.py \
  --approved work/<task_id>/approved.json \
  --plan work/<task_id>/approved-render-plan.json \
  --contract assets/templates/steven-opl-standard/1.1.0/contract.json \
  --docx work/<task_id>/candidate.docx \
  --trace work/<task_id>/render-trace.json \
  --report work/<task_id>/validation.json
```

报告分别记录内容、结构和视觉状态。未实际渲染预览时，只能标记 `ready_pending_visual_review`，不得声称视觉版面已验收。结构失败时不得移入 `output/`。

## 资源按需读取

- 采集与补问：[collection.md](references/collection.md)
- 内容与事实边界：[content-rules.md](references/content-rules.md)
- 图片处理：[image-rules.md](references/image-rules.md)
- 数据和批准：[schema-common.md](references/schema-common.md)
- 模板契约：[template-contract.md](references/template-contract.md)
- 输出验收：[output-checklist.md](references/output-checklist.md)

## 交付

交付 Word、`approved.json`、`approved-render-plan.json`、渲染追踪和校验报告，并简要列出视觉复核状态与已知限制。不要把维修全过程、工单或 SOP 伪装成一点课。
