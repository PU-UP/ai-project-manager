# Roadmap：将 AI 项目管家收敛为纯项目经理

> 状态：Step 0–10 全部完成；v1.0.2 已通过最终独立验收
>
> 创建日期：2026-06-23
>
> 完成日期：2026-06-23
>
> 最终验收版本：v1.0.2（包含 `45c2492` 后的 Issue 10.6 修复）
>
> 目标角色：项目档案管理员 + 上下文编排器 + 轻量会议秘书
>
> 非目标：独立项目中的深度分析、内容迭代、优先级判断、路线选择和决策

## Builder 使用规则

- [ ] 严格按 Step 0 → Step 9 执行；除非本 Roadmap 明确允许，不要跨 Step 扩大范围。
- [ ] 开始一个 Step 前，确认其“前置条件”全部满足。
- [ ] 只修改该 Step 列出的文件或同一调用链中不可避免的文件；发现旁支问题时记录到本文“发现的问题”，不要顺手扩修。
- [ ] 每个 Step 完成后运行其“验收命令”，勾选 Todo 和完成定义。
- [ ] 每个 Step 建议形成一个独立 commit，保持可回滚检查点。
- [ ] 不重写现有两个本地 commit；从当前 HEAD 追加纠偏 commit。
- [ ] 不写项目数据库业务记录，不修改用户现有项目内容。
- [ ] 数据迁移遵循：停止新写入 → 兼容旧读取 → UI 降级 → 最后清理 legacy 字段。
- [ ] 不引入 Make、容器、多 Agent 编排、向量数据库或新的任务框架。

## 最终产品契约

### 允许能力

- [ ] 维护项目档案、用户确认的事实、用户决定、开放问题和项目约束。
- [ ] 登记、分类、关联和归档文档，生成事实性摘要。
- [ ] 导出项目上下文包和确定性的组合概览。
- [ ] 复述当前记录，指出缺失、冲突、过期项，并提出最多 1–3 个澄清问题。
- [ ] 仅在用户明确要求或确认具体写入摘要后写入。
- [ ] 遇到深度任务时生成 context packet 并交接给通用或领域 Agent。

### 禁止能力

- [ ] 不替项目做研究、方案设计、复杂分析或持续内容迭代。
- [ ] 不主动判断项目价值、优先级、风险等级、暂停/继续/转向。
- [ ] 不替用户做资源分配、路线选择或最终决策。
- [ ] 不产生自主研究—评估—迭代循环。
- [ ] 不把 Agent 推断保存成用户确认的事实或决定。

### 目标运行模式

- **Context Mode**：默认只读；恢复、整理、复述、提示缺口。
- **Record Mode**：显式写入；只保存有来源且已确认的信息。
- **Handoff Mode**：超出边界；输出上下文包后停止，不继续深度执行。

---

## Step 0：建立安全基线与执行检查点

**优先级：P0**

**目标：** 确认当前工程可运行，保护用户数据，并为后续 builder 提供可重复基线。

### 前置条件

- [x] 工作目录为仓库根目录。
- [x] 已阅读 `AGENTS.md`、`skills/project-manager-upgrader/SKILL.md` 和本 Roadmap。
- [x] 已确认工作区没有与本 Step 冲突的用户修改。

### Todo

- [x] 运行 `git status --short`，把起始状态记录到本 Roadmap 的“执行记录”。
- [x] 运行 `uv run python -m compileall app`。
- [x] 运行 `node --check app/static/app.js`。
- [x] 运行 `uv run python -m app.agent_tools doctor`。
- [x] 运行 `uv run python -m app.agent_tools feedback-report`。
- [x] 运行 `uv run python -m app.agent_tools export --brief`，确认现有数据可读。
- [x] 识别实际 SQLite 文件位置，在 `.agent-workspace/backups/` 创建迁移前备份；不得纳入 Git。
- [x] 在“执行记录”中填写命令结果、数据库备份位置和发现的问题。

### 完成定义

- [x] 所有基线命令通过，或失败项已明确记录且不会影响下一 Step。
- [x] 现有项目数据有可恢复备份。
- [x] 未修改任何项目业务数据。

### 建议 commit

本 Step 默认不产生 commit；若只补充 Roadmap 执行记录，可与 Step 1 一起提交。

---

## Step 1：建立唯一产品边界源

**优先级：P0**

**目标：** 用一个 canonical contract 固定“纯项目经理”人格，停止四处复制产品规则。

### 前置条件

- [x] Step 0 完成。

### 主要文件

- 新增 `docs/product-boundary.md`
- 新增 `docs/record-contract.md`
- 后续 Step 再精简 `AGENTS.md`、README、runtime skill 和 system prompt

### Todo

- [x] 在 `docs/product-boundary.md` 写明允许能力、禁止能力、三种运行模式和停止条件。
- [x] 为浅沟通写允许示例：复述、澄清、缺口提示、中性选项整理。
- [x] 为越界请求写禁止示例：深度研究、方案迭代、替用户选择、项目执行。
- [x] 明确 Handoff 输出字段：目标、约束、已确认事实、用户决定、相关文档、开放问题、请求任务。
- [x] 在 `docs/record-contract.md` 定义“用户确认”“文档可追溯事实”“Agent 推断”的写入差异。
- [x] 明确所有新事实和决定必须具有来源与确认状态。
- [x] 明确 `system_judgement`、价值评分、控制建议不属于新写入协议。
- [x] 在两个文档顶部加入版本号和最后更新时间。

