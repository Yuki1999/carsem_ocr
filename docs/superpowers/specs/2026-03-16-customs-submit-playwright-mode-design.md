# Customs Submit Playwright Mode Design

**Date:** 2026-03-16

## Goal

在系统设置中增加“报关提交模式”开关，让手工提交和自动模式都可以统一切换为 `http` 或 `playwright` 两种引擎；当选择 `playwright` 时，报关提交改走浏览器自动化流程。

## Current State

- 系统设置目前只持久化 `auto_mode_enabled` 和 LLM 配置，存储位置在 `output/settings/llm_settings.json`。
- 手工提交和自动模式最终都调用 `submit_to_customs_site()`。
- 当前 `submit_to_customs_site()` 仅支持 `requests.Session()` 直连登录 `/Home/Login`，再调用 `/Home/GetNextDeclarationNo` 和 `/Home/SaveData`。
- 结果中心目前能显示自动模式状态和提交结果，但不会显示提交引擎。

## User-Facing Behavior

### System Settings

新增一个全局设置项：

- `报关提交模式`
  - `HTTP`
  - `Playwright`

默认值保持为 `http`，切换后立即持久化，刷新页面后保持不变。

### Submission Behavior

- 手工点击“提交报关”时，读取系统设置中的 `customs_submit_mode`
- 自动模式在“生成草稿后自动提交”时，也读取同一个设置
- 两条路径必须使用完全一致的提交引擎
- 选择 `playwright` 时，不再走 `requests` 提交，而是启动 Playwright 浏览器登录并填写页面

### Result Visibility

每次提交都在 `submission.meta` 写入：

- `submit_engine`: `http` 或 `playwright`

结果中心展示本次提交使用的模式，便于排查。

## Architecture

### Settings Persistence

在 `llm_settings_store.py` 中增加 `customs_submit_mode` 字段：

- 默认值：`http`
- 允许值：`http`、`playwright`
- 任何非法值都归一化为 `http`

前端系统设置页读取和保存时同步包含该字段。

### Unified Submission Router

保留 `submit_to_customs_site()` 作为统一入口，但把它重构为路由器：

- `mode == "http"` 时调用现有 HTTP 提交流程
- `mode == "playwright"` 时调用新的 Playwright 提交流程

这样上层业务逻辑不需要分叉，只传入模式即可。

### Playwright Engine

新增独立模块 `app/customs_playwright.py`，职责单一：

- 打开登录页
- 填写用户名密码并登录
- 获取报关单号
- 填写表头和明细字段
- 点击保存/提交
- 读取页面成功或失败提示
- 返回与 HTTP 引擎一致的结构

页面字段填写仍使用现有草稿结构：

- `Mawb -> MainBLNo`
- `Hawb -> SubBLNo`
- 其他字段按网站页面字段名填写

### Declaration Number Strategy

第一版 Playwright 模式继续复用接口获取报关单号，而不是从 UI 抓取：

- 减少页面依赖
- 降低选择器复杂度
- 保持与 HTTP 模式一致

如果后续网站行为要求必须从页面生成，再单独演进。

## Data Flow

1. 用户在系统设置切换 `customs_submit_mode`
2. 前端立即调用 `/api/llm-settings` 保存
3. 手工提交或自动模式启动报关提交
4. `main.py` 读取设置并把 `mode` 传给 `submit_to_customs_site()`
5. `submit_to_customs_site()` 按模式路由到 `http` 或 `playwright`
6. 提交结果回写到 `submission.meta`
7. 结果中心显示 `submit_engine` 与提交结果

## Error Handling

### Playwright Environment Missing

如果运行环境未安装 Playwright 或浏览器依赖缺失：

- 明确抛出错误
- 不静默回退到 HTTP
- 结果中心显示可读错误信息

### Login / Page Structure Failures

Playwright 模式下需要区分错误来源：

- `login_failed`
- `page_structure_changed`
- `submission_rejected`
- `playwright_unavailable`

这样和现有 HTTP 路径的错误语义保持一致。

## Testing Strategy

### Backend

- 设置归一化测试：`customs_submit_mode` 默认值和合法值持久化
- 提交路由测试：手工提交与自动模式都能把模式传给统一提交入口
- Playwright 不可用测试：缺少依赖时返回明确错误
- HTTP 回归测试：现有 HTTP 流程继续可用

### Frontend

- 系统设置切换 `customs_submit_mode` 后立即持久化
- 页面刷新后值保持
- 结果中心展示 `submit_engine`

## Non-Goals

本次不做以下内容：

- Playwright 失败后自动回退 HTTP
- 多站点兼容
- 浏览器录屏或截图存档
- 复杂页面自适应选择器框架
