# SmartTest 数据库设计

> 版本：v1.0（2026-11-03）
> 目标数据库：MySQL 8.0（Compose）/ MySQL 9.4（本机开发）
> ORM：SQLAlchemy 2.x；迁移：Alembic；驱动：PyMySQL + cryptography
> 字符集：`utf8mb4`；排序规则：`utf8mb4_0900_ai_ci`；时间：UTC

---

## 1. 设计约定

| 约定 | 说明 |
| --- | --- |
| 主键 | `BIGINT AUTO_INCREMENT`，命名为 `id` |
| 业务任务 ID | `async_tasks.task_id CHAR(36)`（UUID），对前端暴露 |
| 时间 | `DATETIME(6)`，应用层统一写 UTC；MySQL 会话 `time_zone='+00:00'` |
| 布尔 | `BOOLEAN`（MySQL `TINYINT(1)`） |
| 枚举 | `VARCHAR(32)` + 应用层 Python Enum 校验，不用 MySQL ENUM（便于迁移） |
| JSON | MySQL `JSON`；只存结构化、大小可控的数据；应用层限制大小 |
| 大文本 | `TEXT/MEDIUMTEXT/LONGTEXT`，应用层截断；DOM/截图/报告存文件 |
| 软删除 | `deleted_at DATETIME(6) NULL`；查询默认 `deleted_at IS NULL` |
| 外键 | 默认 `ON DELETE RESTRICT`；项目/用例/脚本软删除，保留执行历史 |
| 命名 | 表复数 snake_case；外键 `<table>_id`；索引 `idx_...`；唯一 `uq_...` |
| 项目隔离 | 所有领域表带 `project_id`；查询必须同时校验 `project_id` |
| ID 精度 | 前端 JS 安全整数为 2^53-1；MVP 自增 ID 远小于该值；文档保留该限制 |

### 1.1 时间与时区

- Python 使用 `datetime.now(timezone.utc)`；MySQL 连接设置 `time_zone='+00:00'`。
- API 输出 ISO 8601，带 `Z` 或 `+00:00`；前端按本地时区展示。
- 不使用 MySQL `TIMESTAMP` 的自动时区转换，统一 `DATETIME(6)` 存 UTC。

### 1.2 软删除与唯一约束

- `projects`、`test_requirements`、`workflows`、`test_cases`、`test_scripts` 支持软删除。
- 唯一约束不会因为软删除自动释放：
  - `test_cases(project_id, case_code)`：重新生成时若冲突，追加 `-R2` 等后缀；
  - `web_pages(project_id, url_hash)`：页面不软删除，重新采集时更新；
  - `test_scripts(test_case_id, version)`：版本只增不减。
- 项目硬删除默认关闭（`ALLOW_HARD_DELETE=false`），避免误删执行历史。

---

## 2. ER 图