### 验收

- [x] 新 Agent 只阅读 `product-boundary.md` 即可正确区分 Context / Record / Handoff。
- [x] 文档不授权分析、规划、优先级、风险评估或建议路线。
- [x] `record-contract.md` 能回答“什么可以写、什么必须先确认”。

### 验收命令

```powershell
rg -n "Context Mode|Record Mode|Handoff Mode|非目标|停止条件" docs/product-boundary.md
rg -n "source|confirmation|system_judgement" docs/record-contract.md
git diff --check
```

### 建议 commit

`docs: define pure project-manager boundary`

---

## Step 2：添加产品边界契约测试

**优先级：P0**

**目标：** 在改 Prompt 和 Schema 前，先让偏航能够机械失败。

### 前置条件

- [x] Step 1 完成并已形成 commit。

### 主要文件

- 新增 `tests/`
- 可新增最小测试依赖配置，但不得引入大型测试框架之外的新运行时

### Todo

- [x] 为 intent matrix 建立结构化 fixture。
- [x] 添加用例：“X 项目现在记录了什么” → Context。
- [x] 添加用例：“把这段会议纪要整理到 X 项目” → Record/organize。
- [x] 添加用例：“深入研究并决定 X 的路线” → Handoff。
- [x] 添加用例：“反复迭代方案直到最好” → Handoff。
- [x] 添加用例：“记录这个用户决定” → Record，且不要求系统判断。
- [x] 添加 schema 测试：只包含一个 project event 的 payload 可以校验成功。
- [x] 添加安全测试：未知项目不会自动创建。
- [x] 添加安全测试：未确认内容不能进入 confirmed facts/user decisions。
- [x] 添加安全测试：彻底删除需要独立显式确认标记。
- [x] 测试失败信息必须告诉 builder 应修改哪个契约或入口。

### 完成定义

- [x] 测试覆盖三种模式的典型请求。
- [x] 测试覆盖无 judgement 写入和来源确认边界。
- [x] 当前尚未纠偏的实现允许出现预期失败，但失败清单必须记录；不要为了全绿削弱断言。

### 验收命令

```powershell
uv run pytest -q
```

### 建议 commit

`test: lock pure project-manager behavior contract`

---

## Step 3：解除写入协议对系统判断的强制依赖

**优先级：P0**

**目标：** 让“记录事实”不再结构性地产生项目判断和控制建议。

### 前置条件

- [x] Step 2 契约测试已存在。
- [x] 已确认旧数据备份可恢复。

### 主要文件

- `app/schemas.py`
- `app/services/control_parser.py`
- `app/services/apply_control.py`
- `app/services/interaction_log.py`
- `app/services/episode_log.py`
- `app/agent_tools.py`

### Todo

- [x] 将 `ControlResponse.system_judgement` 改为过渡期 optional，默认 `None`。
- [x] 普通 apply payload 不再需要 `SystemJudgement`。
- [x] apply 返回中新增或统一中性 `change_summary`，不生成推荐。
- [x] 日志允许 `system_judgement = null`，继续兼容读取旧记录。
- [x] episode 不再要求 judgement summary。
- [x] 保留旧 payload 的解析兼容，但不要求新调用方继续发送 judgement。
- [x] 为 delete 增加独立显式确认字段或危险操作入口。
- [x] 更新 schema 测试并确保无 judgement 写入通过。
- [x] 不在本 Step 删除数据库旧列。

### 完成定义

- [x] 单事件 payload 无 system judgement 可成功 apply。
- [x] 旧 payload 仍可读取和应用。
- [x] 新日志不会凭空生成判断。
- [x] delete 不能由普通、模糊 payload 触发。

### 验收命令

```powershell
uv run pytest -q
uv run python -m compileall app
uv run python -m app.agent_tools doctor
git diff --check
```

### 建议 commit

`refactor: decouple records from system judgement`

---

## Step 4：重写 Agent 行为入口并移除 Work Mode

**优先级：P0**

**目标：** 让所有外部 Agent 从入口处获得同一套克制边界。

### 前置条件

- [x] Step 3 完成且契约测试通过。

### 主要文件

- `AGENTS.md`
- `README.md`
- `skills/project-manager-runtime/SKILL.md`
- `app/prompts/project_control_panel.md`
- `app/services/apply_control.py`
- `app/__init__.py`
- 必要时同步版本文件

### Todo

