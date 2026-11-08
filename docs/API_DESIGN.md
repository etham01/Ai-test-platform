# SmartTest API 设计

> 版本：v1.0（2026-11-03）
> Base URL：`http://127.0.0.1:8000`
> 统一前缀：`/api/v1`
> 文档：FastAPI 自动生成 `/docs`、`/openapi.json`
> 关联：`DATABASE_DESIGN.md`、`SECURITY.md`、`IMPLEMENTATION_PLAN.md`

---

## 1. 通用约定

### 1.1 统一响应格式

成功：
```json
{
  "success": true,
  "data": { },
  "error": null,
  "request_id": "req_01J..."
}
```

失败：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "项目不存在或无权访问",
    "details": null
  },
  "request_id": "req_01J..."
}
```

- `request_id` 同时写入响应头 `X-Request-ID`，便于日志排查。
- 业务错误码稳定、可枚举；`message` 为面向用户的中文摘要；`details` 可选（字段错误、冲突 ID 等）。
- 不把 traceback、SQL、密钥返回给前端。

### 1.2 HTTP 状态码

| 状态码 | 使用场景 |
| --- | --- |
| 200 | 查询/更新成功 |
| 201 | 创建成功 |
| 202 | 已创建异步任务（长任务） |
| 204 | 删除成功（无响应体） |
| 400 | 参数语义错误（非 Pydantic 字段级） |
| 401 | 可选 API Token 缺失/错误 |
| 403 | 项目越权/操作禁止 |
| 404 | 资源不存在（或不属于当前用户，避免枚举） |
| 409 | 状态冲突（脚本未校验、重复执行、配置缺失） |
| 422 | Pydantic 校验失败 |
| 429 | 上游限流或本地限流 |
| 500 | 未捕获内部错误 |
| 502 | LLM/浏览器/子进程上游失败 |
| 504 | 上游超时 |

### 1.3 分页

请求：`?page=1&page_size=20`
响应 `data`：
```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```
- `page` 从 1 开始；`page_size` 默认 20，最大 100。
- 列表接口只返回摘要字段，不返回 `content`/`traceback`/大 JSON。

### 1.4 时间与 ID

- 时间：ISO 8601 UTC，如 `2026-11-03T12:34:56.789Z`。
- ID：JSON number（BIGINT）。MVP 数值远小于 JS 安全整数；如未来超过 2^53，改为字符串并升版本。
- `task_id`：UUID 字符串。

### 1.5 项目归属与认证

- 所有嵌套资源以 `/projects/{project_id}/...` 开头；服务层必须校验项目存在、未删除、属于当前用户。
- 顶层资源（`/requirements/{id}`、`/test-cases/{id}`、`/test-scripts/{id}`、`/executions/{id}`、`/workflows/{id}`）通过资源反查 `project_id` 再校验归属。
- MVP 单用户：默认 `demo` 用户；不引入 OAuth。
- 可选 `SMARTTEST_API_TOKEN`：设置后，除 `/health` 外的 `/api/v1` 请求需带 `X-API-Token`；前端在本地存储 token。默认不设置，仅本地演示。
- API 默认绑定 `127.0.0.1`；不得在未加认证的情况下暴露到公网。

### 1.6 内容类型与大小限制

- 请求/响应 `application/json; charset=utf-8`。
- 默认请求体 ≤1 MB；需求正文 ≤64 KB；脚本 ≤60 KB；`storage_state` 上传 ≤1 MB。
- 文件下载使用 `Content-Disposition: attachment`（报告/脚本）；图片可 inline。
- 长任务不占用 HTTP 连接：返回 202 + `task_id`，前端轮询。

---

## 2. 错误码

| code | HTTP | 说明 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | 字段校验失败 |
| `UNAUTHORIZED` | 401 | 可选 token 缺失/错误 |
| `FORBIDDEN` | 403 | 无权访问该资源 |
| `PROJECT_NOT_FOUND` | 404 | 项目不存在/无权 |
| `PAGE_NOT_FOUND` | 404 | 页面不存在 |
| `REQUIREMENT_NOT_FOUND` | 404 | 需求不存在 |
| `WORKFLOW_NOT_FOUND` | 404 | 流程不存在 |
| `CASE_NOT_FOUND` | 404 | 用例不存在 |
| `SCRIPT_NOT_FOUND` | 404 | 脚本不存在 |
| `EXECUTION_NOT_FOUND` | 404 | 执行不存在 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `LLM_NOT_CONFIGURED` | 409 | 项目未配置可用 LLM |
| `LLM_AUTH_FAILED` | 502 | 上游 401/403（不回显 Key） |
| `LLM_TIMEOUT` | 504 | 上游超时 |
| `LLM_INVALID_OUTPUT` | 502 | 修复后仍无法解析 |
| `SCRIPT_NOT_VALIDATED` | 409 | 脚本未通过校验，不能执行 |
| `SCRIPT_VALIDATION_FAILED` | 422 | 校验失败（返回 issues） |
| `EXECUTION_CONFLICT` | 409 | 同一执行重复启动/已完成取消 |
| `TARGET_NOT_ALLOWED` | 403 | URL 不在授权范围/SSRF 拦截 |
| `UNSUPPORTED_BROWSER` | 400 | 浏览器类型/通道不可用 |
| `STORAGE_PATH_INVALID` | 400 | 文件路径非法 |
| `PAYLOAD_TOO_LARGE` | 413 | 超过大小限制 |
| `RATE_LIMITED` | 429 | 本地/上游限流 |
| `INTERNAL_ERROR` | 500 | 未捕获错误 |

---

## 3. 接口目录

> 标 `异步` 的接口返回 202 + `task_id`；长任务由 Celery 执行。

### 3.1 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 存活检查，不查依赖 |
| GET | `/api/v1/health/deps` | DB/Redis/浏览器可用性 |

`GET /health` → 200：
```json
{"status": "ok", "service": "smarttest-api", "version": "0.1.0"}
```

`GET /api/v1/health/deps` → 200：
```json
{
  "success": true,
  "data": {
    "database": {"ok": true, "latency_ms": 3},
    "redis": {"ok": true, "latency_ms": 1},
    "browser": {"ok": true, "channel": "chromium", "version": "..."}
  },
  "error": null,
  "request_id": "..."
}
```
依赖失败时返回 200 但 `ok=false`（便于前端展示），或 503；实现时统一为 200 + `ok` 字段，避免健康检查误杀。

### 3.2 项目

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/projects` | 创建 |
| GET | `/api/v1/projects` | 分页列表 |
| GET | `/api/v1/projects/{project_id}` | 详情 |
| PUT | `/api/v1/projects/{project_id}` | 更新 |
| DELETE | `/api/v1/projects/{project_id}` | 软删除 |
| GET | `/api/v1/projects/{project_id}/overview` | 统计概览 |