```mermaid
erDiagram
    users ||--o{ projects : owns
    projects ||--o| llm_configs : configures
    projects ||--o{ web_pages : contains
    web_pages ||--o{ page_elements : has
    web_pages ||--o{ page_relations : from_page
    web_pages ||--o{ page_relations : to_page
    projects ||--o{ test_requirements : contains
    projects ||--o{ workflows : contains
    test_requirements ||--o{ workflows : informs
    test_requirements ||--o{ test_cases : derives
    projects ||--o{ test_cases : contains
    test_cases ||--o{ test_scripts : generates
    projects ||--o{ test_scripts : contains
    projects ||--o{ test_executions : runs
    test_executions ||--o{ execution_scripts : includes
    test_scripts ||--o{ execution_scripts : selected
    test_executions ||--o{ test_results : yields
    test_scripts ||--o{ test_results : produces
    test_cases ||--o{ test_results : traces
    projects ||--o{ async_tasks : tracks
    async_tasks ||--o{ async_task_logs : logs
    projects ||--o{ generation_records : records

    users {
      bigint id PK
      varchar username UK
      varchar display_name
      boolean is_active
      datetime created_at
      datetime updated_at
    }
    projects {
      bigint id PK
      bigint owner_id FK
      varchar name
      text description
      varchar base_url
      varchar browser_type
      json scan_config
      varchar status
      datetime deleted_at
    }
    llm_configs {
      bigint id PK
      bigint project_id FK "unique per project"
      varchar provider
      varchar base_url
      varchar model
      text api_key_encrypted
      varchar api_key_hint
      decimal temperature
      int timeout_seconds
      int max_retries
      boolean is_active
    }
    web_pages {
      bigint id PK
      bigint project_id FK
      varchar url
      varchar normalized_url
      char url_hash
      varchar title
      int depth
      varchar status
      int http_status
      text text_summary
      varchar dom_snapshot_path
      varchar screenshot_path
      bigint discovered_from_page_id FK
      varchar source
      text error_message
    }
    page_elements {
      bigint id PK
      bigint project_id FK
      bigint page_id FK
      varchar element_type
      varchar tag
      varchar role
      varchar accessible_name
      varchar label
      varchar placeholder
      varchar text
      varchar element_id
      varchar name
      varchar input_type
      text href
      json selector_candidates
      boolean is_sensitive
      json attributes
    }
    page_relations {
      bigint id PK
      bigint project_id FK
      bigint from_page_id FK
      bigint to_page_id FK
      varchar target_url
      varchar relation_type
      varchar source
      float confidence
      json evidence
    }
    test_requirements {
      bigint id PK
      bigint project_id FK
      varchar title
      mediumtext content
      json related_page_ids
      json generation_config
      varchar status
      datetime deleted_at
    }
    workflows {
      bigint id PK
      bigint project_id FK
      bigint requirement_id FK
      varchar name
      text description
      json steps
      json involved_page_ids
      text uncertainty
      varchar status
      varchar source
      bigint generation_record_id FK
      datetime deleted_at
    }
    test_cases {
      bigint id PK
      bigint project_id FK
      bigint requirement_id FK
      varchar case_code
      varchar title
      varchar module
      varchar priority
      json preconditions
      json related_page_ids
      json steps
      json test_data
      text expected_result
      json assertions
      json assumptions
      varchar status
      varchar generation_source
      bigint generation_record_id FK
      datetime deleted_at
    }
    test_scripts {
      bigint id PK
      bigint project_id FK
      bigint test_case_id FK
      int version
      varchar filename
      longtext content
      char content_hash
      varchar status
      json validation_report
      varchar generation_source
      bigint generation_record_id FK
    }
    test_executions {
      bigint id PK
      bigint project_id FK
      varchar status
      varchar mode
      int timeout_seconds
      int total
      int passed
      int failed
      int skipped
      int errors
      datetime started_at
      datetime finished_at
      varchar report_path
      varchar log_path
      text error_message
      varchar celery_task_id
      bigint created_by FK
    }
    execution_scripts {
      bigint id PK
      bigint execution_id FK
      bigint script_id FK
    }
    test_results {
      bigint id PK
      bigint execution_id FK
      bigint project_id FK
      bigint script_id FK
      bigint test_case_id FK
      varchar node_id
      varchar test_name
      varchar status
      int duration_ms
      text failure_message
      mediumtext traceback
      varchar screenshot_path
      json failure_analysis
      bigint analysis_generation_record_id FK
    }
    async_tasks {
      bigint id PK
      char task_id UK
      bigint project_id FK
      varchar task_type
      varchar status
      int progress
      varchar message
      json result
      text error
      varchar celery_task_id
      boolean cancel_requested
      datetime started_at
      datetime finished_at
    }
    async_task_logs {
      bigint id PK
      bigint async_task_ref_id FK
      varchar level
      varchar message
      datetime created_at
    }
    generation_records {
      bigint id PK
      bigint project_id FK
      varchar task_type
      varchar prompt_version
      varchar provider
      varchar model
      boolean is_mock
      text input_summary
      text output_summary
      varchar raw_response_path
      int prompt_tokens
      int completion_tokens
      int duration_ms
      varchar status
      text error
    }
```

> Mermaid 的字段列表是摘要；完整约束以第 4 节表结构为准。

---

## 3. 枚举值