- [x] 删除 Work Mode 及其 analysis/review/synthesis/planning/prioritization/risk assessment 授权。
- [x] 只保留 Context / Record / Handoff 三模式。
- [x] 把“参与项目工作”“方向判断”“提出建议”改为恢复、整理、复述、澄清和交接。
- [x] 把“我对这次输入的判断”改为“当前记录摘要/信息缺口”。
- [x] Prompt 不再要求 real progress、pseudo progress、AI delegation 或 top recommendation。
- [x] 删除全局 Prompt 内项目特例；项目级规则从 constraint/context 读取。
- [x] `AGENTS.md` 精简为命令优先入口，并链接 canonical boundary/record contract。
- [x] README 面向人描述用途，不重复完整运行协议。
- [x] runtime skill 只保留触发、操作步骤、写入门槛和 Handoff。
- [x] 修正 `build_context()` 的 `runtime.role`、`principle` 和 `agent_operations`。
- [x] 更新版本时同步 `pyproject.toml`、`uv.lock`、runtime skill 和 usage script。
- [x] 运行 intent matrix；深度请求必须进入 Handoff。

### 完成定义

- [x] 四个知识入口都链接同一个产品边界源。
- [x] runtime 中不存在默认深度项目思考能力。
- [x] Handoff 会输出上下文包后停止。
- [x] 新 Agent 不需要读取重复、冲突的规则。

### 验收命令

```powershell
rg -n "Work Mode|planning|prioritization|risk assessment|方向判断|参与项目工作" AGENTS.md README.md skills/project-manager-runtime/SKILL.md app/prompts/project_control_panel.md
uv run pytest -q
uv run python -m compileall app
uv run python -m app.agent_tools doctor
git diff --check
```

预期：第一条搜索不应发现授权性表达；若为非目标说明，人工确认语义后记录。

### 建议 commit

`refactor: enforce context record and handoff modes`

---

## Step 5：用确定性上下文快照替代系统判断 UI

**优先级：P0**

**目标：** 页面只展示可由数据确定的状态，不把 Agent 建议包装成事实。

### 前置条件

- [x] Step 4 完成。

### 主要文件

- `app/services/control_analyzer.py`（可重命名或替换）
- `app/main.py`
- `app/templates/index.html`
- `app/templates/project.html`
- `app/templates/macros.html`
- `app/static/app.js`
- `app/static/style.css`

### Todo

- [x] 首页移除 `top_control_recommendation`、真实/伪进展、AI 委派和人工介入建议。
- [x] 项目详情不再突出 control action 和 Agent 风险评级。
- [x] 新增 deterministic portfolio snapshot：状态数量、最近更新、陈旧项目、缺失字段、待确认项。
- [x] 所有 snapshot 指标由数据库字段确定性计算，不调用 LLM。
- [x] 旧 system judgement 仅在需要时作为 legacy 历史查看，不进入默认首页。
- [x] 页面文案使用“待用户确认”“缺少记录”“最近更新”，不使用“建议继续/暂停”。
- [x] 添加最小 UI/API smoke test。

### 完成定义

- [x] 默认首页没有 Agent 控制建议。
- [x] 每个组合指标可追溯到数据库查询。
- [x] 旧项目仍能打开详情页。

### 验收命令

```powershell
uv run pytest -q
node --check app/static/app.js
uv run python -m compileall app
```

如果仓库已有浏览器验证能力，再检查首页和一个项目详情页的可见文本与布局。

### 建议 commit

`refactor: replace judgement UI with context snapshot`

---

## Step 6：为事实与决定增加来源和确认状态

**优先级：P1**

**目标：** 用户能够区分已确认信息、文档摘录、Agent 整理结果和 legacy 数据。

### 前置条件

- [x] Step 5 完成。
- [x] 数据库备份仍可用。

### 主要文件

- `app/models.py`
- `app/db.py`
- `app/schemas.py`
- `app/services/project_updater.py`
- 导出与详情页相关文件

### Todo

- [x] 设计最小 provenance 字段：`source_type`、`source_ref`、`confirmation`、`recorded_at`。
- [x] `source_type` 至少支持 `user | document | import | legacy`。
- [x] `confirmation` 至少支持 `confirmed | unconfirmed | legacy`。
- [x] 新事实和决定默认不能省略来源。
- [x] Agent 整理出的未确认内容只能进入 open questions 或 unconfirmed。
- [x] 历史数据迁移为 legacy，不伪装成用户确认。
- [x] context export 展示来源和确认状态。
- [x] UI 对 confirmed/unconfirmed/legacy 做清晰、克制的区分。
- [x] 添加迁移幂等测试：重复 `init_db()` 不破坏数据。

### 完成定义

- [x] 任意新增长期事实可以回答“来自哪里、是否确认”。
- [x] 未确认内容无法通过 schema 进入 confirmed decisions/facts。
- [x] 旧数据完整可读。

### 验收命令

```powershell
uv run pytest -q
uv run python -m compileall app
uv run python -m app.agent_tools export --brief
```

### 建议 commit

`feat: add provenance to project context`

---

## Step 7：新增最小文档索引能力

**优先级：P1**

**目标：** 让“整理文档”成为一等能力，但不扩张为内容创作平台。

### 前置条件

- [x] Step 6 完成，provenance 可用。

### 数据范围

`project_documents` 第一版只包含：

- `id`
- `project_id`
- `title`
- `document_type`
- `source_uri`
- `source_kind`
- `summary`
- `tags`
- `version_or_date`
- `status`: `current | stale | superseded | unknown`
- `added_at`
- `updated_at`

