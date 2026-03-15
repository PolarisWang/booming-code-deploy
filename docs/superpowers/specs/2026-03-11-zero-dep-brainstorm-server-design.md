# 零依赖头脑风暴服务器

用一个使用 Node.js 内置模块的单一零依赖 `server.js` 替换头脑风暴伴侣服务器的 vendored node_modules（express、ws、chokidar——714 个被跟踪的文件）。

## 动机

将 node_modules 纳入 git 仓库会产生供应链风险：冻结的依赖无法获得安全补丁，714 个第三方代码文件在未经审计的情况下被提交，对 vendored 代码的修改看起来像普通提交。虽然实际风险较低（仅限本地开发服务器），但消除它很简单。

## 架构

一个使用 `http`、`crypto`、`fs` 和 `path` 的单一 `server.js` 文件（约 250-300 行）。文件服务两个角色：

- **直接运行时**（`node server.js`）：启动 HTTP/WebSocket 服务器
- **被引用时**（`require('./server.js')`）：导出 WebSocket 协议函数用于单元测试

### WebSocket 协议

仅对文本帧实现 RFC 6455：

**握手：** 使用 SHA-1 + RFC 6455 魔法 GUID 从客户端的 `Sec-WebSocket-Key` 计算 `Sec-WebSocket-Accept`。返回 101 Switching Protocols。

**帧解码（客户端到服务器）：** 处理三种掩码长度编码：
- 小：负载 < 126 字节
- 中：126-65535 字节（16 位扩展）
- 大：> 65535 字节（64 位扩展）

使用 4 字节掩码键对负载进行 XOR 解掩码。返回 `{ opcode, payload, bytesConsumed }` 或 `null`（不完整缓冲区）。拒绝未掩码帧。

**帧编码（服务器到客户端）：** 具有相同三种长度编码的未掩码帧。

**处理的操作码：** TEXT (0x01)、CLOSE (0x08)、PING (0x09)、PONG (0x0A)。未识别的操作码获得状态 1003（不支持的数据）的关闭帧。

**刻意跳过：** 二进制帧、分片消息、扩展（permessage-deflate）、子协议。对于本地客户端之间的小型 JSON 文本消息来说这些不必要。

**缓冲区积累：** 每个连接维护一个缓冲区。在 `data` 时，附加并循环 `decodeFrame` 直到它返回 null 或缓冲区为空。

### HTTP 服务器

三条路由：

1. **`GET /`** — 按修改时间提供 screen 目录中最新的 `.html` 文件。检测完整文档与片段，将片段包装在框架模板中，注入 helper.js。返回 `text/html`。
2. **`GET /files/*`** — 从 screen 目录提供静态文件，使用硬编码扩展名映射进行 MIME 类型查找。
3. **其他所有内容** — 404。

WebSocket 升级通过 HTTP 服务器上的 `'upgrade'` 事件处理，与请求处理程序分开。

### 配置

环境变量（均为可选）：

- `BRAINSTORM_PORT` — 绑定的端口（默认：随机高端口 49152-65535）
- `BRAINSTORM_HOST` — 绑定的接口（默认：`127.0.0.1`）
- `BRAINSTORM_URL_HOST` — 启动 JSON 中 URL 的主机名（默认：当主机为 `127.0.0.1` 时为 `localhost`）
- `BRAINSTORM_DIR` — screen 目录路径（默认：`/tmp/brainstorm`）

### 启动序列

1. 如果不存在则创建 `SCREEN_DIR`（`mkdirSync` 递归）
2. 从 `__dirname` 加载框架模板和 helper.js
3. 在配置的主机/端口上启动 HTTP 服务器
4. 在 `SCREEN_DIR` 上启动 `fs.watch`
5. 监听成功后，将 `server-started` JSON 记录到 stdout
6. 将相同 JSON 写入 `SCREEN_DIR/.server-info`

### 应用层 WebSocket 消息

当 TEXT 帧从客户端到达时：

1. 解析为 JSON
2. 作为 `{ source: 'user-event', ...event }` 记录到 stdout
3. 如果事件包含 `choice` 属性，将 JSON 追加到 `SCREEN_DIR/.events`

### 文件监视

`fs.watch(SCREEN_DIR)` 替换 chokidar。对 HTML 文件事件：

- 新文件：删除 `.events` 文件（如果存在），记录 `screen-added`
- 文件更改：记录 `screen-updated`（不清除 `.events`）
- 两种事件：向所有连接的 WebSocket 客户端发送 `{ type: 'reload' }`

使用约 100ms 超时对每个文件名进行防抖，防止重复事件。

## 变更内容

| 之前 | 之后 |
|------|------|
| `index.js` + `package.json` + `package-lock.json` + 714 个 `node_modules` 文件 | `server.js`（单一文件） |
| express、ws、chokidar 依赖 | 无 |
| 无静态文件服务 | `/files/*` 从 screen 目录提供服务 |

## 保持不变的内容

- `helper.js` — 无更改
- `frame-template.html` — 无更改
- `start-server.sh` — 一行更新：`index.js` 改为 `server.js`
- `stop-server.sh` — 无更改
- `visual-companion.md` — 无更改
- 所有现有的服务器行为和外部接口

## 平台兼容性

- `server.js` 只使用跨平台 Node 内置模块
- `fs.watch` 在 macOS、Linux 和 Windows 上对单个平面目录是可靠的

## 测试

**单元测试**（`ws-protocol.test.js`）：通过引用 `server.js` 导出直接测试 WebSocket 帧编码/解码、握手计算和协议边缘情况。

**集成测试**（`server.test.js`）：测试完整服务器行为——HTTP 服务、WebSocket 通信、文件监视、头脑风暴工作流。使用 `ws` npm 包作为仅测试的客户端依赖（不随发布到最终用户）。