| 枚举 | 值 | 使用处 |
| --- | --- | --- |
| `ProjectStatus` | `active`, `archived` | projects.status |
| `TaskType` | `scan`, `explore`, `workflow_analysis`, `case_generation`, `script_generation`, `execution`, `failure_analysis` | async_tasks.task_type |
| `TaskStatus` | `queued`, `running`, `succeeded`, `failed`, `cancelled` | async_tasks.status |
| `PageStatus` | `discovered`, `parsed`, `failed`, `blocked` | web_pages.status |
| `PageSource` | `start`, `link`, `manual` | web_pages.source |
| `RelationType` | `link`, `navigation`, `form_action`, `redirect`, `inferred_flow` | page_relations.relation_type |
| `RelationSource` | `observed_link`, `observed_navigation`, `observed_form_action`, `observed_redirect`, `model_inferred` | page_relations.source |
| `RequirementStatus` | `draft`, `active`, `archived` | test_requirements.status |
| `WorkflowStatus` | `inferred`, `confirmed`, `edited`, `archived` | workflows.status |
| `WorkflowSource` | `llm`, `mock`, `user` | workflows.source |
| `CaseStatus` | `draft`, `needs_review`, `confirmed`, `archived` | test_cases.status |
| `GenerationSource` | `llm`, `mock`, `user` | test_cases/test_scripts/workflows |
| `ScriptStatus` | `draft`, `validated`, `rejected`, `archived` | test_scripts.status |
| `ExecutionStatus` | `pending`, `running`, `passed`, `failed`, `error`, `timeout`, `cancelled` | test_executions.status |
| `ExecutionMode` | `local`, `docker` | test_executions.mode |
| `ResultStatus` | `passed`, `failed`, `error`, `skipped` | test_results.status |
| `Priority` | `P0`, `P1`, `P2`, `P3` | test_cases.priority |
| `AssertionSource` | `user_requirement`, `observed_page`, `model_inference` | assertions JSON |
| `LLMProvider` | `openai_compatible`, `mock` | llm_configs.provider |

---

## 4. 表结构

### 4.1 `users`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK, AUTO_INCREMENT | 用户 ID |
| username | VARCHAR(64) | NOT NULL, UNIQUE | 登录名；MVP 种子 `demo` |
| display_name | VARCHAR(128) | NOT NULL | 显示名 |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | 是否启用 |
| created_at | DATETIME(6) | NOT NULL | UTC |
| updated_at | DATETIME(6) | NOT NULL | UTC |

索引：`uq_users_username(username)`。

种子：迁移插入 `id=1, username='demo', display_name='演示用户'`（幂等）。MVP 单用户；未来多用户时保留 `owner_id`。

### 4.2 `projects`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | 项目 ID |
| owner_id | BIGINT | FK users.id, NOT NULL | 所有者 |
| name | VARCHAR(128) | NOT NULL | 项目名 |
| description | TEXT | NULL | 描述 |
| base_url | VARCHAR(2048) | NOT NULL | 授权起始 URL |
| browser_type | VARCHAR(32) | NOT NULL DEFAULT 'chromium' | chromium/chrome |
| scan_config | JSON | NULL | 默认采集参数 |
| status | VARCHAR(32) | NOT NULL DEFAULT 'active' | active/archived |
| created_at | DATETIME(6) | NOT NULL | UTC |
| updated_at | DATETIME(6) | NOT NULL | UTC |
| deleted_at | DATETIME(6) | NULL | 软删除 |

索引：`idx_projects_owner(owner_id)`、`idx_projects_deleted(deleted_at)`。

`scan_config` 示例：
```json
{
  "max_pages": 8,
  "max_depth": 2,
  "timeout_seconds": 15,
  "total_timeout_seconds": 300,
  "wait_after_load_ms": 800,
  "include_patterns": [],
  "exclude_patterns": ["/logout", "/download"]
}
```

### 4.3 `llm_configs`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, UNIQUE, NOT NULL | 一项目一配置 |
| provider | VARCHAR(32) | NOT NULL | openai_compatible/mock |
| base_url | VARCHAR(512) | NULL | 兼容 API 根地址；mock 可为空 |
| model | VARCHAR(128) | NOT NULL | 模型名；mock 为 `mock-v1` |
| api_key_encrypted | TEXT | NULL | Fernet 密文；绝不返回 |
| api_key_hint | VARCHAR(16) | NULL | 末 4 位提示 |
| temperature | DECIMAL(3,2) | NOT NULL DEFAULT 0.20 | 0.00–2.00 |
| timeout_seconds | INT | NOT NULL DEFAULT 60 | 调用超时 |
| max_retries | INT | NOT NULL DEFAULT 2 | 有限重试 |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |

索引：`uq_llm_configs_project(project_id)`。

**安全**：API Key 用 Fernet 加密；密钥来自 `SMARTTEST_SECRET_KEY`（生产）或 `.dev/secret.key`（开发，gitignored）。`GET` 只返回 `configured`、`key_hint`、`provider`、`model`、`is_mock`。