### Todo

- [x] 新增文档表和幂等迁移。
- [x] 新增 typed schema。
- [x] 新增 `document_add`。
- [x] 新增 `document_update_metadata`。
- [x] 新增 `document_link`。
- [x] 新增 `document_archive`。
- [x] 明确不提供“自主重写文档内容”的 runtime operation。
- [x] context export 包含项目相关文档引用。
- [x] 项目详情页展示文档标题、来源、状态、版本和事实性摘要。
- [x] 对不存在的本地路径或失效引用只标记，不自动删除。
- [x] 添加 CRUD、关联、归档和旧数据库迁移测试。

### 完成定义

- [x] 可以登记、关联、更新和归档文档。
- [x] 文档摘要不包含改进建议或路线决策。
- [x] Handoff context packet 能携带相关文档引用。

### 验收命令

```powershell
uv run pytest -q
uv run python -m compileall app
node --check app/static/app.js
```

### 建议 commit

`feat: add project document index`

---

## Step 8：渐进废弃决策型字段

**优先级：P1**

**目标：** 从数据模型中移除会诱导 Agent 代替用户判断的字段，同时保住历史记录。

### 前置条件

- [x] Step 7 完成。
- [x] 已确认 snapshot、provenance 和 documents 足以承载主要 UI。

### 待废弃字段

- `value_score`
- `risk_level`（替换为用户确认的 `known_risks`，不自动分级）
- `ai_delegation_level`
- `human_intervention_level`
- `control_action`
- `control_action_note`
- `progress_percent`（只允许显式用户值时可另行保留）
- `key_judgements`（拆为 user decisions 与 open questions）

### Todo

- [x] 第一阶段：schema 停止新写入上述字段。
- [x] 第二阶段：export 将其标为 legacy，不作为核心 context。
- [x] 第三阶段：UI 移除默认展示。
- [x] 将明确由用户给出的风险迁入 `known_risks`。
- [x] 将可确认的历史 judgement 拆分为 user decision 或 legacy note；不得自动升级为 confirmed。
- [x] 评估 SQLite 是否值得物理删列；若收益不足，保留 nullable legacy 列。
- [x] 删除不再使用的枚举、label、seed 示例和代码路径。
- [x] 添加旧数据库回归测试。

### 完成定义

- [x] 新项目不再要求价值评分、风险评级、委派等级或控制动作。
- [x] 默认导出和页面不含决策型字段。
- [x] 历史数据没有静默丢失。

### 验收命令

```powershell
rg -n "value_score|risk_level|ai_delegation_level|human_intervention_level|control_action|top_control_recommendation" app skills README.md AGENTS.md
uv run pytest -q
uv run python -m compileall app
```

搜索允许命中明确标记的 migration/legacy 兼容代码；逐项人工确认。

### 建议 commit

`refactor: retire decision-oriented project fields`

---

## Step 9：统一验证、精简维护面并完成交付

**优先级：P2**

**目标：** 给后续 builder 一个稳定的验证入口，并移除不再产生价值的 harness 复杂度。

### 前置条件

- [x] Step 0–8 全部完成。

### Todo

- [x] 在现有 Python CLI 中新增统一 `verify`，不引入新任务框架。
- [x] `verify` 串联 Python compile、tests、JS syntax、doctor、版本同步和 boundary reference check。
- [x] `feedback-report` 只汇总事实，不自动输出产品升级建议。
- [x] 将 usage/episode/upgrader 说明移到 maintainer 文档，runtime skill 只保留日常操作。
- [x] 评估 episode 是否有真实消费路径；没有则缩减为最小 apply audit。
- [x] 检查并删除重复规则、死枚举、无消费者字段和过期示例。
- [x] README 加入最终快速开始和 Handoff 示例。
- [x] 运行全量验证。
- [x] 用临时数据库完成一次创建项目、记录事件、登记文档、导出上下文、归档文档的端到端 smoke。
- [x] 用真实页面完成一次首页和项目详情的视觉检查。
- [x] 更新版本和变更说明。
- [x] 在“执行记录”填写最终状态、遗留风险和 deferred work。

### 完成定义

- [x] `uv run python -m app.agent_tools verify` 一条命令可判断工程是否健康。
- [x] 新 Agent 只读 AGENTS + canonical boundary 即可正确操作。
- [x] 普通记录不产生 judgement、评分或建议。
- [x] 深度请求稳定进入 Handoff。
- [x] 文档可登记、追溯、关联和导出。
- [x] 旧数据可读且有明确 legacy 标记。

### 最终验收命令

```powershell
uv run python -m app.agent_tools verify
uv run python -m app.agent_tools doctor
uv run python -m app.agent_tools export --brief
git diff --check
git status --short
```

### 建议 commit

`chore: finalize pure project-manager runtime`

---

## Step 10：修复独立验收发现的契约缺口

**优先级：P0/P1**

**目标：** 修复自动化全绿但生产边界仍可被绕过的问题，使 provenance、项目匹配、旧 payload 兼容和首页 legacy 展示与 canonical contract 一致。

