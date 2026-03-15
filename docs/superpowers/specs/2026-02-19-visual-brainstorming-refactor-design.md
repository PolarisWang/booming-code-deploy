# 可视化头脑风暴重构：浏览器显示，终端命令

**日期：** 2026-02-19
**状态：** 已批准
**范围：** `lib/brainstorm-server/`、`skills/brainstorming/visual-companion.md`、`tests/brainstorm-server/`

## 问题

在可视化头脑风暴期间，Claude 以后台任务运行 `wait-for-feedback.sh` 并阻塞在 `TaskOutput(block=true, timeout=600s)`。这完全占用了 TUI——在可视化头脑风暴运行时用户无法向 Claude 输入。浏览器成为唯一的输入通道。

Claude Code 的执行模型是轮次制的。没有办法让 Claude 在单个轮次中同时监听两个通道。阻塞的 `TaskOutput` 模式是错误的原语——它模拟了平台不支持的事件驱动行为。

## 设计

### 核心模型

**浏览器 = 交互式显示。** 显示原型，让用户点击选择选项。选择在服务器端记录。

**终端 = 对话通道。** 始终不阻塞，始终可用。用户在这里与 Claude 交谈。

### 循环

1. Claude 将 HTML 文件写入会话目录
2. 服务器通过 chokidar 检测，将 WebSocket 重新加载推送到浏览器（不变）
3. Claude 结束其轮次——告诉用户查看浏览器并在终端回应
4. 用户查看浏览器，可选择点击选择选项，然后在终端输入反馈
5. 在下一轮次，Claude 读取 `$SCREEN_DIR/.events` 获取浏览器交互流（点击、选择），与终端文本合并
6. 迭代或推进

无后台任务。无 `TaskOutput` 阻塞。无轮询脚本。

### 关键删除：`wait-for-feedback.sh`

完全删除。其目的是桥接"服务器将事件记录到 stdout"和"Claude 需要接收这些事件"。`.events` 文件替代了这个——服务器直接写入用户交互事件，Claude 用平台提供的任何文件读取机制读取它们。

### 关键新增：`.events` 文件（每屏事件流）

服务器将所有用户交互事件写入 `$SCREEN_DIR/.events`，每行一个 JSON 对象。这给 Claude 提供了当前屏幕的完整交互流——不只是最终选择，还有用户的探索路径。

用户探索选项后的示例内容：

```jsonl
{"type":"click","choice":"a","text":"Option A - Preset-First Wizard","timestamp":1706000101}
{"type":"click","choice":"c","text":"Option C - Manual Config","timestamp":1706000108}
{"type":"click","choice":"b","text":"Option B - Hybrid Approach","timestamp":1706000115}
```

- 在屏幕内只追加。每个用户事件作为新行追加。
- 当 chokidar 检测到新 HTML 文件（推送新屏幕）时，文件被清除（删除），防止旧事件延续。
- 如果 Claude 读取时文件不存在，则没有浏览器交互发生——Claude 只使用终端文本。

## 按文件变更

### `index.js`（服务器）

**A. 将用户事件写入 `.events` 文件。**

**B. 新屏幕时清除 `.events`。**

**C. 替换 `wrapInFrame` 内容注入。**

### `frame-template.html`（UI 框架）

**删除：** feedback-footer div（文本区域、发送按钮、标签、`.feedback-row`）

**添加：** 在 footer 所在位置添加选择指示条，有两种状态：
- 默认："点击上面的选项，然后返回终端"
- 选择后："已选择选项 B——返回终端继续"

### `helper.js`（客户端脚本）

**删除：** `sendToClaude()` 函数、`window.send()` 函数、表单提交处理程序

**保留：** WebSocket 连接、重连逻辑、重新加载处理程序、`window.toggleSelect()`、`window.brainstorm.send()` 和 `window.brainstorm.choice()`

**缩小：** 点击处理程序只捕获 `[data-choice]` 点击

### `visual-companion.md`（技能说明）

**重写"循环"章节**为上述非阻塞流程。删除对以下内容的所有引用：
- `wait-for-feedback.sh`
- `TaskOutput` 阻塞
- 超时/重试逻辑

**替换为：** 新循环（写 HTML → 结束轮次 → 用户在终端回应 → 读取 `.events` → 迭代）

### `wait-for-feedback.sh`

**完全删除。**

## 平台兼容性

服务器代码完全与平台无关——纯 Node.js 和浏览器 JavaScript。非阻塞模型在各平台上自然工作，因为它不依赖任何平台特定的阻塞原语。

## 这带来了什么

- **TUI 在可视化头脑风暴期间始终响应**
- **混合输入** — 在浏览器点击 + 在终端输入，自然合并
- **优雅降级** — 浏览器宕机或用户不打开？终端仍然工作
- **更简单的架构** — 无后台任务，无轮询脚本，无超时管理
- **跨平台** — 相同服务器代码在 Claude Code、Codex 和任何未来平台上工作

## 这放弃了什么

- **纯浏览器反馈工作流** — 用户必须返回终端继续
- **从浏览器内联文本反馈** — 文本区域没了。所有文本反馈通过终端
- **浏览器发送时立即响应** — 旧系统在用户点击发送时 Claude 立即响应