### 4.4 `web_pages`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| url | VARCHAR(2048) | NOT NULL | 原始 URL（截断） |
| normalized_url | VARCHAR(2048) | NOT NULL | 规范化 URL |
| url_hash | CHAR(64) | NOT NULL | SHA-256(normalized_url) |
| title | VARCHAR(512) | NULL | 页面标题 |
| depth | INT | NOT NULL DEFAULT 0 | BFS 深度 |
| status | VARCHAR(32) | NOT NULL | discovered/parsed/failed/blocked |
| http_status | INT | NULL | HTTP 状态码 |
| content_type | VARCHAR(128) | NULL | |
| text_summary | TEXT | NULL | 页面文本摘要，≤8 KB |
| dom_snapshot_path | VARCHAR(512) | NULL | 相对 storage 路径 |
| screenshot_path | VARCHAR(512) | NULL | 相对 storage 路径 |
| discovered_from_page_id | BIGINT | FK web_pages.id, NULL | 发现来源 |
| source | VARCHAR(32) | NOT NULL | start/link/manual |
| error_message | TEXT | NULL | 脱敏错误 |
| fetched_at | DATETIME(6) | NULL | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |

索引：`uq_web_pages_project_url(project_id, url_hash)`、`idx_web_pages_project(project_id)`、`idx_web_pages_status(status)`。

**重复采集策略**：按 `(project_id, url_hash)` upsert；更新标题/摘要/路径/状态，不新增重复行。

### 4.5 `page_elements`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | 冗余便于隔离查询 |
| page_id | BIGINT | FK web_pages.id, NOT NULL | |
| element_type | VARCHAR(32) | NOT NULL | link/button/input/select/textarea/form/other |
| tag | VARCHAR(32) | NOT NULL | a/button/input... |
| role | VARCHAR(64) | NULL | ARIA role |
| accessible_name | VARCHAR(512) | NULL | aria-label/可访问名 |
| label | VARCHAR(512) | NULL | 关联 label |
| placeholder | VARCHAR(512) | NULL | |
| text | VARCHAR(1024) | NULL | 可见文本（脱敏/截断） |
| element_id | VARCHAR(256) | NULL | DOM id |
| name | VARCHAR(256) | NULL | form name |
| input_type | VARCHAR(64) | NULL | password/email/text... |
| href | TEXT | NULL | 链接地址（截断） |
| selector_candidates | JSON | NULL | 定位候选 |
| is_sensitive | BOOLEAN | NOT NULL DEFAULT FALSE | 密码/邮箱/电话/支付字段 |
| attributes | JSON | NULL | 白名单属性（不含 value） |
| created_at | DATETIME(6) | NOT NULL | |

索引：`idx_page_elements_page(page_id)`、`idx_page_elements_project(project_id)`、`idx_page_elements_type(element_type)`。

`selector_candidates` 示例：
```json
{
  "role": {"role": "button", "name": "加入购物车"},
  "label": "用户名",
  "placeholder": "请输入用户名",
  "text": "登录",
  "css": "#login-form button[type=submit]",
  "test_id": "login-submit"
}
```

**敏感字段**：`input[type=password]`、`autocomplete=cc-*`、name/id 含 password/token/secret、email/tel 字段标记 `is_sensitive=true`；不采集 `value`；文本摘要做邮箱/手机号脱敏。

### 4.6 `page_relations`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| from_page_id | BIGINT | FK web_pages.id, NOT NULL | |
| to_page_id | BIGINT | FK web_pages.id, NULL | 目标未采集时为 NULL |
| target_url | VARCHAR(2048) | NULL | 未解析/外域目标 |
| relation_type | VARCHAR(32) | NOT NULL | link/navigation/form_action/redirect/inferred_flow |
| source | VARCHAR(32) | NOT NULL | observed_*/model_inferred |
| confidence | FLOAT | NOT NULL DEFAULT 1.0 | 0–1 |
| evidence | JSON | NULL | href/text/form action/method |
| created_at | DATETIME(6) | NOT NULL | |

索引：`idx_page_relations_from(from_page_id)`、`idx_page_relations_to(to_page_id)`、`idx_page_relations_project(project_id)`。

去重：应用层按 `(from_page_id, COALESCE(to_page_id, 0), target_url, relation_type, source)` 判重；LLM 推断边单独存 `model_inferred`，不与观察边混淆。

### 4.7 `test_requirements`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| title | VARCHAR(256) | NOT NULL | |
| content | MEDIUMTEXT | NOT NULL | 原始需求文本（≤64 KB） |
| related_page_ids | JSON | NULL | 页面 ID 数组 |
| generation_config | JSON | NULL | 生成参数（温度/条数等） |
| status | VARCHAR(32) | NOT NULL DEFAULT 'draft' | draft/active/archived |
| created_by | BIGINT | FK users.id, NULL | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |
| deleted_at | DATETIME(6) | NULL | |