### 验收背景

2026-06-23 独立验收结果：

- `uv run python -m app.agent_tools verify`：通过。
- `uv run pytest -q`：51 passed，2 个 FastAPI lifespan 弃用警告。
- 首页与项目详情：可正常加载，控制台无 error/warn，布局正常。
- 结论：**暂不验收通过**。定向对抗探针发现下述 5 个未被现有测试捕获的问题。

### 前置条件

- [x] 阅读 `docs/product-boundary.md`、`docs/record-contract.md` 和本 Step。
- [x] 根据独立验收记录确认起始基线为 51 passed，并在修复后复跑 `verify`。
- [x] 确认起始工作区无其他未说明改动。
- [x] 修复过程中未写入真实项目业务记录；复现使用纯函数、Pydantic model 或临时数据库。

### Issue 10.1：混合格式事实绕过 provenance

**严重级别：P0**

**位置：** `app/schemas.py:126-141`、`app/provenance.py:111-139`、`app/contracts/record_guard.py`

当前 `validated_facts` 只要包含任意一个结构化 dict，schema 就进入 embedded 分支并提前返回。混合列表中的普通字符串可缺少对应 provenance，最终在 `merge_facts_with_provenance()` 中被默认保存为 `source_type=user`、`confirmation=confirmed`。

已复现输入：

```python
{
    "project_memory_updates": [{
        "project_name": "X",
        "validated_facts": [
            {
                "text": "有来源事实",
                "source_type": "document",
                "confirmation": "confirmed"
            },
            "无来源事实"
        ],
        "_provenance": [{
            "source_type": "user",
            "confirmation": "confirmed"
        }]
    }]
}
```

当前结果：record guard 无 violation；第二条事实被自动解析为 user/confirmed。

#### Todo

- [x] 明确选择并记录一种规则：禁止结构化/字符串混用，或逐项严格校验。
- [x] 推荐最小实现：若包含结构化事实，则要求所有条目都是结构化事实；否则全部使用字符串 + 等长 `_provenance`。
- [x] 将 `has_embedded = any(...)` 改成不会跳过其他条目的逐项校验。
- [x] `record_guard` 同步验证混合列表和 provenance 数量，不能只检查“是否存在 provenance”。
- [x] `merge_facts_with_provenance()` 不得为新写入缺失来源的字符串默认赋予 user/confirmed。
- [x] 添加回归测试：上述 payload 必须被拒绝。
- [x] 添加回归测试：全结构化列表、全字符串 + 等长 provenance 均可通过。

#### 完成定义

- [x] 任意新事实都无法在缺少明确来源时落为 confirmed。
- [x] schema、record guard 和持久化合并逻辑对同一输入给出一致结论。

---

### Issue 10.2：模糊项目名可能写入错误项目

**严重级别：P0**

**位置：** `app/services/project_updater.py:46-62`

`match_project()` 当前使用双向子串匹配。已复现：输入项目名 `AI` 会命中已有项目 `AI客服`。所有 rename/update/memory/delete/event/document 操作都复用该函数，因此未知或相似名称可能修改错误项目。

#### Todo

- [x] 将写操作匹配限制为：精确名称、大小写规范化后的精确名称、显式 `PROJECT_ALIASES`。
- [x] 删除写路径中的双向子串匹配。
- [x] 未保留模糊写入搜索；相似名称只作为未匹配项处理。
- [x] 对 alias 冲突和多候选情况返回明确错误，不取第一个项目。
- [x] 添加回归测试：`AI` 不得匹配 `AI客服`。
- [x] 添加回归测试：精确名称和显式 alias 仍能正常写入。
- [x] 覆盖 event、memory update、archive/delete 和 document operations 的生产 apply 路径。

#### 完成定义

- [x] 未知或相似项目名只进入 `skipped/invalid`，不会产生数据库变化。
- [x] 所有写操作共享同一套安全的精确匹配规则。

---

### Issue 10.3：旧 system_judgement 兼容测试绕过生产守卫

**严重级别：P1**

**位置：** `tests/test_record_contract.py:195-209`、`app/services/apply_control.py:89-117`

现有兼容测试直接调用 `apply_updates(conn, parsed)`，绕过 `apply_raw_json()` 中的 `validate_record_payload()`。因此测试声称旧 payload 可 apply，但真实 CLI/API 路径会因 `forbidden_system_judgement` 拒绝同一 payload。

#### Todo

- [x] 先做产品选择并写入 `docs/record-contract.md`：旧 payload 是“只可解析”还是“生产 apply 仍兼容”。
- [x] 保持 Roadmap 原承诺：旧 payload 可读取和 apply，但忽略/只归档 legacy judgement；新调用方禁止生成。
- [x] 兼容逻辑位于生产入口，不再只在测试中绕过 guard。
- [x] 修改测试，通过 `apply_raw_json()` 验证真实路径。
- [x] 添加 payload 测试：主动发送 judgement 时得到清晰的 deprecated/ignored 语义。
- [x] 未选择生产拒绝旧 payload；无需修改为“只可解析”。

