# Local Agent Customs Submit Design

**Date:** 2026-03-16

## Goal

在不改变 OCR、历史记录、填报草稿和结果中心主体架构的前提下，把“报关提交”这一步切换为可选的本地 Agent 执行模式。服务器继续负责识别和草稿生成，本地 Agent 只负责在用户电脑上执行 Playwright 报关提交。

## Scope

本次仅覆盖“报关提交”执行位置切换：

- OCR 提取仍在服务器
- 报关草稿生成仍在服务器
- 手工提交和自动模式在进入“提交报关”阶段时，可选择由本地 Agent 执行
- 本地 Agent 不负责 OCR、模板或草稿编辑

## Current State

- 系统已经支持 `http` 和 `playwright` 两种服务器端报关提交引擎
- 系统设置中的 `customs_submit_mode` 目前控制服务器侧执行引擎
- 自动模式和手工提交都统一调用 `submit_to_customs_site()`
- 结果中心已能显示提交状态和 `submit_engine`

## User-Facing Behavior

### System Settings

系统设置中的报关提交引擎扩展为：

- `server_http`
- `server_playwright`
- `local_agent`

当选择 `local_agent` 时，额外显示：

- `本地执行 Agent`

该项从在线 Agent 列表中选择，作为当前报关任务的执行目标。

### Manual Submit

用户点击“提交报关”时：

- 若模式为服务器执行，行为与现在一致
- 若模式为 `local_agent`，服务器创建一条“待本地 Agent 执行”的报关任务，不在服务器本地直接提交

### Auto Mode

自动模式进入“提交报关”阶段时：

- 若模式为服务器执行，行为与现在一致
- 若模式为 `local_agent`，自动模式不在服务器直接提交，而是把任务排给指定本地 Agent

### Result Center

结果中心新增/扩展以下状态语义：

- `等待本地 Agent 执行`
- `本地 Agent 执行中`
- `本地 Agent 执行成功`
- `本地 Agent 执行失败`

同时展示：

- `submit_engine = local_agent`
- `assigned_agent_id`

## Architecture

## Server Responsibilities

服务器仍然保留现有职责：

- 文件上传
- OCR 提取
- LLM 草稿生成
- 历史记录存储
- 结果中心状态聚合

新增职责：

- 维护本地 Agent 注册表
- 为指定 Agent 创建报关提交任务
- 接收 Agent 的执行结果回传

### Local Agent Responsibilities

本地 Agent 是一个独立常驻程序，仅负责：

- 向服务器注册自己的身份
- 定时发送心跳
- 拉取分配给自己的报关提交任务
- 在本机用 Playwright 执行登录和表单提交
- 把提交结果回传服务器

### Why Pull Model

采用“Agent 拉取任务”而不是服务器主动推送：

- 简化网络要求，不需要从服务器直连客户电脑
- 适配大多数内网/办公环境
- 页面关闭后仍可继续执行
- 易于扩展到多台报关电脑

## Agent Identity

每个本地 Agent 具有固定身份：

- `agent_id`
- `agent_name`
- `hostname`
- `status`
- `last_heartbeat_at`

服务器只把任务分配给明确选定的 `agent_id`，避免多台设备抢同一条任务。

## Data Flow

1. 用户在系统设置中选择 `customs_submit_mode = local_agent`
2. 用户选择目标 `assigned_agent_id`
3. 用户手工提交，或自动模式进入提交阶段
4. 服务器创建一条本地执行报关任务，并写入：
   - `submit_engine = local_agent`
   - `assigned_agent_id`
   - `submit_status = queued_local`
5. 本地 Agent 轮询拉取属于自己的待执行任务
6. Agent 在本机用 Playwright 执行报关提交
7. Agent 回传成功或失败结果
8. 服务器更新历史记录与结果中心状态

## API Additions

### Agent APIs

需要增加一组本地 Agent 专用接口：

- `POST /api/local-agents/register`
- `POST /api/local-agents/heartbeat`
- `GET /api/local-agents`
- `POST /api/local-agents/{agent_id}/poll-customs-task`
- `POST /api/local-agents/{agent_id}/report-customs-task`

### Submission APIs

现有提交接口保持不变，但内部行为扩展：

- 手工提交接口根据模式决定是服务器直接提交还是创建本地任务
- 自动模式在 `local_agent` 模式下同样创建本地任务

## Persistence

### Settings

`llm_settings.json` 增加：

- `customs_submit_mode`
- `local_agent_id`

### Agent Registry

建议新增轻量本地文件存储：

- `output/settings/local_agents.json`

记录在线 Agent 和最近心跳时间。

### Pending Local Tasks

现有报关提交任务数据结构中增加：

- `assigned_agent_id`
- `submit_engine`
- `delivery_status`

历史记录中的 `submission.meta` 增加：

- `submit_engine`
- `assigned_agent_id`

## Error Handling

### Agent Offline

如果用户选择了 `local_agent`，但目标 Agent 不在线：

- 提交入口直接返回可读错误
- 不创建无法执行的任务

### Heartbeat Timeout

如果 Agent 超过阈值未心跳：

- 标记为离线
- 不再给它分配新任务

### Agent Crash During Execution

如果 Agent 拉到任务后长时间未回传：

- 服务器将任务标记为超时或待人工处理
- 不自动假设成功

### Submission Failure

Agent 回传失败时，服务器应保留完整错误信息并写回：

- `submit_status = failed`
- `submit_message`
- `submit_result`

## Testing Strategy

### Backend

- 设置归一化测试：支持 `local_agent` 和 `local_agent_id`
- Agent 注册/心跳/在线状态测试
- `local_agent` 模式下创建本地执行任务测试
- Agent 回传成功/失败后历史记录更新测试

### Frontend

- 系统设置保存 `local_agent` 与 `local_agent_id`
- Agent 在线列表展示
- 结果中心显示 `assigned_agent_id` 和本地执行状态

### Local Agent

- 轮询拉任务测试
- 提交成功回传测试
- 提交失败回传测试
- 心跳保活测试

## Non-Goals

本次不做：

- 本地 Agent 执行 OCR
- 本地 Agent 生成报关草稿
- 多站点支持
- 服务端主动推送到客户端
- 本地 Agent 抢单机制