索引：`idx_requirements_project(project_id)`、`idx_requirements_deleted(deleted_at)`。

### 4.8 `workflows`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| requirement_id | BIGINT | FK test_requirements.id, NULL | |
| name | VARCHAR(256) | NOT NULL | |
| description | TEXT | NULL | |
| steps | JSON | NOT NULL | 流程步骤 |
| involved_page_ids | JSON | NULL | 涉及页面 |
| uncertainty | TEXT | NULL | 不确定点 |
| status | VARCHAR(32) | NOT NULL DEFAULT 'inferred' | inferred/confirmed/edited/archived |
| source | VARCHAR(32) | NOT NULL | llm/mock/user |
| generation_record_id | BIGINT | FK generation_records.id, NULL | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |
| deleted_at | DATETIME(6) | NULL | |

索引：`idx_workflows_project(project_id)`、`idx_workflows_status(status)`。

`steps` 示例：
```json
[
  {"step_no": 1, "page_id": 3, "action": "goto", "target": "/login", "description": "打开登录页"},
  {"step_no": 2, "page_id": 3, "action": "fill", "target": "用户名", "value": "demo", "description": "输入用户名"},
  {"step_no": 3, "page_id": 3, "action": "click", "target": "登录", "description": "提交登录"},
  {"step_no": 4, "page_id": 4, "action": "assert", "target": "商品列表标题", "description": "确认登录成功"}
]
```

### 4.9 `test_cases`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| requirement_id | BIGINT | FK test_requirements.id, NULL | |
| case_code | VARCHAR(64) | NOT NULL | 项目内唯一，如 `TC-001` |
| title | VARCHAR(512) | NOT NULL | |
| module | VARCHAR(128) | NULL | |
| priority | VARCHAR(16) | NOT NULL DEFAULT 'P2' | P0–P3 |
| preconditions | JSON | NULL | 字符串数组 |
| related_page_ids | JSON | NULL | 页面 ID 数组 |
| steps | JSON | NOT NULL | 至少 1 步 |
| test_data | JSON | NULL | 结构化测试数据 |
| expected_result | TEXT | NULL | 总预期 |
| assertions | JSON | NOT NULL | 断言数组 |
| assumptions | JSON | NULL | 假设/待确认项 |
| status | VARCHAR(32) | NOT NULL DEFAULT 'draft' | draft/needs_review/confirmed/archived |
| generation_source | VARCHAR(32) | NOT NULL DEFAULT 'user' | llm/mock/user |
| generation_record_id | BIGINT | FK generation_records.id, NULL | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |
| deleted_at | DATETIME(6) | NULL | |

唯一：`uq_test_cases_project_code(project_id, case_code)`；索引 `idx_test_cases_project(project_id)`、`idx_test_cases_requirement(requirement_id)`、`idx_test_cases_status(status)`。

`steps` 示例：
```json
[
  {"step_no": 1, "page_reference": "3", "action": "goto", "target": "/login", "value": null, "description": "打开登录页"},
  {"step_no": 2, "page_reference": "3", "action": "fill", "target": "用户名", "value": "demo", "description": "输入用户名"},
  {"step_no": 3, "page_reference": "3", "action": "fill", "target": "密码", "value": "demo123", "description": "输入密码"},
  {"step_no": 4, "page_reference": "3", "action": "click", "target": "登录", "value": null, "description": "提交"},
  {"step_no": 5, "page_reference": "4", "action": "assert", "target": "页面标题", "value": "商品列表", "description": "登录成功"}
]
```

`assertions` 示例：
```json
[
  {"assertion_type": "url", "target": "current_url", "expected": "/products", "source": "user_requirement", "confidence": 0.9},
  {"assertion_type": "element_visible", "target": "商品列表", "expected": true, "source": "observed_page", "confidence": 1.0}
]
```

### 4.10 `test_scripts`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| test_case_id | BIGINT | FK test_cases.id, NOT NULL | |
| version | INT | NOT NULL | 从 1 递增 |
| filename | VARCHAR(256) | NOT NULL | 安全文件名，如 `tc_001_v1.py` |
| content | TEXT | NOT NULL | 脚本内容，应用层 ≤60 KB |
| content_hash | CHAR(64) | NOT NULL | SHA-256 |
| status | VARCHAR(32) | NOT NULL | draft/validated/rejected/archived |
| validation_report | JSON | NULL | issues 数组 |
| generation_source | VARCHAR(32) | NOT NULL | llm/mock/user |
| generation_record_id | BIGINT | FK generation_records.id, NULL | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |

唯一：`uq_test_scripts_case_version(test_case_id, version)`；索引 `idx_test_scripts_project(project_id)`、`idx_test_scripts_status(status)`。

脚本文件同时写入 `storage/projects/{project_id}/scripts/{script_id}/v{version}.py`；DB 内容为事实来源，工作区执行时以 DB 内容重新落盘。

### 4.11 `test_executions`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| status | VARCHAR(32) | NOT NULL | pending/running/passed/failed/error/timeout/cancelled |
| mode | VARCHAR(16) | NOT NULL | local/docker |
| timeout_seconds | INT | NOT NULL DEFAULT 120 | 运行超时 |
| total | INT | NOT NULL DEFAULT 0 | |
| passed | INT | NOT NULL DEFAULT 0 | |
| failed | INT | NOT NULL DEFAULT 0 | |
| skipped | INT | NOT NULL DEFAULT 0 | |
| errors | INT | NOT NULL DEFAULT 0 | |
| started_at | DATETIME(6) | NULL | |
| finished_at | DATETIME(6) | NULL | |
| report_path | VARCHAR(512) | NULL | 相对 storage |
| log_path | VARCHAR(512) | NULL | 相对 storage |
| error_message | TEXT | NULL | 脱敏摘要 |
| celery_task_id | VARCHAR(64) | NULL | |
| created_by | BIGINT | FK users.id, NULL | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |

索引：`idx_executions_project(project_id)`、`idx_executions_status(status)`、`idx_executions_created(created_at)`。

### 4.12 `execution_scripts`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| execution_id | BIGINT | FK test_executions.id, NOT NULL | |
| script_id | BIGINT | FK test_scripts.id, NOT NULL | |
| created_at | DATETIME(6) | NOT NULL | |

唯一：`uq_execution_scripts(execution_id, script_id)`；索引 `idx_execution_scripts_script(script_id)`。

### 4.13 `test_results`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| execution_id | BIGINT | FK test_executions.id, NOT NULL | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| script_id | BIGINT | FK test_scripts.id, NULL | |
| test_case_id | BIGINT | FK test_cases.id, NULL | |
| node_id | VARCHAR(512) | NULL | pytest node id |
| test_name | VARCHAR(512) | NOT NULL | |
| status | VARCHAR(32) | NOT NULL | passed/failed/error/skipped |
| duration_ms | INT | NULL | |
| failure_message | TEXT | NULL | 首段失败信息 |
| traceback | MEDIUMTEXT | NULL | 截断 traceback |
| screenshot_path | VARCHAR(512) | NULL | 相对 storage |
| failure_analysis | JSON | NULL | 观察/推断/建议 |
| analysis_generation_record_id | BIGINT | FK generation_records.id, NULL | |
| created_at | DATETIME(6) | NOT NULL | |

索引：`idx_results_execution(execution_id)`、`idx_results_status(status)`、`idx_results_script(script_id)`。

### 4.14 `async_tasks`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| task_id | CHAR(36) | NOT NULL, UNIQUE | UUID，前端使用 |
| project_id | BIGINT | FK projects.id, NULL | 全局任务可为空 |
| task_type | VARCHAR(32) | NOT NULL | 见枚举 |
| status | VARCHAR(32) | NOT NULL | queued/running/succeeded/failed/cancelled |
| progress | INT | NOT NULL DEFAULT 0 | 0–100 |
| message | VARCHAR(1024) | NULL | 当前步骤 |
| result | JSON | NULL | 结果摘要/资源 ID |
| error | TEXT | NULL | 脱敏错误 |
| celery_task_id | VARCHAR(64) | NULL | |
| cancel_requested | BOOLEAN | NOT NULL DEFAULT FALSE | |
| started_at | DATETIME(6) | NULL | |
| finished_at | DATETIME(6) | NULL | |
| created_at | DATETIME(6) | NOT NULL | |
| updated_at | DATETIME(6) | NOT NULL | |

索引：`uq_async_tasks_task_id(task_id)`、`idx_async_tasks_project(project_id)`、`idx_async_tasks_status(status)`、`idx_async_tasks_created(created_at)`。

### 4.15 `async_task_logs`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| async_task_ref_id | BIGINT | FK async_tasks.id, NOT NULL | |
| level | VARCHAR(16) | NOT NULL | info/warning/error |
| message | VARCHAR(2048) | NOT NULL | 脱敏 |
| created_at | DATETIME(6) | NOT NULL | |