#### 完成定义

- [x] 文档、record guard、CLI/API 和测试对旧 payload 行为完全一致。
- [x] 测试不再直接绕过生产安全入口证明兼容性。

---

### Issue 10.4：known_risks / risk_note 可无来源写入

**严重级别：P1**

**位置：** `app/schemas.py:68-72`、`app/schemas.py:98-110`、`app/contracts/record_guard.py`

`risk_note` 和 `known_risks` 当前为普通字符串字段。以下 payload 无 provenance 也能通过 schema 与 record guard：

```python
{
    "project_updates": [{
        "project_name": "X",
        "risk_note": "Agent 推断风险"
    }],
    "project_memory_updates": [{
        "project_name": "X",
        "known_risks": ["Agent 推断风险"]
    }]
}
```

这与 `record-contract.md` 中“risk_note 仅在用户提供并确认写入时更新”不一致。

#### Todo

- [x] 为 `known_risks` 采用与 validated facts 一致的结构化 provenance，并新增 `_risk_provenance`。
- [x] `risk_note` 停止新写入，只从带 provenance 的 known risks 展示风险。
- [x] record guard 拒绝无来源风险以及 `confirmation=unconfirmed/legacy` 的新风险。
- [x] 迁移旧风险为 legacy，不自动标为用户 confirmed。
- [x] 添加 schema、guard、apply 和导出回归测试。

#### 完成定义

- [x] Agent 推断风险不能直接进入长期档案。
- [x] 页面能够区分用户确认风险和 legacy 风险。

---

### Issue 10.5：首页未标记 legacy 建议

**严重级别：P1**

**位置：** `app/templates/index.html:251-254`、`app/templates/project.html:143-147`

项目详情页会为历史 decision 显示 provenance 标签，但首页近期记录直接渲染 `decision` 和 `next_action`。实机验收中，旧 Agent 生成的“应调整为 active”“建议下一步”等内容仍以普通“记录/待办”展示，容易被误认为当前用户决定。

#### Todo

- [x] 首页 timeline 使用与详情页一致的 provenance 标签。
- [x] 对 legacy decision 显示“历史存档”，不使用普通当前决定的视觉权重。
- [x] 对无 provenance 的旧 next_action 标记 legacy。
- [x] 不改写或删除历史事件内容。
- [x] 扩充 UI smoke：legacy decision/next_action 在首页被标记。
- [x] 使用隔离临时数据库浏览器复验首页和包含 legacy 事件的项目详情。

#### 完成定义

- [x] 默认首页不会把历史 Agent 控制建议呈现成当前普通记录。
- [x] 首页与详情页的 provenance 语义一致。

---

### Issue 10.6：新 next_action 可无 provenance 写入

**严重级别：P1**

**位置：** `app/schemas.py:223-241`、`app/contracts/record_guard.py`、`app/prompts/project_control_panel.md:128`、`app/templates/index.html`、`app/templates/project.html`

独立复验确认原五项问题均已修复，但发现 `ProjectEventInput.next_action` 仍是无来源字符串：schema 与 record guard 都会接受 Agent 直接生成的行动建议。Prompt 仍要求输出 `next_action`，而 UI 为避免误导，只能把所有 next action 一律标记为 legacy。这会同时造成两类错误：Agent 建议仍能进入长期档案；用户刚确认的新行动也会被误标为“历史待办”。

已复现输入：

```python
{
    "project_events": [{
        "project_name": "X",
        "event_type": "note",
        "summary": "会议记录",
        "next_action": "Agent 建议的下一步"
    }]
}
```

当前结果：schema 解析成功，record guard 无 violation。

#### 推荐设计

保留项目经理记录用户确认行动的能力，新增 `next_action_provenance`，语义与 `decision_provenance` 一致：

- 新 `next_action` 必须携带 `source_type` 与 `confirmation=confirmed`。
- `source_type` 只允许 `user | document | import`。
- 历史无来源 next action 迁移或读取为 `legacy`。
- 首页与详情页根据真实 provenance 展示，不再把所有 next action 强制标为 legacy。

如果不希望扩展 schema，备选方案是停止新协议写入 `next_action`，仅保留 legacy 只读；两种方案必须选择其一并同步 canonical contract。

#### Todo

- [x] 在 `docs/record-contract.md` 明确 next action 的来源与确认规则。
- [x] 为 `ProjectEventInput` 增加 `next_action_provenance`。
- [x] schema 拒绝无 provenance、unconfirmed 或 legacy 来源的新 next action。
- [x] record guard 对原始 payload 执行相同约束。
- [x] 为 `project_events` 增加幂等迁移，并把旧 next action 标为 legacy。
- [x] `append_project_event()` 保存 next-action provenance。
- [x] `row_to_event_dict()` 返回真实 next-action provenance，旧数据返回 legacy。
- [x] 更新 Prompt JSON 示例，不再生成无来源 next action。
- [x] 首页和详情页使用真实 provenance 标签；新 confirmed 行动不显示为“历史待办”。
- [x] 添加生产路径回归测试：无 provenance next action 被拒绝。
- [x] 添加生产路径回归测试：confirmed user/document next action 可写入并正确导出。
- [x] 添加迁移回归测试：旧 next action 保持可读并标为 legacy。
- [x] 添加 UI smoke：新 confirmed 行动与 legacy 行动标签不同。

