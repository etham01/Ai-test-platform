# SmartTest 测试与验证

> 版本：v1.0（2026-11-03）
> 当前结果：后端 36 passed；前端 `pnpm build` 通过；UI 流程人工实跑；
> `scripts/e2e_demo.py` 自动 E2E 通过（5 页 → 1 流程 → 2 用例 → 1 脚本 → 执行 passed）。

---

## 1. 测试分层

| 层 | 范围 | 依赖 |
| --- | --- | --- |
| 单元测试 | URLPolicy、路径安全、Fernet、Schema、AST 校验、JSON 解析/修复、OpenAI 兼容客户端（MockTransport） | 无外部服务 |
| 集成测试 | 项目 CRUD、项目隔离、schema 校验、Celery eager 调试任务 | MySQL 3307 |
| 浏览器测试 | 系统 Chrome / Playwright 页面打开与 UI 冒烟 | 前端/后端/DemoShop |
| 端到端验证 | 采集 → 需求 → 流程 → 用例 → 脚本 → 执行 → 报告/失败分析 | MySQL/Redis/worker/DemoShop/前端 |

---

## 2. 运行命令

```bash
# 启动依赖
bash scripts/dev_services.sh start
python -m uvicorn demo_site.main:app --host 127.0.0.1 --port 8001

# 后端 lint + 测试
cd backend
ruff check app migrations tests
pytest tests -q

# 前端类型检查 + 构建
pnpm --dir frontend build

# 环境检查
.venv/Scripts/python.exe scripts/verify_env.py
```

集成测试使用 `smarttest_test` 数据库，测试前会 `drop_all/create_all`，**不会修改业务库 `smarttest`**。

---

## 3. 单元测试清单（当前 36 项）

| 文件 | 覆盖 |
| --- | --- |
| `tests/unit/test_url_policy.py` | URL 规范化、同源、危险链接、私网/元数据拦截、开发 allowlist、重定向/链接过滤 |
| `tests/unit/test_paths_and_security.py` | 路径穿越、Windows 保留文件名、Fernet 加解密/掩码 |
| `tests/unit/test_project_schema.py` | base_url 校验、项目名 trim、更新字段 |
| `tests/unit/test_logging_redaction.py` | API Key/password/Bearer/数据库 DSN 脱敏 |
| `tests/unit/test_script_validator.py` | 合法脚本、危险导入、eval、缺断言、语法错误、while True 警告 |
| `tests/unit/test_ai_output.py` | 代码围栏 JSON、无效 JSON、修复一次后成功 |
| `tests/unit/test_openai_provider.py` | 正常内容/usage、429 重试、401 不重试、空内容 |
| `tests/integration/test_projects_api.py` | health、项目 CRUD、软删除、隔离、422、Celery eager 调试任务 |

---

## 4. 端到端验证（实际执行记录）

环境：Windows 11，MySQL 9.4 @3307，Redis 8.10.3 @6379，系统 Chrome，Celery solo worker。

1. 启动 DemoShop、后端、worker、前端。
2. 新建项目 `DemoShop 演示项目`，base_url `http://127.0.0.1:8001`。
3. 页面探索 `max_pages=8, max_depth=2`：**8 页、53 条关系、全部 parsed**。
4. 单页扫描 `http://127.0.0.1:3306/` 与 `http://169.254.169.254/...`：任务失败，未落页面。
5. 限制测试：临时项目 `max_pages=3, max_depth=1`：只采集 3 页（首页/products/cart）。
6. 需求 `登录与购物流程` → Mock 流程分析：2 个流程。
7. 生成用例：5 条；登录成功/失败标记 `needs_review`（model_inference）。
8. 生成脚本：5 个 v3 脚本均 `validated`；显式运行 **5 passed**。
9. 执行验证：脚本 11（TC-001）+ 脚本 16（故意错误标题）→ 1 passed / 1 failed。
10. 报告 39.6 KB、日志 4.3 KB、失败截图 150.6 KB；失败分析返回 observed_error + inferred causes。
11. 超时执行（10s）→ `timeout`；取消长任务 → `cancelled`，进程树被杀。
12. UI：11 条项目路由 0 console error；UI 创建需求 → 生成用例 → 生成脚本 → 执行 #4（1 passed）。
13. 自动 E2E：`python scripts/e2e_demo.py` → 5 pages / 1 workflow / 2 cases / 1 validated script /
    execution #5 `passed`，报告 33.3 KB；脚本默认软删除临时项目。

---

## 5. 复现 E2E 的注意点

- `PLAYWRIGHT_CHANNEL=chrome` 使用系统 Chrome；若已 `python -m playwright install chromium`，可留空。
- Celery Windows 必须 `--pool=solo --concurrency=1`。
- DemoShop 的登录账号是 `demo / demo123`，商品与价格固定。
- 失败截图依赖生成脚本使用 `page` fixture；执行器 conftest 已注入。
- 执行工作区在 `storage/executions/{execution_id}/`；不要用旧工作区覆盖新执行。
- 执行 URL 守卫只允许项目 origin；DemoShop 必须运行在 `http://127.0.0.1:8001`。
- 端口冲突时先 `bash scripts/dev_services.sh status`，不要重复启动 MySQL/Redis。

---

## 6. 未覆盖/未验证

- DockerRunner/容器隔离：本机无 Docker/WSL，未实现也未验证；API 对 `mode=docker` 返回 409。
- 真实 LLM 供应商：无 API Key；仅 Mock + httpx MockTransport 测试。
- 真实第三方站点、验证码、复杂 SPA、跨域 Cookie：未测试。
- Windows 资源硬限制（Job Object/cgroup）、Docker 出口 allowlist：未实现。
- 基础组件、Table/Select/Checkbox/Alert/Dialog/Sonner 已接入官方 shadcn-vue CLI；views 层无原生 table/select/checkbox/input/textarea。
- 报告 HTML sanitizer、多用户认证：未实现。
