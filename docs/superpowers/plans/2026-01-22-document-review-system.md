# 文档审查系统实现计划

> **对于代理工作者：** 必需：使用 booming:subagent-driven-development（如果有子 agents）或 booming:executing-plans 来逐任务实现此计划。

**目标：** 为 brainstorming 和 writing-plans 技能添加规格和计划文档审查循环。

**架构：** 在每个技能目录中创建审查者提示模板。修改技能文件以在文档创建后添加审查循环。使用 Task 工具和通用子 agent 进行审查者派发。

**技术栈：** Markdown 技能文件，通过 Task 工具进行子 agent 派发

**规格：** docs/booming/specs/2026-01-22-document-review-system-design.md

---

## 块 1：规格文档审查者

此块将规格文档审查者添加到 brainstorming 技能中。

### 任务 1：创建规格文档审查者提示模板

**文件：**
- 创建：`skills/brainstorming/spec-document-reviewer-prompt.md`

- [ ] **步骤 1：** 创建审查者提示模板文件

```markdown
# Spec Document Reviewer Prompt Template

Use this template when dispatching a spec document reviewer subagent.

**Purpose:** Verify the spec is complete, consistent, and ready for implementation planning.

**Dispatch after:** Spec document is written to docs/booming/specs/

```
Task tool (general-purpose):
  description: "Review spec document"
  prompt: |
    You are a spec document reviewer. Verify this spec is complete and ready for planning.

    **Spec to review:** [SPEC_FILE_PATH]

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Completeness | TODOs, placeholders, "TBD", incomplete sections |
    | Coverage | Missing error handling, edge cases, integration points |
    | Consistency | Internal contradictions, conflicting requirements |
    | Clarity | Ambiguous requirements |
    | YAGNI | Unrequested features, over-engineering |

    ## CRITICAL

    Look especially hard for:
    - Any TODO markers or placeholder text
    - Sections saying "to be defined later" or "will spec when X is done"
    - Sections noticeably less detailed than others

    ## Output Format

    ## Spec Review

    **Status:** ✅ Approved | ❌ Issues Found

    **Issues (if any):**
    - [Section X]: [specific issue] - [why it matters]

    **Recommendations (advisory):**
    - [suggestions that don't block approval]
```

**Reviewer returns:** Status, Issues (if any), Recommendations
```

- [ ] **步骤 2：** 验证文件已正确创建

运行：`cat skills/brainstorming/spec-document-reviewer-prompt.md | head -20`
预期：显示头部和目的章节

- [ ] **步骤 3：** 提交

```bash
git add skills/brainstorming/spec-document-reviewer-prompt.md
git commit -m "feat: add spec document reviewer prompt template"
```

---

### 任务 2：向 Brainstorming 技能添加审查循环

**文件：**
- 修改：`skills/brainstorming/SKILL.md`

- [ ] **步骤 1：** 读取当前 brainstorming 技能

运行：`cat skills/brainstorming/SKILL.md`

- [ ] **步骤 2：** 在"设计完成后"部分之后添加审查循环章节

找到"After the Design"章节，在文档之后、实现之前添加新的"规格审查循环"章节：

```markdown
**规格审查循环：**
编写规格文档后：
1. 派发规格文档审查者子 agent（见 spec-document-reviewer-prompt.md）
2. 如果 ❌ 发现问题：
   - 修复规格文档中的问题
   - 重新派发审查者
   - 重复直到 ✅ 批准
3. 如果 ✅ 批准：继续实现设置

**审查循环指导：**
- 编写规格的同一 agent 修复它（保留上下文）
- 如果循环超过 5 次迭代，向人类寻求指导
- 审查者是顾问——如果你认为反馈不正确，解释你的不同意见
```

- [ ] **步骤 3：** 验证更改

运行：`grep -A 15 "Spec Review Loop" skills/brainstorming/SKILL.md`
预期：显示新的审查循环章节

- [ ] **步骤 4：** 提交

```bash
git add skills/brainstorming/SKILL.md
git commit -m "feat: add spec review loop to brainstorming skill"
```

---

## 块 2：计划文档审查者

此块将计划文档审查者添加到 writing-plans 技能中。

### 任务 3：创建计划文档审查者提示模板

**文件：**
- 创建：`skills/writing-plans/plan-document-reviewer-prompt.md`

- [ ] **步骤 1：** 创建审查者提示模板文件

（内容见计划文档审查者提示模板）

- [ ] **步骤 2：** 验证文件已创建

运行：`cat skills/writing-plans/plan-document-reviewer-prompt.md | head -20`
预期：显示头部和目的章节

- [ ] **步骤 3：** 提交

```bash
git add skills/writing-plans/plan-document-reviewer-prompt.md
git commit -m "feat: add plan document reviewer prompt template"
```

---

### 任务 4：向 Writing-Plans 技能添加审查循环

**文件：**
- 修改：`skills/writing-plans/SKILL.md`

- [ ] **步骤 1：** 读取当前技能文件

运行：`cat skills/writing-plans/SKILL.md`

- [ ] **步骤 2：** 在"执行交接"章节之前添加逐块审查章节

- [ ] **步骤 3：** 更新任务语法示例以使用复选框

- [ ] **步骤 4：** 验证审查循环章节已添加

- [ ] **步骤 5：** 验证任务语法示例已更新

- [ ] **步骤 6：** 提交

```bash
git add skills/writing-plans/SKILL.md
git commit -m "feat: add plan review loop and checkbox syntax to writing-plans skill"
```

---

## 块 3：更新计划文档头部

此块更新计划文档头部模板以引用新的复选框语法要求。

### 任务 5：更新 Writing-Plans 技能中的计划头部模板

**文件：**
- 修改：`skills/writing-plans/SKILL.md`

- [ ] **步骤 1：** 读取当前计划头部模板

运行：`grep -A 20 "Plan Document Header" skills/writing-plans/SKILL.md`

- [ ] **步骤 2：** 更新头部模板以引用复选框语法

- [ ] **步骤 3：** 验证更改

运行：`grep -A 5 "For agentic workers:" skills/writing-plans/SKILL.md`
预期：显示带有复选框语法提及的更新头部

- [ ] **步骤 4：** 提交

```bash
git add skills/writing-plans/SKILL.md
git commit -m "docs: update plan header to reference checkbox syntax"
```