#### 完成定义

- [x] Agent 不能把建议直接写入 `next_action`。
- [x] 用户确认的新行动不会被误标为历史。
- [x] 历史 next action 不丢失，并保持 legacy 标签。
- [x] schema、guard、数据库、导出、Prompt 和 UI 对 next action provenance 的语义一致。

---

### Step 10 回归测试清单

- [x] 混合事实 payload 被拒绝，不会默认补 user/confirmed。
- [x] 相似项目名无法命中可写目标。
- [x] 旧 judgement payload 的生产行为与文档一致。
- [x] 无 provenance 风险写入被拒绝。
- [x] 首页 legacy 事件有明确历史标签。
- [x] 无 provenance next action 写入被拒绝。
- [x] confirmed next action 与 legacy next action 正确区分。
- [x] `uv run pytest -q` 全部通过，无 xfail 掩盖上述问题（64 passed）。
- [x] `uv run python -m app.agent_tools verify` 全绿。
- [x] `uv run python -m app.agent_tools doctor` 全绿。
- [x] `git diff --check` 通过。
- [x] 工作区只包含 Step 10 预期改动。

### Step 10 最终验收

Builder 完成后必须再次请求独立验收。验收者应：

1. 复跑上述 6 个问题场景，不只依赖仓库测试。
2. 通过真实 `/api/apply` 或 `apply_raw_json()` 验证写路径。
3. 实机检查首页和项目详情的 legacy 标签。
4. 确认真实项目数据库未被测试污染。
5. 将结果填写到“执行记录”，再决定是否恢复“Roadmap 已完成”。

### 建议 commit

`fix: close pure project-manager acceptance gaps`

---

## 不在本 Roadmap 范围内

- [ ] 不开发独立聊天 UI。
- [ ] 不构建 RAG、向量数据库或自动知识图谱。
- [ ] 不引入多 Agent 自动编排。
- [ ] 不让项目管家自动根据 feedback 修改自己。
- [ ] 不执行任何独立项目的实际工程、写作、投研或运营任务。
- [ ] 不一次性硬删除 legacy 数据列。
- [ ] 不为追求形式完整而引入 CI、容器或复杂观测系统。

## 发现的问题

Builder 在执行过程中只追加简短记录，不在当前 Step 外扩修：

- [x] **Step 4 验收备注：** `SKILL.md` 中 `prioritization` 仅出现在禁止句「Do not perform… prioritization」中，非授权表达。
- [x] **Step 2 已解决（Step 3）：** `system_judgement` 已 optional；单事件无 judgement 可 apply。
- [x] **Step 2 契约已锁、实现待接：** `record_guard` 已校验 `_provenance`，但 apply 路径尚未强制；Step 6 落地 schema 后接入。
- [x] **Step 6 已解决：** `record_guard` 已接入 `apply_raw_json`；`validated_facts` 结构化存储；历史字符串事实迁移为 `legacy`。
- [x] **Step 9 备注：** FastAPI `@app.on_event("startup")` DeprecationWarning 仍非阻塞。
- [x] **视觉验收（人工）：** 首页与项目详情布局、文案与组合快照展示已确认通过（2026-06-23）。

**遗留风险 / deferred：** 物理删除 legacy DB 列（Step 8 评估保留）；`llm.py` / `seed.py` 仍含演示用决策型种子数据；episode 仅最小审计无消费端。

## 执行记录

**Step 0 起始 `git status --short`：** 干净（无未提交变更）。

**Step 0 基线命令：**


| 命令                                                 | 结果                                      |
| -------------------------------------------------- | --------------------------------------- |
| `uv run python -m compileall app`                  | 通过                                      |
| `node --check app/static/app.js`                   | 通过                                      |
| `uv run python -m app.agent_tools doctor`          | 通过（runtime/skill 0.8.0，7 项检查全绿）         |
| `uv run python -m app.agent_tools feedback-report` | 通过（30 条 usage，7 条 feedback，8 条 upgrade） |
| `uv run python -m app.agent_tools export --brief`  | 通过（多项目数据可读）                             |


**数据库：** `data/project_control_panel.db`（315392 字节）

**迁移前备份：** `.agent-workspace/backups/project_control_panel-20260623-101104.db`（未纳入 Git）