**POST /projects** 请求：
```json
{
  "name": "DemoShop",
  "description": "本地演示商城",
  "base_url": "http://127.0.0.1:8001",
  "browser_type": "chromium",
  "scan_config": {
    "max_pages": 8,
    "max_depth": 2,
    "timeout_seconds": 15,
    "total_timeout_seconds": 300,
    "wait_after_load_ms": 800
  }
}
```
响应 201：
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "DemoShop",
    "description": "本地演示商城",
    "base_url": "http://127.0.0.1:8001",
    "browser_type": "chromium",
    "scan_config": { "max_pages": 8, "max_depth": 2 },
    "status": "active",
    "created_at": "2026-11-03T12:00:00Z",
    "updated_at": "2026-11-03T12:00:00Z"
  },
  "error": null,
  "request_id": "req_..."
}
```

**GET /projects** 支持 `?status=active&page=1&page_size=20`。

**GET /projects/{id}/overview**：
```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "pages": 7,
    "relations": 12,
    "requirements": 2,
    "workflows": 1,
    "test_cases": 5,
    "validated_scripts": 3,
    "executions": 2,
    "last_execution": {"id": 1, "status": "passed", "created_at": "..."},
    "llm": {"provider": "mock", "model": "mock-v1", "is_mock": true, "configured": true}
  },
  "error": null,
  "request_id": "..."
}
```

### 3.3 LLM 配置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/llm-config` | 读取（脱敏） |
| PUT | `/api/v1/projects/{project_id}/llm-config` | 创建/更新 |
| POST | `/api/v1/projects/{project_id}/llm-config/test` | 测试连接 |