索引：`idx_task_logs_task(async_task_ref_id)`、`idx_task_logs_created(created_at)`。

**上限**：每任务最多 500 条；超过后丢弃旧日志或截断；详细日志写文件。

### 4.16 `generation_records`

| 列 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PK | |
| project_id | BIGINT | FK projects.id, NOT NULL | |
| task_type | VARCHAR(32) | NOT NULL | workflow/case/script/failure |
| prompt_version | VARCHAR(32) | NOT NULL | 如 `v1` |
| provider | VARCHAR(32) | NOT NULL | openai_compatible/mock |
| model | VARCHAR(128) | NOT NULL | |
| is_mock | BOOLEAN | NOT NULL DEFAULT FALSE | UI 区分 |
| input_summary | TEXT | NULL | 输入摘要（脱敏/截断） |
| output_summary | TEXT | NULL | 输出摘要（截断） |
| raw_response_path | VARCHAR(512) | NULL | 原始响应文件（脱敏/截断） |
| prompt_tokens | INT | NULL | 若 API 返回 |
| completion_tokens | INT | NULL | 若 API 返回 |
| duration_ms | INT | NULL | |
| status | VARCHAR(32) | NOT NULL | succeeded/failed |
| error | TEXT | NULL | 脱敏 |
| created_at | DATETIME(6) | NOT NULL | |

索引：`idx_generation_project(project_id)`、`idx_generation_type(task_type)`、`idx_generation_created(created_at)`。

---

## 5. JSON 结构契约

### 5.1 测试步骤（`test_cases.steps`）

```json
{
  "step_no": 1,
  "page_reference": "3",
  "action": "goto|fill|click|select|check|uncheck|press|wait|assert|custom",
  "target": "用户名",
  "value": "demo",
  "description": "输入用户名"
}
```

约束：
- `step_no` 从 1 连续递增；
- `action` 在允许集合内；
- `goto/fill/click` 必须有非空 `target`；
- `page_reference` 可为页面 ID 字符串或页面 URL；服务层校验属于项目。

### 5.2 断言（`test_cases.assertions`）

```json
{
  "assertion_type": "url|title|text|element_visible|element_text|value|count|custom",
  "target": "current_url",
  "expected": "/products",
  "source": "user_requirement|observed_page|model_inference",
  "confidence": 0.9
}
```

约束：`source=model_inference` 时 UI 必须显示“待确认”；`confidence` 0–1。

### 5.3 失败分析（`test_results.failure_analysis`）

```json
{
  "observed_error": "TimeoutError: locator.click: Timeout 30000ms exceeded",
  "inferred_causes": [
    {"cause": "登录按钮的可访问名与脚本定位器不一致", "evidence": "页面元素显示 'Sign in'，脚本使用 '登录'", "confidence": 0.72}
  ],
  "suggestions": ["改用 role=button name=Sign in 或 data-testid"],
  "needs_more_info": false,
  "provider": "mock",
  "model": "mock-v1",
  "is_mock": true
}
```

### 5.4 脚本校验报告（`test_scripts.validation_report`）

```json
{
  "ok": false,
  "issues": [
    {"severity": "error", "line": 3, "col": 0, "code": "IMPORT_DENIED", "message": "不允许导入模块 os"},
    {"severity": "warning", "line": 12, "col": 4, "code": "NO_ASSERTION", "message": "测试函数未发现断言"}
  ],
  "checked_at": "2026-11-03T12:00:00Z",
  "validator_version": "v1"
}
```

---

## 6. 迁移与初始化

### 6.1 迁移策略

- Alembic 配置：`backend/alembic.ini`、`backend/migrations/env.py`。
- 每个 Phase 一组迁移；迁移文件入库；禁止只靠 `create_all`。
- 生成后**人工审查**：索引、外键、字符集、JSON、默认值。
- 开发可 `alembic downgrade -1`；生产/演示数据升级前备份。
- 测试库：`smarttest_test`，集成测试前 `alembic upgrade head` + 清表。

### 6.2 命令

```bash
cd backend
alembic current
alembic upgrade head
alembic revision --autogenerate -m "add pages and elements"
alembic downgrade -1          # 仅开发
```

### 6.3 初始数据

- `users`：`demo`（id=1）。
- 不自动创建项目/用例；由演示脚本或 UI 创建。
- 可选 `scripts/seed_demo.py` 创建 DemoShop 项目、Mock LLM、需求与页面（需先采集）。

### 6.4 MySQL 实例