| Step | 状态  | 日期         | Commit    | 验证结果                 | 备注                                                     |
| ---- | --- | ---------- | --------- | -------------------- | ------------------------------------------------------ |
| 0    | 完成  | 2026-06-23 | —         | 全通过                  | 基线 HEAD `0480611`；未改业务数据                               |
| 1    | 完成  | 2026-06-23 | `d45fcb6` | 验收通过                 | 新增 `product-boundary.md`、`record-contract.md`          |
| 2    | 完成  | 2026-06-23 | `fe556e7` | 12 passed, 1 xfailed | `app/contracts/`、`tests/`、pytest dev 依赖                |
| 3    | 完成  | 2026-06-23 | `d87dcad` | 17 passed            | optional judgement、`change_summary`、`confirm_explicit` |
| 4    | 完成  | 2026-06-23 | `e6dc92f` | 17 passed；rg 无授权命中   | v0.9.0；四入口链接 canonical contract                        |
| 5    | 完成  | 2026-06-23 | `41f1b7f` | 25 passed            | context_snapshot + UI smoke                            |
| 5+   | 完成  | 2026-06-23 | `b1736eb` | —                    | 组合快照卡片排版修补                                             |
| 6    | 完成  | 2026-06-23 | `b4d8cbc` | 31→48                | provenance（与 Step 7 同 commit）                          |
| 7    | 完成  | 2026-06-23 | `b4d8cbc` | 41 passed            | project_documents + document_*                         |
| 8    | 完成  | 2026-06-23 | `af0b8e6` | 48 passed            | legacy 决策字段废弃 + known_risks                            |
| 9    | 完成  | 2026-06-23 | `54fb827`/`ee22a47` | 51 passed; verify 全绿；视觉验收通过 | v1.0.0 + verify CLI + e2e smoke |
| 10   | 完成  | 2026-06-23 | `45c2492` + v1.0.2 收口提交 | 64 passed；verify/doctor/diff 与浏览器复验全绿 | next_action provenance 已贯通 schema/guard/DB/export/UI |

**Step 10 执行记录：** 原五项修复提交为 `45c2492`。选择严格的同质 provenance 格式；旧 `system_judgement` 生产兼容为“归档并忽略”；`risk_note` 停止新写入；所有写操作改用精确/alias 匹配；首页与详情统一显示 legacy 标签。独立复验确认 61 tests、verify/doctor、五个原始探针、页面 legacy 标签均通过，真实库 `projects/project_events/project_documents/logs` 计数保持 `13/40/0/25`。复验新增发现 Issue 10.6：`next_action` 仍可无 provenance 写入。

**Issue 10.6 执行记录：** 新增 `next_action_provenance` 与幂等迁移；无来源、unconfirmed、legacy 新写入均被 schema 和 record guard 拒绝；confirmed user/document 行动可经 `apply_raw_json()` 写入并导出；旧行动迁移为 legacy。版本同步为 `1.0.2`。验收前备份：`.agent-workspace/backups/project_control_panel-step106-20260623-162647.db`。迁移前后真实库业务表计数均为 `13/40/0/25`，历史行动均已带 legacy provenance。64 tests、verify、doctor、UI smoke 和 `git diff --check` 通过。浏览器实机复验因本地浏览器策略明确拒绝 `127.0.0.1:8055`，未绕过该限制，留待独立复验者执行。

**最终独立验收记录：** 2026-06-23 使用当前工作区重新执行全量测试（64 passed）、统一 verify、doctor 与 `git diff --check`，全部通过；另在独立端口 `8001` 启动当前版本，使用真实浏览器检查首页和项目详情，页面正常、legacy 待办标签正确、无控制台错误。真实库业务表计数保持 `13/40/0/25`，37 条历史 next action 均已有 provenance，无缺失记录。Issue 10.6 与 Step 10 原始验收条件全部满足。


## 改造收尾

**最终交付版本：** `1.0.2`；Step 0–10 与 Issue 10.6 均已完成并通过独立复验。

**一句话：** 从「会替用户判断的项目助手」收敛为「只维护档案、导出上下文、必要时交接」的纯项目经理运行时。

**关键 commit 链：** `d45fcb6`（边界契约）→ `fe556e7`（契约测试）→ `d87dcad`（去 judgement 依赖）→ `e6dc92f`（三模式入口）→ `41f1b7f`（确定性 UI）→ `b4d8cbc`（来源追溯 + 文档索引）→ `af0b8e6`（废弃决策字段）→ `54fb827`（verify 与交付）

**日常验收：**

```powershell
uv run python -m app.agent_tools verify
```

**后续维护：** 见 [maintainer-guide.md](maintainer-guide.md)；框架升级用 `skills/project-manager-upgrader/`，不与项目业务记录混淆。

**已知 deferred（不阻塞 v1.0）：** legacy DB 列保留；`seed.py`/`llm.py` 演示数据仍含历史决策型字段；episode 仅最小 apply 审计。

## Roadmap 完成判定

- [x] Context、Record、Handoff 三模式均有契约测试。
- [x] 项目管家不会在独立项目中进行深度思考、内容迭代或代替决策。
- [x] 项目上下文中的事实、决定和风险都有来源与确认状态。（Step 10）
- [x] 文档整理是一等能力，且不会扩张为自主内容创作。
- [x] 首页展示确定性上下文健康信息，legacy Agent 建议不会伪装成当前记录。（Step 10）
- [x] 新 next action 具有来源与确认状态，confirmed 与 legacy 展示准确。（Issue 10.6）
- [x] 普通写入无需 `system_judgement`。
- [x] 旧项目和历史记录仍可读取。
- [x] Issue 10.6 回归测试、统一 verify、全量测试、UI smoke 与独立复验全部通过。