**GET** 响应：
```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "provider": "mock",
    "base_url": null,
    "model": "mock-v1",
    "configured": true,
    "key_hint": null,
    "temperature": 0.2,
    "timeout_seconds": 60,
    "max_retries": 2,
    "is_mock": true,
    "updated_at": "..."
  },
  "error": null,
  "request_id": "..."
}
```

**PUT** 请求（`api_key` 只写；省略表示保留原值）：
```json
{
  "provider": "openai_compatible",
  "base_url": "https://api.example.com/v1",
  "model": "example-model",
  "api_key": "sk-...",
  "temperature": 0.2,
  "timeout_seconds": 60,
  "max_retries": 2,
  "clear_api_key": false
}
```
响应不包含 `api_key`/密文，只返回 `configured` 与 `key_hint`。

**POST /test** 响应：
```json
{
  "success": true,
  "data": {
    "ok": true,
    "is_mock": false,
    "provider": "openai_compatible",
    "model": "example-model",
    "latency_ms": 842,
    "message": "连接成功"
  },
  "error": null,
  "request_id": "..."
}
```
Mock：
```json
{"ok": true, "is_mock": true, "provider": "mock", "model": "mock-v1", "latency_ms": 0, "message": "Mock 模式：不会调用真实模型"}
```

### 3.4 页面采集与探索

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/projects/{project_id}/pages/scan` | 单页采集（异步） |
| POST | `/api/v1/projects/{project_id}/pages/explore` | 多页 BFS（异步） |
| GET | `/api/v1/projects/{project_id}/pages` | 页面列表 |
| GET | `/api/v1/projects/{project_id}/pages/{page_id}` | 页面详情 + 元素 |
| GET | `/api/v1/projects/{project_id}/relations` | 页面关系 |
| GET | `/api/v1/projects/{project_id}/pages/{page_id}/screenshot` | 截图（图片） |
| GET | `/api/v1/projects/{project_id}/pages/{page_id}/dom` | DOM 快照（文本附件） |
| POST | `/api/v1/projects/{project_id}/auth/storage-state` | 上传登录态（P1） |
| DELETE | `/api/v1/projects/{project_id}/auth/storage-state` | 删除登录态（P1） |

**POST /pages/scan**：
```json
{"url": "http://127.0.0.1:8001/login"}
```
响应 202：
```json
{"success": true, "data": {"task_id": "c1...", "task_type": "scan"}, "error": null, "request_id": "..."}
```

**POST /pages/explore**：
```json
{
  "start_url": "http://127.0.0.1:8001/",
  "max_pages": 8,
  "max_depth": 2,
  "timeout_seconds": 15,
  "total_timeout_seconds": 300,
  "wait_after_load_ms": 800,
  "extra_urls": []
}
```
约束：
- `start_url` 默认项目 `base_url`；必须通过 URLPolicy。
- `max_pages` 1–50；`max_depth` 0–5；超时 5–120s。
- `extra_urls` 也必须同源/授权。

**GET /pages** 响应（摘要）：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "url": "http://127.0.0.1:8001/",
        "title": "DemoShop 首页",
        "depth": 0,
        "status": "parsed",
        "http_status": 200,
        "element_count": 12,
        "created_at": "..."
      }
    ],
    "total": 7,
    "page": 1,
    "page_size": 20
  },
  "error": null,
  "request_id": "..."
}
```

**GET /pages/{id}** 包含 `text_summary`、`elements`（最多 80 条）、`dom_snapshot_path` 的安全元数据（不直接返回文件路径给前端，返回可访问 URL）。