- 本机开发：项目独立实例 `127.0.0.1:3307`，data dir `.dev/mysql/data`，`--mysqlx=0` 避免与现有 3306 服务的 X Plugin 端口冲突。
- Compose：`mysql:8.0`，host 3307。
- 连接串示例：
```text
mysql+pymysql://smarttest:smarttest_dev_pw@127.0.0.1:3307/smarttest?charset=utf8mb4
```
- MySQL 9.4 默认 `caching_sha2_password`；PyMySQL 需要 `cryptography`。
- 时区：连接后执行 `SET time_zone = '+00:00'`（SQLAlchemy connect event）。

### 6.5 容量与清理

| 数据 | 上限/策略 |
| --- | --- |
| 页面/项目 | 默认 max_pages=8；可配置至 50 |
| 元素/页面 | 最多 80 条（按优先级截断） |
| 文本摘要 | ≤8 KB |
| DOM 文件 | ≤200 KB（gzip 可选） |
| 截图 | ≤5 MB/张 |
| 脚本 | ≤60 KB |
| 需求/用例 JSON | ≤1 MB |
| LLM 原始响应 | ≤256 KB，30 天后可清理 |
| 执行日志 | ≤2 MB/次 |
| 任务日志 | 每任务 ≤500 条 |
| 执行历史 | 默认保留；按项目软删除不清理文件 |

清理策略（P1）：定期删除过期 `async_task_logs`、`generation_records.raw_response_path` 文件、孤儿 workspace；不在 MVP 自动执行，提供脚本/文档。

---

## 7. 索引与查询模式

| 查询 | 索引 |
| --- | --- |
| 项目列表（owner, 未删除） | `idx_projects_owner` + `deleted_at` |
| 项目下页面分页 | `uq_web_pages_project_url` / `idx_web_pages_project` |
| 页面元素 | `idx_page_elements_page` |
| 页面关系 | `idx_page_relations_from` / `_to` |
| 需求/用例/脚本列表 | `idx_*_project` |
| 用例按需求 | `idx_test_cases_requirement` |
| 执行历史 | `idx_executions_project` + `created_at` |
| 执行结果 | `idx_results_execution` |
| 任务轮询 | `uq_async_tasks_task_id` |
| 生成记录 | `idx_generation_project` + `created_at` |

避免：
- 对 `TEXT/LONGTEXT` 建索引；
- 对大 JSON 做 `JSON_EXTRACT` 过滤（MVP 不做）；
- `SELECT *` 拉取大字段列表（列表接口只返回摘要字段）。

---

## 8. 一致性与并发

- 任务状态更新使用短事务；不在长任务持锁。
- 执行创建时校验脚本 `status=validated` 且属于项目；同一脚本可被多次执行。
- 页面 upsert 使用唯一键；并发探索同一项目时，后写覆盖前写，任务本身应避免重复（MVP 单 worker）。
- 删除项目/需求/用例为软删除；执行记录保留。
- JSON 字段更新必须整体赋值（SQLAlchemy 不跟踪原地修改），或使用 `MutableDict`；MVP 统一整体赋值。
- 统计字段（execution total/passed/...）在结果解析后一次性写回，避免并发累加错误。

---

## 9. 与提示词的偏差

| 项 | 提示词 | 本设计 | 原因 |
| --- | --- | --- | --- |
| MySQL 版本 | 8.0 | 本机 9.4；Compose 8.0 | 环境已装 9.4，避免安装冲突 |
| 用户体系 | 可简化 | 单用户 + owner_id | 满足隔离与未来扩展 |
| 任务表 | 可选 | 必选 `async_tasks` + logs | 业务历史/进度/取消需要 |
| 脚本内容 | 可文件存储 | DB 存内容 + 文件副本 | 版本/编辑/下载一致性更好，大小受限 |
| 失败分析表 | 未列 | `test_results.failure_analysis` JSON | 避免额外表，查询足够 |
| 执行-脚本 | 未列 | `execution_scripts` 关联表 | 保留多脚本执行关系 |

---

## 10. 数据库验收清单

- [ ] `alembic upgrade head` 在空库可重复执行成功。
- [ ] 所有表 `utf8mb4`，时间字段为 UTC。
- [ ] 所有领域表有 `project_id` 且查询带项目过滤。
- [ ] 唯一约束/外键/索引与本文一致。
- [ ] 默认用户种子存在且幂等。
- [ ] 删除项目不物理删除执行历史。
- [ ] API Key 不以明文入库。
- [ ] JSON 字段有应用层大小/结构校验。
- [ ] 迁移文件可审查、可回滚（开发环境）。
