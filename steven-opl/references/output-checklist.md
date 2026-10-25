# 输出验收清单

## 内容与批准

- `approved.json` 合法，事实均能解析到 `source_index`；
- `approved-render-plan.json` 合法并绑定当前内容散列；
- 无关键冲突、未确认建议或未关闭安全阻塞；
- 模板类别与课型映射一致；
- 图片用途、原文件 SHA-256 和排版映射已确认。

## 文件与模板

- 模板 ID、版本、内容 schema 和 SHA-256 匹配；
- 模板源文件生成前后不变；
- DOCX ZIP 和关键 XML 完整；
- 必填字段存在，无残留占位符；
- 教学行数与排版计划一致；
- 培训记录表无填写内容。

## 图文布局

- 无图行合并为整行文字；
- 有图行按左、右交替；
- 每行图片数量与计划完全一致；
- 标题和正文与计划一致；
- 所有教学行含 `cantSplit`，高度符合契约；
- 渲染追踪中的原图散列与批准数据一致；
- 每个工作副本散列能在 DOCX 媒体中找到。

## 分层状态

报告分别输出：

- `content_validation`；
- `structure_validation`；
- `visual_validation`；
- `delivery_status`。

自动结构校验通过但未实际预览时，状态为 `ready_pending_visual_review`；不得表述为视觉版面已验收。任何内容、散列或结构错误均为 `blocked`。