Element 示例：
```json
{
  "id": 10,
  "element_type": "input",
  "tag": "input",
  "role": "textbox",
  "accessible_name": "用户名",
  "label": "用户名",
  "placeholder": "请输入用户名",
  "text": null,
  "element_id": "username",
  "name": "username",
  "input_type": "text",
  "href": null,
  "selector_candidates": {
    "role": {"role": "textbox", "name": "用户名"},
    "label": "用户名",
    "placeholder": "请输入用户名",
    "css": "#username"
  },
  "is_sensitive": false
}
```
密码字段示例：`is_sensitive=true`，不返回值；`text` 为 null。

**GET /relations** 响应：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "from_page_id": 1,
        "to_page_id": 3,
        "target_url": "http://127.0.0.1:8001/products",
        "relation_type": "link",
        "source": "observed_link",
        "confidence": 1.0,
        "evidence": {"href": "/products", "text": "商品列表"}
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 100
  },
  "error": null,
  "request_id": "..."
}
```

### 3.5 测试需求

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/projects/{project_id}/requirements` | 创建 |
| GET | `/api/v1/projects/{project_id}/requirements` | 列表 |
| GET | `/api/v1/requirements/{requirement_id}` | 详情 |
| PUT | `/api/v1/requirements/{requirement_id}` | 更新 |
| DELETE | `/api/v1/requirements/{requirement_id}` | 软删除 |

请求：
```json
{
  "title": "登录与购物流程",
  "content": "验证用户使用正确密码登录、浏览商品、加入购物车并进入结算；错误密码应提示错误。",
  "related_page_ids": [2, 3, 4],
  "generation_config": {"max_cases": 5, "temperature": 0.2}
}
```

### 3.6 业务流程

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/projects/{project_id}/workflows/analyze` | 分析（异步） |
| GET | `/api/v1/projects/{project_id}/workflows` | 列表 |
| GET | `/api/v1/workflows/{workflow_id}` | 详情 |
| PUT | `/api/v1/workflows/{workflow_id}` | 编辑/确认 |
| DELETE | `/api/v1/workflows/{workflow_id}` | 软删除（P1） |

分析请求：
```json
{"requirement_id": 1, "page_ids": [1, 2, 3, 4], "force_refresh": false}
```
响应 202 `{task_id, task_type:"workflow_analysis"}`。

流程对象：
```json
{
  "id": 1,
  "name": "登录后浏览商品",
  "description": "用户从登录页进入商品列表并查看详情",
  "steps": [
    {"step_no": 1, "page_id": 2, "action": "goto", "target": "/login", "description": "打开登录页"},
    {"step_no": 2, "page_id": 2, "action": "fill", "target": "用户名", "value": "demo", "description": "输入用户名"},
    {"step_no": 3, "page_id": 3, "action": "assert", "target": "商品列表", "description": "登录成功"}
  ],
  "involved_page_ids": [2, 3],
  "uncertainty": "未提交表单，登录成功后的跳转由页面链接推断",
  "status": "inferred",
  "source": "mock",
  "needs_confirmation": true
}
```
`PUT` 可将 `status` 改为 `confirmed`/`edited`，并编辑 steps。

### 3.7 测试用例

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/test-cases` | 列表 |
| GET | `/api/v1/test-cases/{case_id}` | 详情 |
| PUT | `/api/v1/test-cases/{case_id}` | 编辑 |
| DELETE | `/api/v1/test-cases/{case_id}` | 软删除 |
| POST | `/api/v1/test-cases/{case_id}/regenerate` | 重新生成（P1，异步） |

列表过滤：`?requirement_id=&status=&priority=&page=&page_size=`。

用例对象示例见 `DATABASE_DESIGN.md` 的 steps/assertions。关键字段：
```json
{
  "id": 1,
  "case_code": "TC-001",
  "title": "正确密码登录成功",
  "module": "认证",
  "priority": "P0",
  "preconditions": ["已打开登录页"],
  "related_page_ids": [2, 3],
  "steps": [],
  "test_data": {"username": "demo", "password": "demo123"},
  "expected_result": "跳转至商品列表",
  "assertions": [],
  "assumptions": [],
  "status": "needs_review",
  "generation_source": "mock",
  "created_at": "..."
}
```

