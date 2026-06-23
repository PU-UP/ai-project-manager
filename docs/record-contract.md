# 记录契约（写入与来源）

> **版本：** 1.0.0
>
> **最后更新：** 2026-06-23
>
> **状态：** canonical — 定义什么可以写、什么必须先确认；后续 schema 与 apply 协议以此为准演进。

## 目的

区分 **用户确认信息**、**文档可追溯事实** 和 **Agent 推断**，防止未经验证的内容进入长期档案。

产品边界见 `docs/product-boundary.md`；本文只约束 **Record Mode** 下的写入语义。

---

## 三类信息

### 1. 用户确认（user confirmed）

用户在本轮或既往对话中 **明确陈述或确认** 的内容。

| 属性 | 要求 |
|---|---|
| `source_type` | `user` |
| `confirmation` | `confirmed` |
| `source_ref` | 可选：用户原话摘要、会话引用或事件 ID |

**可写入：** `validated_facts`、用户决定（`project_events` 中 `decision`）、`project_updates` 中用户明确要求的 status 变更。

**示例：** 「我确认暂停 Hermes」「决定把 trip-spark 标为 active」。

### 2. 文档可追溯事实（document traceable）

来自已登记文档、会议纪要、外部资料的可核对摘录。

| 属性 | 要求 |
|---|---|
| `source_type` | `document` 或 `import` |
| `confirmation` | 用户确认摘要后可为 `confirmed`；仅 Agent 整理未用户确认时为 `unconfirmed` |
| `source_ref` | 文档 ID、`source_uri`、标题或版本 |

**可写入：** 事实性摘要、文档元数据；不含 Agent 对路线的评价。

**示例：** 「根据 2026-06-20 会议纪要：预算上限 5 万」— 需用户确认写入摘要。

### 3. Agent 推断（agent inference）

Agent 基于上下文做的解释、归纳、风险提示或建议。

| 属性 | 要求 |
|---|---|
| `confirmation` | 必须为 `unconfirmed` |
| 禁止写入 | `validated_facts`、用户决定、confirmed 状态的长期 memory |

**允许去向：**

- 自然语言回复（Context Mode）
- `open_questions`（以问题形式保留，不写成已证实事实）
- Handoff packet 中的「待外部 Agent 处理」说明

**禁止：** 将推断直接 apply 为 `key_judgements`、风险等级、价值评分或控制动作。

---

## 写入门槛

### 可以写

- 用户明确要求记录，且 Agent 已给出写入摘要并得到确认。
- 内容与用户原话或可追溯文档一致，或用户确认「这样记可以」。
- 普通进展、blocker、note 类 `project_events`（描述发生了什么，非 Agent 价值判断）。
- 项目改名、约束更新、归档（用户明确指令）。

### 必须先确认再写

- 任何进入 `validated_facts` 或等价「已证实事实」字段的条目。
- 任何 `decision` 类用户决定（含 status 变更语义）。
- 从会议纪要/文档整理的批量事实。
- 将 Agent 归纳并入 `project_memory_updates`。

### 不可以写（新协议）

- `system_judgement`（系统级判断、组合建议、top recommendation）。
- `value_score`、自动 `risk_level` 评级。
- `control_action` / `control_action_note`（除非未来 schema 明确为用户字面决定且带来源）。
- `ai_delegation_level`、`human_intervention_level` 等委派建议字段。
- 未确认内容标记为 `confirmed`。

> **过渡期说明：** 旧 payload 与数据库可能仍含上述字段；新 Agent 调用方 **不应** 在新写入中发送它们。Step 3 起从 schema 层解除强制依赖。

---

## 来源与确认字段（目标模型）

后续 Step 6 将在数据模型中落地；Record Mode 应提前遵守：

| 字段 | 含义 |
|---|---|
| `source_type` | `user` \| `document` \| `import` \| `legacy` |
| `source_ref` | 可追溯引用（URI、文档 ID、用户引述） |
| `confirmation` | `confirmed` \| `unconfirmed` \| `legacy` |
| `recorded_at` | 写入时间（系统生成） |

**规则：**

- 新增长期事实与用户决定 **不得省略** `source_type` 与 `confirmation`（schema 落地后由校验强制执行）。
- `legacy` 仅用于历史迁移数据，不得用于新写入伪装确认。

---

## apply payload 结构（Record Mode）

Agent 在 Record Mode 输出 **严格 JSON**，顶层可包含：

- `project_creations` / `project_renames` / `project_updates`
- `project_constraint_updates` / `project_memory_updates`
- `project_events` / `project_deletions`

**不要求、不推荐：**

```json
{
  "system_judgement": { ... }
}
```

若旧工具链仍接受 `system_judgement`，新调用方应省略或传 `null`；普通单事件记录不应触发系统级判断生成。

---

## 快速判定表

| 内容性质 | confirmation | 可进入 validated_facts / decision |
|---|---|---|
| 用户原话「我决定…」 | confirmed | 是 |
| 文档摘录，用户确认摘要 | confirmed | 是 |
| 文档摘录，未确认 | unconfirmed | 否（可进 open_questions 或待确认区） |
| Agent 归纳「这说明…」 | unconfirmed | 否 |
| Agent 风险/价值/优先级判断 | — | 否（不写入；可 Handoff） |
| 历史导入数据 | legacy | 只读展示，不升级为新 confirmed |

---

## 什么可以写、什么必须先确认（FAQ）

**Q：用户说「记一下今天讨论了 X」但没有明确事实？**

A：可写 `project_events` 类型 `note`，summary 描述讨论发生；不要把未定论点写入 `validated_facts`。

**Q：Agent 能否更新 risk_note？**

A：仅当用户提供了具体风险描述并确认写入；Agent 不得自行评级或改写为系统风险等级。

**Q：能否在 apply 里附带「建议继续推进 Y」？**

A：不可以。建议属于 Handoff 或 Context 自然语言，不属于记录契约。

**Q：未知项目名能否自动创建？**

A：不可以。须用户明确确认后使用 `project_creations`。

**Q：删除项目？**

A：默认归档；彻底删除需独立显式确认（后续 Step 3 增加危险操作门槛）。

---

## 相关文档

- 产品边界与三模式：`docs/product-boundary.md`
- 改造路线图：`docs/roadmap-pure-project-manager.md`
