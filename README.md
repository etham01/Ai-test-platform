# SmartTest

面向 Web 应用的智能多页面自动化测试用例与脚本生成平台（本科毕业设计项目）。

> 当前状态：**端到端 MVP 已完成**（Phase 1–7），交付就绪；环境阻塞项如实列出。
> 已实际验证：多页面采集、Mock/真实 LLM 抽象、业务流程与用例生成、Pytest + Playwright
> 脚本生成/校验、受限本地执行、逐条结果、截图、HTML 报告、失败分析与取消/超时。
> Docker 隔离与真实 LLM 供应商调用受当前环境限制，**未验证**，详见
> `docs/KNOWN_LIMITATIONS.md`。

## 技术栈

- 前端：Vue 3.5 + TypeScript + Vite 8 + Tailwind CSS 4 + Vue Router 4 + Pinia 3
  - UI 使用官方 shadcn-vue CLI 组件（reka-nova 风格，Tailwind 4 CSS variables）。
- 后端：Python 3.12 + FastAPI + Pydantic 2 + SQLAlchemy 2 + Alembic + PyMySQL
- 数据库：MySQL 9.4（本机 3307）/ MySQL 8.0（Compose）
- 任务：Celery 5.6 + Redis（本机便携 Redis 8.10.3，Compose Redis 7）
- 浏览器：Playwright Python（系统 Chrome 或 Chromium）
- AI：OpenAI 兼容客户端 + 明确标注的 `MockLLMProvider`
- 测试：Pytest 9 + pytest-playwright 0.10 + pytest-html 4.2

## 快速开始（本地开发）

```bash
# 0) 配置（不要提交 .env；.env.example 里是开发默认值）
cp .env.example .env

# 1) 下载/启动开发服务：MySQL 3307 + Redis 6379
bash scripts/fetch_redis.sh
bash scripts/dev_services.sh start
bash scripts/dev_services.sh status

# 2) Python 环境
python -m venv .venv
source .venv/Scripts/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# 可选：安装 Playwright 自带 Chromium；若失败，.env 中 PLAYWRIGHT_CHANNEL=chrome 使用系统 Chrome
python -m playwright install chromium

# 3) 数据库迁移
cd backend
alembic upgrade head
cd ..

# 4) 启动本地 DemoShop（固定测试数据，独立进程）
python -m uvicorn demo_site.main:app --host 127.0.0.1 --port 8001

# 5) 启动后端
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 6) 启动 Celery（Windows 使用 solo）
cd backend
celery -A app.tasks.celery_app:celery_app worker --loglevel=INFO --pool=solo --concurrency=1

# 7) 启动前端
pnpm --dir frontend install
pnpm --dir frontend dev
```

打开：

- 前端工作台：http://127.0.0.1:5173
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health
- 依赖检查：http://127.0.0.1:8000/api/v1/health/deps
- DemoShop：http://127.0.0.1:8001（演示账号 `demo / demo123`）

## 端到端演示流程

1. 新建项目，Base URL 填 `http://127.0.0.1:8001`。
2. 进入项目 → 页面 → 开始探索（默认 8 页 / 深度 2）。
3. 在「测试需求」创建需求并关联页面。
4. 在「业务流程」分析并确认流程。
5. 在「测试用例」选择需求生成用例；`model_inference` 会标记待确认。
6. 在「脚本」选择用例生成 Pytest + Playwright 脚本；AST/安全校验通过后才可执行。
7. 在「执行与报告」选择已验证脚本创建执行；可查看结果、截图、日志、HTML 报告。
8. 对失败结果点击「失败分析」，区分 observed error 与 inferred causes。

## 当前已实现

- 项目 CRUD、软删除、`owner_id + project_id` 隔离
- 统一响应 envelope、错误处理、request id、日志脱敏
- MySQL 迁移（users/projects/pages/elements/relations/LLM/requirements/workflows/cases/scripts/executions/results/tasks）
- Redis + Celery 异步任务，任务进度、日志、取消
- Playwright 同源有限 BFS、元素/关系落库、DOM/截图
- SSRF/URL 策略：私网、环回、链路本地、云元数据、重定向、危险链接、开发 allowlist
- LLM 配置（Fernet 加密 Key、掩码、Mock/真实 Provider、连接测试、生成记录）
- 结构化流程/用例生成：Prompt 版本、JSON 解析、Pydantic 校验、有限修复
- 脚本生成、AST/安全校验、版本化、预览/编辑/下载
- 受限本地执行：独立工作区、环境清洗、URL 路由守卫、超时/取消/进程树终止
- JUnit XML 解析、逐条结果、失败截图、pytest-html 报告、日志
- 失败分析（Mock/真实 Provider 同接口，明确 observed vs inferred）
- Vue 工作台：项目概览/页面/流程/需求/用例/脚本/执行/设置

## 验证命令

```bash
# 后端
cd backend
ruff check app migrations tests
pytest tests -q

# 前端
pnpm --dir frontend build

# 环境
.venv/Scripts/python.exe scripts/verify_env.py
```

最近一次实测：后端 **36 passed**；前端 `vue-tsc + vite build` 通过；
DemoShop 采集 **8 页 / 53 条关系**；5 条生成脚本实际执行全部通过；
另有 1 passed + 1 failed 执行验证报告/截图/失败分析，超时与取消也已验证。

## 文档

- [实施计划](docs/IMPLEMENTATION_PLAN.md)
- [架构设计](docs/ARCHITECTURE.md)
- [数据库设计](docs/DATABASE_DESIGN.md)
- [API 设计](docs/API_DESIGN.md)
- [安全设计](docs/SECURITY.md)
- [测试与验证](docs/TESTING.md)
- [使用指南](docs/USER_GUIDE.md)
- [前端 shadcn-vue 迁移](docs/FRONTEND_SHADCN_MIGRATION.md)
- [已知限制](docs/KNOWN_LIMITATIONS.md)

## 重要限制

- 本机没有 Docker/WSL，DockerRunner/Compose 执行 profile **未实现/未验证**；API 对 `mode=docker` 返回 409。
- 默认使用 Mock LLM；真实 OpenAI 兼容客户端已实现并用假 HTTP 服务测试，
  但当前没有真实 API Key 做供应商实测。
- 本地执行模式**不是安全沙箱**，仅用于本地 demo 站点；生产必须使用容器/沙箱。
- 基础组件、Table、Select/Checkbox、Alert、Dialog、Sonner 均已接入官方 shadcn-vue CLI。
- 更多细节见 `docs/KNOWN_LIMITATIONS.md`。