### 3.8 AI 生成

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/projects/{project_id}/ai/generate-cases` | 生成用例（异步） |
| POST | `/api/v1/projects/{project_id}/ai/generate-scripts` | 生成脚本（异步） |
| POST | `/api/v1/projects/{project_id}/ai/analyze-failure` | 失败分析（异步） |
| GET | `/api/v1/projects/{project_id}/ai/generation-records` | 生成记录 |

**生成用例**：
```json
{
  "requirement_id": 1,
  "page_ids": [1, 2, 3, 4],
  "max_cases": 5,
  "temperature": 0.2,
  "include_workflow_ids": [1]
}
```
响应 202 `{task_id, task_type:"case_generation"}`；任务 `result` 包含 `case_ids`、`count`、`warnings`。

**生成脚本**：
```json
{"test_case_ids": [1, 2], "style": "one_file_per_case"}
```
响应 202；任务 `result` 包含 `script_ids`、`rejected` 列表。

**失败分析**：
```json
{"execution_id": 1, "result_id": 3}
```
响应 202；任务 `result` 包含 `analysis` 摘要。

**生成记录**：
```json
{
  "items": [
    {
      "id": 10,
      "task_type": "case_generation",
      "prompt_version": "v1",
      "provider": "mock",
      "model": "mock-v1",
      "is_mock": true,
      "status": "succeeded",
      "duration_ms": 12,
      "prompt_tokens": null,
      "completion_tokens": null,
      "created_at": "..."
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 3.9 脚本

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/test-scripts` | 列表 |
| GET | `/api/v1/test-scripts/{script_id}` | 详情（含 content） |
| PUT | `/api/v1/test-scripts/{script_id}` | 编辑 → 新版本 + 重新校验 |
| POST | `/api/v1/test-scripts/{script_id}/validate` | 重新校验 |
| GET | `/api/v1/test-scripts/{script_id}/download` | 下载 `.py` |
| DELETE | `/api/v1/test-scripts/{script_id}` | 软删除（P1） |

列表过滤：`?test_case_id=&status=`。

脚本详情：
```json
{
  "id": 1,
  "test_case_id": 1,
  "version": 1,
  "filename": "tc_001_v1.py",
  "status": "validated",
  "generation_source": "mock",
  "validation_report": {"ok": true, "issues": []},
  "content": "import pytest\nfrom playwright.sync_api import expect\n...",
  "created_at": "..."
}
```

编辑请求：
```json
{"content": "import pytest\n..."}
```
响应 200，返回新版本对象；若校验失败，`status=rejected` 且 `validation_report.issues` 有明细，仍保存为新版本（用户可继续编辑）。

### 3.10 执行与报告

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/projects/{project_id}/executions` | 创建执行（异步） |
| GET | `/api/v1/projects/{project_id}/executions` | 执行列表 |
| GET | `/api/v1/executions/{execution_id}` | 执行详情 |
| GET | `/api/v1/executions/{execution_id}/results` | 逐条结果 |
| GET | `/api/v1/executions/{execution_id}/report` | HTML 报告 |
| GET | `/api/v1/executions/{execution_id}/log` | 执行日志（文本） |
| POST | `/api/v1/executions/{execution_id}/cancel` | 取消 |
| GET | `/api/v1/test-results/{result_id}/screenshot` | 失败截图 |

**创建执行**：
```json
{
  "script_ids": [1, 2],
  "timeout_seconds": 120,
  "mode": "local"
}
```
校验：
- 脚本属于项目且 `status=validated`；否则 409 `SCRIPT_NOT_VALIDATED`。
- `mode=docker` 时若 Docker 不可用，返回 409/503，**不回退**到本地。
- 返回 202：
```json
{"success": true, "data": {"execution_id": 1, "task_id": "..."}, "error": null, "request_id": "..."}
```

**执行详情**：
```json
{
  "id": 1,
  "project_id": 1,
  "status": "failed",
  "mode": "local",
  "timeout_seconds": 120,
  "total": 2,
  "passed": 1,
  "failed": 1,
  "skipped": 0,
  "errors": 0,
  "started_at": "...",
  "finished_at": "...",
  "report_url": "/api/v1/executions/1/report",
  "log_url": "/api/v1/executions/1/log",
  "error_message": null
}
```

**结果**：
```json
{
  "items": [
    {
      "id": 3,
      "script_id": 2,
      "test_case_id": 2,
      "test_name": "test_login_success",
      "status": "passed",
      "duration_ms": 1820,
      "failure_message": null,
      "traceback": null,
      "screenshot_url": null,
      "failure_analysis": null
    },
    {
      "id": 4,
      "script_id": 3,
      "test_case_id": 3,
      "test_name": "test_wrong_password",
      "status": "failed",
      "duration_ms": 1510,
      "failure_message": "Expected title ...",
      "traceback": "...",
      "screenshot_url": "/api/v1/test-results/4/screenshot",
      "failure_analysis": null
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 50
}
```

**报告下载**：`GET /executions/{id}/report` → `text/html`，`Content-Disposition: attachment; filename="smarttest-execution-1.html"`。前端可用 blob 下载或新窗口打开；报告内容视为不可信（可能含页面文本），不在主应用 DOM 中直接注入。

**取消**：`POST /executions/{id}/cancel` → 200 `{status:"cancelling"}`；重复取消幂等；已完成返回 409 或 200 带当前状态（实现时选幂等 200）。

### 3.11 任务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/tasks/{task_id}` | 任务状态/进度 |
| GET | `/api/v1/tasks/{task_id}/logs` | 任务日志（最近 200 条） |
| POST | `/api/v1/tasks/{task_id}/cancel` | 取消任务 |

任务对象：
```json
{
  "task_id": "c1...",
  "project_id": 1,
  "task_type": "explore",
  "status": "running",
  "progress": 50,
  "message": "已采集 4/8 个页面",
  "result": null,
  "error": null,
  "cancel_requested": false,
  "started_at": "...",
  "finished_at": null,
  "created_at": "..."
}
```
终态：`succeeded/failed/cancelled`；前端轮询 1.5–2 s，终态停止。

**日志**：
```json
{"items": [{"level": "info", "message": "采集页面 http://...", "created_at": "..."}], "total": 12}
```

**取消**：
- 设置 `cancel_requested=true`；Scan/生成任务在步骤边界检查；执行任务由 runner 杀进程树。
- 若任务已完成，返回 200 + 当前状态（幂等）或 409；文档选幂等 200。

---

## 4. OpenAPI 与前端类型

- FastAPI 自动生成 `/openapi.json`；每个请求/响应使用 Pydantic Schema。
- 前端使用 `openapi-typescript` 生成 `src/types/openapi.d.ts`：
```bash
pnpm --dir frontend add -D openapi-typescript
pnpm --dir frontend exec openapi-typescript http://127.0.0.1:8000/openapi.json -o src/types/openapi.d.ts
```
- 在 `src/types/api.ts` 中导出领域别名（`Project`、`Page`、`TestCase` 等），API client 使用这些类型。
- 生成物入库；后端 schema 变更时重新生成并提交，避免手写漂移。

---

## 5. 版本与兼容性

- 路径版本 `/api/v1`；破坏性变更升 `/api/v2`。
- 字段新增向后兼容；字段删除/重命名需版本升级。
- 错误码稳定；`message` 可变。
- `task_id` 格式稳定为 UUID；不要依赖 Celery task id。
- 文件 URL 由服务端生成，不把物理路径暴露给前端。

---

## 6. API 验收清单

- [ ] 所有列表分页、过滤、项目隔离。
- [ ] 所有长任务返回 202 + task_id，并有任务/日志/取消接口。
- [ ] 所有错误返回统一 envelope + request_id。
- [ ] LLM Key 不回传、不写日志。
- [ ] 脚本未校验不能执行。
- [ ] 报告/截图/日志下载校验项目归属与路径。
- [ ] OpenAPI 可打开，关键 schema 完整。
- [ ] 前端类型由 OpenAPI 生成或与 schema 对齐。
