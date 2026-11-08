# SmartTest 实施计划（毕业设计版）

> 项目：SmartTest——面向 Web 应用的智能多页面自动化测试用例与脚本生成平台
> 仓库根目录：`D:\Paper`
> 文档版本：v1.0（2026-11-03）
> 当前阶段：Phase 7 完成（交付就绪，环境阻塞项如实列出）
> 原则：先打通端到端 MVP，再增强；不伪造验证结果；不覆盖已有资产。

---

## 1. 仓库与环境审查结论

### 1.1 仓库现状

| 项目 | 实测结果 | 结论 |
| --- | --- | --- |
| 工作目录 | `D:\Paper` | 空仓库，仅有一个文件 |
| 已有文件 | `SmartTest_Project_Prompt.txt`（32 KB） | 只读保留，不修改、不覆盖 |
| Git 仓库 | 否 | Phase 1 可 `git init`，不影响现有文件 |
| 前端/后端代码 | 无 | 从零初始化 |
| 数据库迁移/模型 | 无 | 从零设计 |
| `.env`/密钥 | 无 | 需要 `.env.example` 与本地开发密钥方案 |
| 已有依赖/锁文件 | 无 | 不涉及“优先沿用既有锁文件”的约束 |

**审查结论：没有需要保留或迁移的业务代码；唯一的用户资产是提示词文件，保持原样。**

### 1.2 运行环境实测

| 依赖 | 实测 | 可用性 | 备注 |
| --- | --- | --- | --- |
| Node.js | v22.19.0 | 可用 | 满足 Vite 8 的 `>=22.12` 要求 |
| npm | 10.9.3 | 可用 | registry 已配置为 `https://registry.npmmirror.com` |
| pnpm | 10.34.5 | 可用 | 前端统一使用 pnpm |
| Python | 3.12.10（`D:\tools\Python`） | 可用 | 使用项目 `.venv`，不污染全局 |
| pip | 25.0.1 | 可用 | PyPI 直连可用 |
| MySQL | 9.4.0，服务 `MySQL94`，监听 3306 | 部分可用 | 现有服务 root 密码未知；不能假设可登录 |
| MySQL 项目实例 | 已实测在 3307 初始化并启动成功 | 可用 | `mysqld --initialize-insecure` + 独立 datadir 可行；验证后已关闭并清理 |
| Redis | 系统未安装 | 缺失 | 已实测便携版 Redis 8.10.3（redis-windows）可下载、启动、`PING` 返回 `PONG` |
| Docker | 未安装 | 不可用 | 不能在本机验证容器隔离/Compose |
| WSL | 未安装 | 不可用 | 不能通过 WSL 提供 Redis/Docker |
| Playwright (Python) | 未安装 | 缺失 | 需要安装；浏览器缓存目录不存在 |
| Chrome / Edge | 已安装 | 可用 | 可作为 Playwright `channel=chrome` 的回退浏览器 |
| Java | 25 | 可用 | 与项目无关 |
| PostgreSQL | 18.4 | 已安装但不用 | 不替换 MySQL |
| 磁盘 | D: 约 254 GB 可用 | 充足 | MySQL 数据目录约 200 MB |
| 端口 | 3307/6379/8000/8001/5173 空闲 | 可用 | 均未被占用 |
| GitHub 直连 | 很慢，12 MB 包在 120 s 内未下完 | 不稳定 | 使用 `ghproxy.net` / `gh-proxy.com` 镜像 |
| Playwright CDN | 可达，Chromium 约 178 MB | 可用但较大 | 优先尝试；失败则用系统 Chrome |
| Docker Hub | 可达 | 可用 | 但本机无 Docker，不能验证 |

### 1.3 关键冲突与风险（先于代码）

1. **提示词要求 MySQL 8.0，本机是 9.4.0，且 3306 的 root 密码未知。**
   - 处理：开发默认使用项目独立的 MySQL 9.4 实例（端口 3307，独立 data dir），不碰现有 3306；`docker-compose.yml` 中仍使用 `mysql:8.0`，保持与提示词一致。版本差异写入 `KNOWN_LIMITATIONS.md`。
2. **提示词要求 Redis，本机没有。**
   - 处理：提供 `scripts/fetch_redis.sh` 下载便携版 Redis 8.10.3（redis-windows，仅开发、仅绑定 127.0.0.1、可设密码），Celery 仍按 Redis broker/backend 配置；Compose 中使用 `redis:7`。便携包为第三方构建，写入供应链限制。
3. **本机没有 Docker/WSL，无法验证 Docker 隔离执行。**
   - 处理：默认实现并验证“受限本地执行模式”；不实现 DockerRunner；保留 Compose 基础设施与设计说明，并在文档中明确标注“未实现/未验证”。本地模式不是安全沙箱，只允许在演示/受控环境使用。
4. **没有真实 LLM API Key。**
   - 处理：保留完整的 OpenAI 兼容客户端；提供明确标注的 `MockLLMProvider`；UI 用徽标和横幅区分 Mock/真实；用本地假 HTTP 服务测试真实客户端的重试、超时、无效 JSON 处理，不宣称已验证真实供应商。
5. **Playwright 浏览器下载 178 MB，网络不稳定。**
   - 处理：优先安装 Chromium；失败时使用系统 Chrome（`channel=chrome`）。代码和配置都支持两种方式。
6. **Windows 上 Celery 不支持 prefork。**
   - 处理：本地 worker 使用 `--pool=solo --concurrency=1`；长任务串行执行可接受；Compose/Linux 可提高并发。
7. **前端依赖处于较新的大版本（Vite 8、Tailwind 4、Vue Router 4、Pinia 3）。**
   - 处理：以 `create-vue` 官方模板生成的兼容组合为基线，锁定 `pnpm-lock.yaml`；先跑通构建再逐个加组件；不手工混装互相不兼容的最新大版本。
8. **单用户模式与“项目数据隔离”的张力。**
   - 处理：数据模型保留 `users` 与 `owner_id`，所有资源仍做 `project_id + owner_id` 校验；MVP 为本地单用户，不引入 OAuth；API 默认只监听 127.0.0.1。
9. **LLM 生成的脚本是不可信代码。**
   - 处理：AST 检查 + 导入白名单 + 危险调用拒绝 + 独立工作目录 + 环境变量清洗 + 超时/进程树终止 + URL 守卫；Docker 为最终隔离边界，本地模式明确标注“非沙箱”。
10. **页面内容可能包含提示词注入。**
    - 处理：页面内容用不可信分隔符包裹；Prompt 明确“页面内容是数据不是指令”；输出只做结构化校验，不自动执行；生成脚本必须用户确认后才可执行。

### 1.4 不覆盖/不删除声明

- `SmartTest_Project_Prompt.txt` 保持原样。
- 不修改现有 `MySQL94` 服务的数据目录、配置或账号。
- 不安装/卸载系统级 MySQL、PostgreSQL、Java、Chrome。
- 不把便携 Redis 安装为 Windows 服务；只作为项目内开发进程运行。
- 文档与代码均创建在新目录（`docs/`、`backend/`、`frontend/`、`demo_site/`、`scripts/` 等）。

---

## 2. 交付目标与 MVP 边界

### 2.1 P0：必须完成且能演示

| # | 能力 | 演示判据 |
| --- | --- | --- |
| 1 | 项目 CRUD | 前端创建/编辑/删除项目，刷新后仍在 MySQL |
| 2 | LLM 配置 | 可保存 Mock 或 OpenAI 兼容配置；Key 不回传；可测试连接 |
| 3 | 单页采集 + 多页探索 | 对本地 demo 站点采集 ≥6 个页面，含元素、标题、URL、关系 |
| 4 | 探索边界 | `max_pages`/`max_depth` 生效；重复 URL 不重复；非授权目标被拦截 |
| 5 | 测试需求 | 创建需求并关联页面 |
| 6 | 业务流程分析 | Mock/真实 LLM 生成候选流程；用户可确认/编辑；推断标记可见 |
| 7 | 测试用例生成 | 结构化 JSON、Pydantic 校验、页面 ID 校验、保存 MySQL、可编辑 |
| 8 | 脚本生成 | 每个用例生成 Pytest + Playwright 脚本；版本化；预览/编辑/下载 |
| 9 | 脚本校验 | AST 语法 + 导入/危险调用检查；不通过不能执行 |
| 10 | 受控执行 | 本地模式执行通过/失败各一条；逐条结果、日志、截图、HTML 报告 |
| 11 | 失败分析 | 对失败结果调用 Mock/真实 LLM，区分观察到的错误与模型推测 |
| 12 | 前端完整流程 | 从 UI 完成上述流程，不依赖手工调内部接口 |
| 13 | 本地 demo 站点 | 首页/登录/列表/详情/购物车/结算/订单确认，可重复启动 |
| 14 | 文档与验证 | README、启动命令、测试命令、已知限制、E2E 验证脚本 |

### 2.2 P1：应做，但不阻塞演示

- Docker Runner 真正跑通（**当前环境阻塞，未实现**）。
- 真实 LLM 供应商实测（**需要用户提供 Key**）。
- 登录态 `storage_state` 上传与加密保存。
- 取消/超时在真实长任务中的完整演练。
- 页面关系 SVG 可视化（P0 可先列表 + 简单图）。
- OpenAPI → TypeScript 类型自动生成。
- 失败截图、浏览器信息、失败步骤定位。
- 用例重新生成、脚本批量生成、执行历史对比。
- SSE 替换轮询（P0 用轮询）。
- 演示数据一键 seed。

### 2.3 P2：可选增强

- 多用户登录/OAuth、团队权限。
- 分布式 worker、任务优先级、定时任务。
- Docker 网络出口代理（真正按域名 allowlist）。
- SPA 深度交互采集、表单安全提交、验证码人工接管。
- 视觉回归、可访问性、性能测试。
- 测试覆盖率映射（注意：自定义维度覆盖率 ≠ 代码覆盖率）。
- 国际化、移动端适配、报告导出 PDF。

### 2.4 当前环境可能做不到、需要用户/后续补齐

| 项 | 原因 | 交付方式 |
| --- | --- | --- |
| Docker 隔离执行验证 | 本机无 Docker/WSL | 未实现；保留 Compose 基础设施 + 明确“未验证” |
| 真实 LLM 调用 | 无 API Key | 完整客户端 + Mock + 假 HTTP 测试 + 配置入口 |
| 精确 MySQL 8.0 | 本机 9.4 | 本地 9.4；Compose 8.0；SQL 兼容性说明 |
| Redis 7 | 本机便携 Redis 8.10.3 | 本地 8.10.3；Compose 7；版本差异说明 |
| 第三方真实站点 | 未授权 | 只用本地 demo 站点；不擅自扫描公网 |
| 验证码/登录绕过 | 安全与合规禁止 | 仅支持合法 `storage_state` 或人工提供会话 |
| 完整 SSRF/DNS rebinding 证明 | 本地模式无法形成强边界 | 分层校验 + 残余风险说明；Docker 出口代理列为 P2 |

---

## 3. 总体架构决策（摘要）

> 详细图与边界见 `docs/ARCHITECTURE.md`。

- **模块化单体**，不拆微服务、不上 Kubernetes。FastAPI 负责 API，Celery worker 负责长任务，前端独立构建。理由是毕业设计需要可运行、可解释、可演示，微服务只会放大部署与调试成本。
- **同步技术栈**：SQLAlchemy 2.x 同步 Session + PyMySQL；Playwright Python 同步 API；Celery 同步任务。FastAPI 的 `def` 端点由线程池执行，避免 async/sync 混用的隐性 bug。
- **MySQL 是唯一业务主库**；Redis 只做 Celery broker/backend 与短期任务协调；文件系统存脚本副本、DOM 快照、截图、日志、HTML 报告，数据库存元数据与相对路径。
- **异步任务统一落库**：`async_tasks` + `async_task_logs` 是任务状态的业务事实来源；Celery 只负责执行。前端轮询 `/tasks/{task_id}`。
- **浏览器层**：Playwright 同步 API，一次任务一个 Browser/Context；同源 BFS；严格 `max_pages`/`max_depth`/超时；禁止自动提交表单；URL 政策 + 浏览器路由守卫双层校验。
- **AI 层**：`LLMProvider` 接口；`OpenAICompatibleClient` 与 `MockLLMProvider` 同接口；Prompt 独立版本化；JSON 解析 + Pydantic 校验 + 有限修复；所有推断标记 `model_inference`。
- **执行层**：`ExecutionRunner` 接口，LocalRunner（本机验证）；DockerRunner 未实现（API 对 docker 模式返回 409）；AST 检查只是辅助，不是沙箱。
- **前端**：Vue 3 + TypeScript + Vite + Tailwind + shadcn-vue + Router + Pinia；统一 API client；轮询任务；Mock/真实 LLM 徽标；不使用无后端行为的按钮。

### 3.1 技术栈最终确认版

| 层 | 选型 | 版本策略 |
| --- | --- | --- |
| 前端框架 | Vue 3.5 + TypeScript | 以 `create-vue` 模板为准 |
| 构建 | Vite 8 | 锁定 `pnpm-lock.yaml` |
| UI | Tailwind CSS 4 + 官方 shadcn-vue CLI（reka-nova） | Button/Input/Textarea/Card/Badge/Modal/Dialog/Table/Alert/Select/Checkbox/Sonner 已接入 |
| 路由/状态 | Vue Router 4.6 + Pinia 3.0 | 已安装并用 `pnpm-lock.yaml` 锁定 |
| HTTP | fetch 封装（可选 axios） | 统一错误/请求 ID |
| 后端 | Python 3.12 + FastAPI 0.140 + Pydantic 2.13 | `requirements.txt` 精确锁定 |
| ORM/迁移 | SQLAlchemy 2.0.51 + Alembic | 迁移文件入库 |
| MySQL 驱动 | PyMySQL + cryptography | 支持 MySQL 9.4 的 caching_sha2 |
| 数据库 | MySQL 9.4（本机开发）/ MySQL 8.0（Compose） | utf8mb4，UTC |
| 队列 | Celery 5.6 + Redis | 本机 Redis 8.10.3 便携版；Compose Redis 7 |
| 浏览器 | Playwright Python 1.64.1 | Chromium 优先，系统 Chrome 回退 |
| 测试 | Pytest 9 + pytest-playwright 0.10 + pytest-html 4.2 | 生成脚本与后端测试共用 |
| 报告 | pytest-html + JUnit XML | HTML 报告 + 结构化解析 |
| LLM | OpenAI 兼容 HTTP API + Mock | 不绑定供应商、不假设 JSON Schema |
| 日志/质量 | Ruff、ESLint、Prettier | 提交前检查 |

### 3.2 开发环境拓扑

```text
┌────────────────────┐        HTTP /api/v1        ┌─────────────────────┐
│ Vue 3 + Vite :5173 │ ─────────────────────────> │ FastAPI :8000       │
└────────────────────┘                            │  API / services     │
                                                  └──────┬──────┬───────┘
                                                         │      │
                                      SQLAlchemy/PyMySQL │      │ Celery enqueue
                                                         v      v
                                              ┌──────────────┐  ┌──────────────┐
                                              │ MySQL :3307  │  │ Redis :6379  │
                                              │ (项目独立)    │  │ (便携版)      │
                                              └──────────────┘  └──────┬───────┘
                                                                       │
                                                              ┌────────v────────┐
                                                              │ Celery worker   │
                                                              │ --pool=solo     │
                                                              │ Playwright / AI │
                                                              └────────┬────────┘
                                                                       │
                                                              ┌────────v────────┐
                                                              │ demo_site :8001 │
                                                              │ 独立 FastAPI    │
                                                              └─────────────────┘
```

---

## 4. 分阶段实施计划

> 状态图例：✅ 已完成 | 🟡 进行中 | ⬜ 未开始 | ⛔ 环境阻塞
> 工期为个人开发估算，含调试与验证，不含论文写作。

### Phase 0：仓库审查与方案细化 ✅

**目标**：确认仓库/环境，形成与现状一致的设计文档，不写业务代码。

**依赖**：无。

**关键产出**：
- `docs/IMPLEMENTATION_PLAN.md`（本文件）
- `docs/ARCHITECTURE.md`
- `docs/DATABASE_DESIGN.md`
- `docs/API_DESIGN.md`
- `docs/SECURITY.md`
- `docs/KNOWN_LIMITATIONS.md`

**已执行的环境验证**：
```bash
node --version && npm --version && pnpm --version
python --version && pip --version
mysql --version
mysqld --initialize-insecure --datadir=<临时目录> ...   # 3307 实例验证
curl -L <Redis 便携包> && redis-server --version && redis-cli ping  # PONG
docker --version                                        # command not found
wsl --status                                            # 未安装
```
验证产生的临时 MySQL/Redis 文件已清理，未改动现有 3306 服务。

**验收**：文档与实际环境一致；不覆盖提示词文件；明确列出环境阻塞项。

**风险/回退**：若用户坚持使用现有 3306，只需改 `DATABASE_URL`，不影响迁移与代码。

**状态**：✅ 完成（2026-11-03）。

---

### Phase 1：项目骨架与基础设施（估算 2–3 天）✅

**目标**：前后端可启动；MySQL 迁移可执行；Redis/Celery 可跑通一个测试任务；项目 CRUD 前后端联调成功。

**依赖**：Phase 0。

**任务拆解**：

| # | 任务 | 关键文件 |
| --- | --- | --- |
| 1.1 | 仓库卫生与目录 | `.gitignore`、`.env.example`、`README.md`、`storage/.gitkeep` |
| 1.2 | Python venv 与依赖 | `backend/requirements.txt`、`backend/requirements-dev.txt`、`backend/pyproject.toml` |
| 1.3 | 配置/日志/错误/入口 | `backend/app/core/config.py`、`logging.py`、`errors.py`、`security.py`、`backend/app/main.py` |
| 1.4 | DB 基础设施 | `backend/app/db/session.py`、`base.py`、`backend/alembic.ini`、`backend/migrations/` |
| 1.5 | 核心模型 | `backend/app/models/{base,user,project,task}.py` |
| 1.6 | 迁移与种子 | 初始迁移；默认演示用户 |
| 1.7 | Celery | `backend/app/tasks/celery_app.py`、`debug_tasks.py`、`services/task_service.py` |
| 1.8 | 任务 API | `backend/app/api/v1/endpoints/tasks.py`、`schemas/task.py` |
| 1.9 | 项目 CRUD | `models/project.py`、`schemas/project.py`、`repositories/project_repository.py`、`services/project_service.py`、`api/v1/endpoints/projects.py` |
| 1.10 | 前端骨架 | `frontend/`（create-vue）、`src/api/client.ts`、`src/layouts/AppLayout.vue`、`src/views/ProjectsView.vue`、`src/router/`、`src/stores/` |
| 1.11 | 开发服务脚本 | `scripts/dev_services.sh`、`scripts/fetch_redis.sh`、`scripts/verify_env.py` |
| 1.12 | 健康检查 | `/health`、`/api/v1/health/deps`（DB/Redis） |

**具体命令**：
```bash
# 1) 开发服务（MySQL 3307 + Redis 6379）
bash scripts/fetch_redis.sh          # 首次，从 ghproxy 下载便携 Redis
bash scripts/dev_services.sh start
bash scripts/dev_services.sh status

# 2) Python
python -m venv .venv
source .venv/Scripts/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# 3) 数据库
cd backend
alembic upgrade head
cd ..

# 4) 后端
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 5) Celery（Windows 必须 solo）
cd backend
celery -A app.tasks.celery_app:celery_app worker --loglevel=INFO --pool=solo --concurrency=1

# 6) 前端
pnpm --dir frontend install
pnpm --dir frontend dev

# 7) 验证
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health/deps
pytest backend/tests/unit -q
```

**验收标准**：
- `GET /health` 返回 200 且 `{"status":"ok"}`。
- `GET /api/v1/health/deps` 显示 MySQL/Redis 均 ok。
- `alembic current` 显示当前 revision；表 `users/projects/async_tasks/async_task_logs` 存在。
- 前端 5173 可打开；创建项目后刷新页面仍能看到（MySQL 持久化）。
- 触发一个 Celery 测试任务，`GET /api/v1/tasks/{task_id}` 从 `queued/running` 到 `succeeded`，且 `async_task_logs` 有记录。
- 删除项目为软删除，列表不再显示，执行历史不被物理删除。

**风险与回退**：
- MySQL 3307 初始化失败 → 改用现有 3306（用户提供凭据）或 3308。
- 便携 Redis 下载失败 → 重试 `ghproxy.net`/`gh-proxy.com`；仍失败则临时用 Celery `filesystem://`（仅应急，文档标注与提示词偏差）。
- Celery Windows 启动失败 → 确认 `--pool=solo`；检查 Redis 密码/URL。
- 前端脚手架依赖冲突 → 以 `create-vue` 默认组合为准，减少手工升级。

**Phase 1 实际完成证据（2026-11-03）**：

| 验证项 | 命令/操作 | 实际结果 |
| --- | --- | --- |
| 开发服务 | `bash scripts/dev_services.sh start` | MySQL 9.4 @ 3307 UP；Redis 8.10.3 @ 6379 UP |
| 数据库迁移 | `alembic upgrade head` / `alembic current` | 迁移 `0001` 成功；当前 `0001 (head)` |
| 依赖健康 | `GET /api/v1/health/deps` | `database.ok=true`、`redis.ok=true` |
| 后端测试 | `pytest tests -q` | 15 passed |
| Python lint | `ruff check app migrations tests` | All checks passed |
| 前端类型/构建 | `pnpm build` | `vue-tsc` + `vite build` 成功 |
| Celery 任务 | `POST /tasks/debug` → 轮询 | `queued → running → succeeded`，日志 2 条 |
| 任务取消 | 10s 调试任务，2s 后 `POST /tasks/{id}/cancel` | 0.5s 内变为 `cancelled`，日志记录取消 |
| 前端 CRUD | 浏览器（系统 Chrome）创建/删除项目 | 卡片与通知正确；无 console error |
| 持久化 | 重启 FastAPI 后重新查询项目 | DemoShop 项目仍在 MySQL |
| 单元测试范围 | URL/路径安全、Fernet、项目 schema、项目隔离、任务 eager | 覆盖 Phase 1 关键路径 |

**Phase 1 已知偏差/后续**：
- 前端 Phase 1 先使用 shadcn-vue 风格手写组件；随后已通过官方 CLI 接入基础组件（见
  `docs/FRONTEND_SHADCN_MIGRATION.md`），基础组件与 Table/Select/Checkbox 已完成迁移。
- Redis 使用第三方 Windows 构建（redis-windows 8.10.3），仅开发；Compose 仍为 `redis:7`。
- 本地执行仍是受限模式；Phase 5 已实现执行器并完成通过/失败/超时/取消验证，但 Docker 隔离未实现。

---

### Phase 2：Demo 站点、页面解析与多页面探索（估算 3–4 天）✅

**目标**：对本地 demo 站点完成单页采集与有限深度 BFS；页面、元素、关系落库；任务进度可查；SSRF/边界防护生效。

**依赖**：Phase 1；Playwright 安装；demo 站点可启动。

**任务拆解**：

| # | 任务 | 关键文件 |
| --- | --- | --- |
| 2.1 | 本地 demo 站点 | `demo_site/main.py`、`demo_site/data.py`、`templates/*.html`、`static/style.css`、`demo_site/requirements.txt` |
| 2.2 | URL 规范化与安全策略 | `backend/app/browser/url_policy.py`、`tests/unit/test_url_policy.py` |
| 2.3 | 浏览器管理 | `backend/app/browser/browser_manager.py` |
| 2.4 | 页面/元素提取 | `backend/app/browser/page_parser.py`、`backend/app/browser/extractors/page_snapshot.js` |
| 2.5 | 有限 BFS 探索 | `backend/app/browser/site_explorer.py` |
| 2.6 | 页面模型/迁移 | `backend/app/models/page.py`、迁移 |
| 2.7 | 采集任务 | `backend/app/tasks/scan_tasks.py`、`services/page_service.py` |
| 2.8 | 页面 API | `api/v1/endpoints/pages.py`、`schemas/page.py` |
| 2.9 | 可选登录态 | `api/v1/endpoints/pages.py` 上传 `storage_state`（P1） |
| 2.10 | 验证脚本 | `scripts/scan_demo.py` 或 pytest 集成测试 |

**具体命令**：
```bash
# 安装浏览器（二选一）
python -m playwright install chromium
# 若下载失败，设置 .env：PLAYWRIGHT_CHANNEL=chrome

# 启动 demo 站点
python -m uvicorn demo_site.main:app --host 127.0.0.1 --port 8001

# 启动后端/worker 后，用 API 触发探索
curl -X POST http://127.0.0.1:8000/api/v1/projects/1/pages/explore \
  -H "Content-Type: application/json" \
  -d '{"start_url":"http://127.0.0.1:8001/","max_pages":8,"max_depth":2}'

# 轮询任务并查看页面
curl http://127.0.0.1:8000/api/v1/tasks/<task_id>
curl http://127.0.0.1:8000/api/v1/projects/1/pages
curl http://127.0.0.1:8000/api/v1/projects/1/relations
```

**验收标准**：
- demo 站点至少包含 `/`、`/login`、`/products`、`/products/{id}`、`/cart`、`/checkout`、`/order/{id}`、`/about`。
- 探索返回 ≥6 个页面；每个页面有标题、URL、文本摘要、元素列表；元素覆盖 input/button/a/select/textarea/form。
- 元素包含 role/accessible name/label/placeholder/text/id/name/type/href 中的可用字段；敏感字段被标记/脱敏。
- 页面关系包含 observed_link/observed_navigation/observed_form_action；不重复添加相同边。
- 重复 URL（含 fragment、尾斜杠、默认端口差异）只采集一次。
- `max_pages=3` 时实际页面数 ≤3；`max_depth=1` 时不采集二级链接。
- 扫描 `http://127.0.0.1:3306`、`http://169.254.169.254/`、`file:///` 被拒绝；非 base_url 同源目标被拒绝；仅 `SMARTTEST_DEV_ALLOWED_TARGETS` 精确列出的 demo 源被允许。
- 单页失败不会导致整个任务崩溃；页面记录 `status=failed` + 错误信息，任务日志可查。
- DOM 快照/截图文件写入 `storage/projects/{project_id}/...`，数据库只存相对路径，大小受限。

**风险与回退**：
- Chromium 下载慢/失败 → `PLAYWRIGHT_CHANNEL=chrome`，使用系统 Chrome；记录版本差异。
- SPA 页面 DOM 未就绪 → `domcontentloaded` + 短暂 settle + 可配置等待；MVP 以服务端渲染 demo 站点为准。
- 表单提交造成副作用 → 默认只记录 form action，不提交；仅显式配置才允许安全 GET 导航。
- 重定向跳出同源 → 每次跳转后重新校验最终 URL；失败则标记 blocked。
- DNS rebinding → 解析所有 IP + 路由守卫 + 最终 URL 校验；残余风险写入安全文档。

---

### Phase 3：LLM 接入、业务流程与测试用例生成（估算 3–4 天）✅

**目标**：LLM 配置可管理且密钥安全；Mock/真实客户端同接口；业务流程、测试需求、测试用例可生成、校验、保存、编辑。

**依赖**：Phase 2（页面数据）。

**任务拆解**：

| # | 任务 | 关键文件 |
| --- | --- | --- |
| 3.1 | LLM 配置模型/加密 | `models/llm_config.py`、`core/security.py`、`services/llm_config_service.py` |
| 3.2 | LLM 配置 API | `api/v1/endpoints/llm_configs.py`、`schemas/llm_config.py` |
| 3.3 | Provider 接口 | `ai/providers/base.py`、`ai/providers/openai_compatible.py`、`ai/providers/mock.py` |
| 3.4 | 输出解析/修复 | `ai/output_parser.py`、`ai/repair.py`、测试 |
| 3.5 | Prompt 模板 | `ai/prompts/workflow_analysis.v1.md`、`case_generation.v1.md`、`prompt_manager.py` |
| 3.6 | 生成记录 | `models/generation.py`、`services/generation_service.py` |
| 3.7 | 流程分析 | `ai/workflow_analyzer.py`、`services/workflow_service.py`、`api/v1/endpoints/workflows.py` |
| 3.8 | 需求 CRUD | `models/requirement.py`、`schemas/requirement.py`、`api/v1/endpoints/requirements.py` |
| 3.9 | 用例生成 | `ai/case_generator.py`、`models/test_case.py`、`services/test_case_service.py`、`api/v1/endpoints/test_cases.py` |
| 3.10 | AI 路由 | `api/v1/endpoints/ai.py`（analyze/generate-cases） |
| 3.11 | 迁移 | 新增 6 张表 |

**具体命令**：
```bash
cd backend
alembic upgrade head
pytest tests/unit/test_output_parser.py tests/unit/test_openai_client.py -q
# 配置 mock（无需真实 Key）
curl -X PUT http://127.0.0.1:8000/api/v1/projects/1/llm-config \
  -H "Content-Type: application/json" \
  -d '{"provider":"mock","model":"mock-v1"}'
curl -X POST http://127.0.0.1:8000/api/v1/projects/1/llm-config/test
```

**验收标准**：
- `GET llm-config` 不返回明文 Key；只返回 `configured`/`key_hint`/`provider`/`is_mock`。
- `PUT` 保存后 Key 以 Fernet 密文入库；日志中搜不到 Key。
- Mock provider 的 `test` 返回成功且明确 `is_mock=true`；真实 provider 在无 Key 时返回明确错误而非假成功。
- 真实 OpenAI 兼容客户端通过本地假 HTTP 服务（httpx MockTransport）验证：正常 JSON、429 重试、超时、无效 JSON、空 choices。
- 业务流程输出包含候选流程、涉及页面、步骤、不确定点；`source=llm/mock`，推断项 `needs_confirmation`。
- 用例输出字段完整：`case_code/title/module/priority/preconditions/related_page_ids/steps/test_data/expected_result/assertions/assumptions`。
- 每个 step 有 `step_no/page_reference/action/target/value/description`；assertion 有 `assertion_type/target/expected/source/confidence`。
- 页面 ID 不属于当前项目时拒绝或修复并记录；无效 JSON 最多 2 次修复后失败，错误可诊断。
- 生成记录保存 prompt 版本、provider、model、is_mock、耗时、token（若返回）、原始响应安全摘要。
- 用例/流程支持查看、编辑、删除（软删除）、重新生成（P1）。

**风险与回退**：
- 无真实 Key → Mock 完成全部演示；真实客户端用假服务测试，文档标注“未真实供应商验证”。
- LLM 输出不稳定 → Pydantic 严格校验 + 有限修复 + 明确错误；不把无效数据写库。
- Prompt 注入 → 不可信内容分隔 + 明确指令 + 输出校验；不自动执行。
- 长上下文 → 页面摘要/元素裁剪/分页预算；记录截断策略。
- 加密密钥丢失 → 无法解密 Key，需要重新录入；文档说明。

---

### Phase 4：自动化脚本生成与安全校验（估算 2 天）✅

**目标**：按用例生成可追踪的 Pytest + Playwright 脚本；语法/安全检查；版本化；预览/编辑/下载。

**依赖**：Phase 3（用例、页面、LLM）。

**任务拆解**：

| # | 任务 | 关键文件 |
| --- | --- | --- |
| 4.1 | 脚本生成 Prompt | `ai/prompts/script_generation.v1.md` |
| 4.2 | 脚本生成器 | `ai/script_generator.py` |
| 4.3 | AST/安全校验 | `execution/script_validator.py`、`tests/unit/test_script_validator.py` |
| 4.4 | 脚本模型/迁移 | `models/test_script.py` |
| 4.5 | 脚本 API | `api/v1/endpoints/test_scripts.py`、`schemas/test_script.py` |
| 4.6 | 版本/编辑/下载 | 版本号自增；编辑后重新校验；下载 Content-Disposition |
| 4.7 | Mock 脚本模板 | Mock provider 生成可执行的导航/登录/购物车脚本 |

**具体命令**：
```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/1/ai/generate-scripts \
  -H "Content-Type: application/json" \
  -d '{"test_case_ids":[1,2]}'
curl http://127.0.0.1:8000/api/v1/projects/1/test-scripts
pytest backend/tests/unit/test_script_validator.py -q
```

**验收标准**：
- 至少一个用例生成语法有效的 `.py` 脚本；`ast.parse` 通过；脚本关联 `test_case_id`。
- 脚本只使用允许的导入（`pytest`、`playwright.sync_api` 等）；包含 `def test_`；有断言/`expect`。
- 危险脚本被拒绝：`import os/subprocess/socket/requests`、`eval/exec/open/__import__`、`os.system`、双下划线属性、超大文件。
- 校验报告结构化（line/col/code/message/severity），前端可展示。
- 编辑脚本生成新版本；旧版本保留；`status=validated` 才允许执行。
- 下载文件名安全（无路径穿越），内容与数据库一致。
- 脚本内容 ≤60 KB，文件名 ≤128 字符。

**风险与回退**：
- LLM 生成定位器不稳定 → Prompt 要求 role/label/placeholder/text 优先；Mock 模板使用 demo 站点真实元素；脚本执行失败可由失败分析解释。
- AST 黑名单误杀 → 采用“导入白名单 + 危险调用拒绝”，报告可读；必要时放宽非危险标准库（仅白名单）。
- 绕过 AST → 明确 AST 不是沙箱；执行隔离与 Docker 是最终边界。

---

### Phase 5：受控执行、结果解析与报告（估算 3–4 天）✅

**目标**：在独立工作目录执行 pytest；解析逐条结果；生成 HTML 报告/日志/截图；支持超时与取消；本地模式可验证；Docker 模式未实现。

**依赖**：Phase 4；demo 站点；Playwright；Celery/Redis。

**任务拆解**：

| # | 任务 | 关键文件 |
| --- | --- | --- |
| 5.1 | 执行器接口/工作区 | `execution/runner.py`、`execution/workspace.py` |
| 5.2 | 本地执行器 | `execution/local_runner.py` |
| 5.3 | 注入 conftest | `execution/conftest_template.py`（URL 守卫/失败截图/凭据 fixture） |
| 5.4 | 结果解析 | `execution/result_parser.py`（JUnit XML） |
| 5.5 | 报告管理 | `execution/report_manager.py` |
| 5.6 | 执行模型/迁移 | `models/execution.py`（executions/execution_scripts/results） |
| 5.7 | 执行 API/任务 | `api/v1/endpoints/executions.py`、`tasks/execution_tasks.py` |
| 5.8 | 取消/超时 | DB `cancel_requested` + psutil 进程树终止 + Celery revoke |
| 5.9 | Docker Runner（未实现） | 环境阻塞；API 明确拒绝 docker 模式 |
| 5.10 | 失败分析 | `ai/failure_analyzer.py`、`api/v1/endpoints/ai.py` |

**具体命令**：
```bash
# 创建执行（选择已校验脚本）
curl -X POST http://127.0.0.1:8000/api/v1/projects/1/executions \
  -H "Content-Type: application/json" \
  -d '{"script_ids":[1,2],"timeout_seconds":120,"mode":"local"}'

curl http://127.0.0.1:8000/api/v1/tasks/<task_id>
curl http://127.0.0.1:8000/api/v1/executions/1/results
curl -OJ http://127.0.0.1:8000/api/v1/executions/1/report
pytest backend/tests/integration/test_execution_flow.py -q -m integration
```

**验收标准**：
- 对 demo 站点执行一个通过用例和一个失败用例；统计 `total/passed/failed` 正确。
- 每个结果有 `node_id/test_name/status/duration`；失败有 message/traceback 摘要；截图文件存在且路径可访问。
- `report.html` 可打开，包含通过/失败明细；报告/日志/截图仅项目所有者可访问。
- 超时任务在 `timeout_seconds` 后被终止并标记 `timeout`；取消任务在 1–2 次轮询内变为 `cancelled`，底层进程被终止。
- 执行目录唯一：`storage/executions/{execution_id}/`；并发执行不覆盖。
- 子进程环境不含 `DATABASE_URL`、`SMARTTEST_SECRET_KEY`、LLM Key；工作目录外不可写（本地模式尽力而为）。
- 生成脚本中的 `requests/socket/urllib` 等被 AST 拒绝；浏览器请求被 conftest 路由守卫限制在允许源。
- Docker 模式：当前未实现，API 返回 409；**不宣称已验证**。

**风险与回退**：
- Windows 进程树难以终止 → psutil `children(recursive=True)` + `terminate/kill`；必要时 `taskkill /T /F`。
- pytest/playwright 版本冲突 → 在 venv 固定版本；执行器使用同一解释器。
- 报告 XSS → 报告以附件下载/CSP 限制；日志脱敏。
- 本地模式不是沙箱 → UI/文档显著警告；默认仅允许 demo 域名；生产必须 Docker。
- Celery solo 取消延迟 → 执行器轮询 DB 标志；API 直接写标志，不依赖 worker 处理取消消息。

---

### Phase 6：前端完整业务流程（估算 4–5 天）✅

**目标**：用户从 UI 完成“建项目 → 配 LLM → 采集 → 看页面/关系 → 写需求 → 生成流程/用例 → 生成/校验脚本 → 执行 → 看结果/报告 → 失败分析”的端到端流程。

**依赖**：Phase 1–5 的 API 稳定。

**任务拆解**：

| # | 任务 | 关键文件 |
| --- | --- | --- |
| 6.1 | 布局/导航/项目上下文 | `src/layouts/AppLayout.vue`、`components/AppSidebar.vue`、`stores/project.ts` |
| 6.2 | API client/类型 | `src/api/client.ts`、`src/types/api.ts`（可由 OpenAPI 生成） |
| 6.3 | 项目概览/设置 | `views/ProjectOverview.vue`、`views/ProjectSettings.vue` |
| 6.4 | 页面管理 | `views/PagesView.vue`、`views/PageDetailView.vue`、`components/PageGraph.vue` |
| 6.5 | 业务流程 | `views/WorkflowsView.vue`（确认/编辑/推断标记） |
| 6.6 | 需求 | `views/RequirementsView.vue` |
| 6.7 | 用例 | `views/TestCasesView.vue`（生成/编辑/删除/来源标记） |
| 6.8 | 脚本 | `views/ScriptsView.vue`（预览/编辑/校验/下载） |
| 6.9 | 执行/报告 | `views/ExecutionsView.vue`、`views/ExecutionDetailView.vue` |
| 6.10 | 任务轮询 | `composables/useTaskPolling.ts`、`components/TaskProgress.vue` |
| 6.11 | Mock/真实徽标 | `components/LlmBadge.vue`、全局横幅 |
| 6.12 | 状态与确认 | `EmptyState/ErrorState/ConfirmDialog/Toast` |

**具体命令**：
```bash
pnpm --dir frontend install
pnpm --dir frontend dev
pnpm --dir frontend build
pnpm --dir frontend lint
```

**验收标准**：
- 从 UI 完成提示词第十章 12 步端到端流程，不手工调用内部 API。
- 所有主要按钮连接真实 API；没有“只有视觉效果”的按钮。
- 加载/空/错误/成功/确认状态齐全；长任务显示进度并可离开页面后回来继续查看。
- 刷新页面后项目、页面、用例、脚本、执行结果仍在（MySQL）。
- Mock 项目显著显示“Mock 演示模式”；生成记录/用例/脚本显示生成来源，不把 Mock 说成真实模型效果。
- 页面关系图可交互（节点/边/图例），至少列表 + SVG 图可用。
- `pnpm build` 通过；TypeScript 无 `any` 泛滥；API 类型与后端 schema 对齐。

**风险与回退**：
- shadcn-vue/Tailwind 4 配置摩擦 → 先用官方 CLI 初始化，组件按需；必要时用 Tailwind 手写等价组件，保持风格一致。
- 前端范围膨胀 → P0 页面先可用，P1 增强（SSE、复杂图）后置。
- 轮询过多 → 1.5–2 s 间隔，终态停止；页面隐藏时暂停。
- 类型漂移 → OpenAPI 生成 + CI 检查（P1）。

---


---

## 8.5 Phase 2–6 实际完成证据（2026-11-03）

| 阶段 | 验证项 | 实测结果 |
| --- | --- | --- |
| Phase 2 | DemoShop 独立站点 | 首页/登录/商品列表/详情/购物车/结算/订单/关于均可访问；`demo/demo123` 登录、加购、下单成功 |
| Phase 2 | URLPolicy | 8 项单元测试通过；私网/环回/元数据地址/危险链接/跨源链接被拒绝；开发 allowlist 精确到 `http://127.0.0.1:8001` |
| Phase 2 | 多页面探索 | 8 页、53 条关系；登录表单密码字段 `is_sensitive=true`；截图 66 KB；DOM 快照可下载；`max_pages=3/depth=1` 实测只采集 3 页 |
| Phase 2 | SSRF 实测 | `http://127.0.0.1:3306/` 与 `http://169.254.169.254/...` 的扫描任务均失败且不落页面 |
| Phase 3 | Mock LLM 配置 | `GET/PUT/Test` 成功；返回 `is_mock=true`；真实 Key 保存后响应仅 `****1234`，明文不出现在响应中 |
| Phase 3 | 流程/用例生成 | 生成 2 个流程、5 条用例；页面 ID 校验通过；`model_inference` 用例为 `needs_review`；生成记录 2 条，`is_mock=true` |
| Phase 3 | 真实客户端测试 | 4 项 httpx MockTransport 测试：正常解析、429 重试、401 不重试、空内容报错 |
| Phase 4 | 脚本生成/校验 | 5 个脚本 `validated`；6 项 AST/安全校验测试通过；危险导入/eval/缺断言/语法错误被拒绝 |
| Phase 4 | 实际执行脚本 | 5 个生成脚本显式运行：**5 passed** |
| Phase 5 | 执行通过/失败 | 执行 #1：1 passed / 1 failed；逐条结果、日志 4.3 KB、HTML 报告 39.6 KB、失败截图 150.6 KB |
| Phase 5 | 超时/取消 | 10s 超时执行 -> `timeout`；长任务取消 -> `cancelled`，进程树终止 |
| Phase 5 | 失败分析 | 失败结果生成 observed_error + inferred causes + suggestions；`is_mock=true` |
| Phase 6 | 前端构建 | `vue-tsc -b && vite build` 通过（2114 modules） |
| Phase 6 | 前端路由 | 11 条项目路由全部打开，0 console error / 0 pageerror |
| Phase 6 | UI 交互 | UI 创建需求 → 生成用例 → 生成脚本 → 创建执行 #4；执行详情显示 1 passed |

**仍未验证/未实现（不得写成已完成）**：
- DockerRunner / 容器执行隔离；当前 API 对 `mode=docker` 明确返回 409，不静默回退。
- 真实 LLM 供应商调用；无真实 API Key，仅 Mock + 假 HTTP 测试。
- 官方 shadcn-vue 基础组件、Table/Select/Checkbox/Alert/Dialog/Sonner 已接入。
- MySQL 8.0/Redis 7 精确组合；本机为 MySQL 9.4/Redis 8.10.3。

### Phase 7：测试、修复与交付（估算 2–3 天）✅

**目标**：可复现的测试证据、端到端演示、文档完整、已知限制诚实。

**依赖**：Phase 1–6。

**任务拆解**：
- 后端单元测试（URL、解析、AST、加密、错误处理）。
- 后端集成测试（项目隔离、采集、Mock 生成、执行）。
- 前端构建/lint；必要组件测试。
- `scripts/e2e_demo.py` 全流程脚本。
- 安全检查清单（密钥、SSRF、日志、路径、报告、执行）。
- README、TESTING、USER_GUIDE、KNOWN_LIMITATIONS 更新。
- 记录实际命令与输出；列出未验证项。

**具体命令**：
```bash
source .venv/Scripts/activate
ruff check backend
pytest backend/tests/unit -q
pytest backend/tests/integration -q -m integration
python scripts/e2e_demo.py --base-url http://127.0.0.1:8000
pnpm --dir frontend build
pnpm --dir frontend lint
```

**验收标准**：
- 上述命令实际执行并记录结果（通过/失败/跳过及原因）。
- E2E 脚本覆盖提示词第十章 12 步；生成执行记录与报告。
- 重启后端/worker 后数据仍在。
- README 从零启动步骤可复现；`.env.example` 无真实密钥。
- `KNOWN_LIMITATIONS.md` 区分：已完成并验证 / 已实现未验证 / 未实现 / 需用户提供。
- 无阻塞性错误；无 `pass`/`TODO`/`NotImplemented` 冒充完成。

---

## 5. 里程碑与演示顺序

| 里程碑 | 内容 | 对应阶段 | 演示价值 |
| --- | --- | --- | --- |
| M1 | 基础设施 + 项目管理 | Phase 1 | 前后端/DB/Celery 联通 |
| M2 | 多页面采集 | Phase 2 | 页面/元素/关系/边界 |
| M3 | Mock 智能生成 | Phase 3–4 | 流程/用例/脚本/校验 |
| M4 | 执行与报告 | Phase 5 | 通过/失败/截图/HTML |
| M5 | 完整 UI + 交付 | Phase 6–7 | 端到端答辩演示 |

**建议演示脚本（10–15 分钟）**：
1. 启动 MySQL/Redis/demo/后端/worker/前端（或提前启动）。
2. 创建项目 `DemoShop`，base_url `http://127.0.0.1:8001`。
3. LLM 选择 Mock，测试连接，展示 Mock 徽标。
4. 探索站点（max_pages=8, depth=2），展示任务进度、页面列表、元素、关系图。
5. 创建需求：登录/商品/购物车/结算；展示错误密码预期。
6. 生成并确认业务流程；指出 `model_inference` 标记。
7. 生成 4–5 条用例，展示结构化步骤/断言/假设。
8. 生成脚本，展示 AST 校验报告；演示一个被拒绝的危险脚本 fixture。
9. 执行通过用例 + 故意失败用例；展示统计、逐条结果、截图、HTML 报告。
10. 对失败结果做失败分析，区分“observed error”和“inferred cause”。
11. 重启后端，刷新页面证明 MySQL 持久化。
12. 展示 `KNOWN_LIMITATIONS.md` 与未验证项（Docker/真实 LLM）。

---

## 6. 风险登记册

| # | 风险 | 概率 | 影响 | 应对 | 回退 |
| --- | --- | --- | --- | --- | --- |
| R1 | 无 Docker，本地执行非沙箱 | 高 | 高 | 默认仅 demo 域名；显式本地模式；AST/URL/环境/超时；文档警告 | Docker 未实现；生产必须容器 |
| R2 | 无真实 LLM Key | 高 | 中 | Mock + 假 HTTP 测试 + 配置入口 | 用户提供 Key 后切换 |
| R3 | 便携 Redis 8.10.3 为第三方构建 | 中 | 中 | 仅 localhost、开发用、可设密码；Compose 用 Redis 7 | 应急 filesystem broker（标注偏差） |
| R4 | MySQL 9.4 与 8.0 差异 | 中 | 低 | 标准 SQL/JSON；Alembic；Compose 8.0 | 用户提供 8.0 实例 |
| R5 | Playwright 浏览器下载失败 | 中 | 中 | 系统 Chrome channel 回退 | 手动安装浏览器/换网络 |
| R6 | 前端依赖大版本摩擦 | 中 | 中 | create-vue 基线 + lockfile；最小组件 | 手写 Tailwind 组件 |
| R7 | LLM 输出无效/幻觉 | 高 | 中 | 严格 Pydantic + 修复上限 + 推断标记 | 重新生成/手工编辑 |
| R8 | Prompt 注入 | 中 | 高 | 不可信分隔、无工具调用、输出校验、不自动执行 | 人工复核 |
| R9 | SSRF/DNS rebinding | 中 | 高 | 多层 URL 校验 + 路由守卫 + 重定向复检 | Docker 出口代理（P2） |
| R10 | 脚本逃逸（本地模式） | 中 | 高 | AST 白名单 + 环境清洗 + 超时 + 工作区 | 仅 demo；生产 Docker |
| R11 | Windows Celery 取消不及时 | 中 | 中 | DB 标志 + psutil 杀进程树 | 缩短超时；重启 worker |
| R12 | 长任务阻塞 solo worker | 高 | 低 | 单任务串行；UI 排队提示 | Linux/Compose 提高并发 |
| R13 | 报告/日志 XSS | 低 | 中 | 附件下载/CSP；日志脱敏 | 仅本人访问；禁用内联 |
| R14 | JSON/DOM 体积过大 | 中 | 中 | 截断 + 文件存储 + 大小上限 | 降低 max_pages/字符预算 |
| R15 | 项目数据越权 | 低 | 高 | 全链路 project_id/owner_id 校验；集成测试 | 单用户本地；可选 API token |
| R16 | 密钥泄露 | 低 | 高 | Fernet、env、脱敏、gitignore、不回传 | 轮换 Key；审计日志 |

---

## 7. 工作量与优先级

| 阶段 | 估算 | 优先级 | 可并行 |
| --- | --- | --- | --- |
| Phase 0 | 0.5 天 | P0 | — |
| Phase 1 | 2–3 天 | P0 | 前端骨架可与后端并行 |
| Phase 2 | 3–4 天 | P0 | demo 站点可先于浏览器层 |
| Phase 3 | 3–4 天 | P0 | Mock provider 可与真实客户端并行 |
| Phase 4 | 2 天 | P0 | 依赖 Phase 3 |
| Phase 5 | 3–4 天 | P0 | 结果解析可与 runner 并行 |
| Phase 6 | 4–5 天 | P0/P1 | 按页面拆分 |
| Phase 7 | 2–3 天 | P0 | 文档可与测试并行 |
| **合计** | **约 20–26 人日** | | 建议 4–5 周（含调试/论文） |

> 估算不是承诺；以“可演示 MVP”优先。若时间紧张，先完成 M1–M4 的后端与最小 UI，再补 Phase 6 的完整体验。

---

## 8. 每阶段 Definition of Done

- 代码存在且可运行，不只是文档/截图。
- 关键路径有自动化测试或可复现命令。
- 错误路径有明确状态/日志，不静默失败。
- 安全边界有说明；未验证项不冒充已验证。
- 文档状态更新（本文件 + 相关设计文档）。
- 不引入未使用的大依赖；不留下假按钮/假数据。

---

## 9. 当前状态与下一步

| 项 | 状态 |
| --- | --- |
| Phase 0 审查与文档 | ✅ 完成 |
| Phase 1 骨架/基础设施 | ✅ 完成（2026-11-03） |
| Phase 2 采集/探索 | ✅ 完成（2026-11-03） |
| Phase 3 LLM/流程/用例 | ✅ 完成（2026-11-03） |
| Phase 4 脚本/校验 | ✅ 完成（2026-11-03） |
| Phase 5 执行/报告 | ✅ 完成（2026-11-03；Docker 未验证） |
| Phase 6 前端完整流程 | ✅ 完成（2026-11-03） |
| Phase 7 测试/交付 | ✅ 完成（2026-11-03） |
| Docker 隔离验证 | ⛔ 本机无 Docker/WSL |
| 真实 LLM 实测 | ⛔ 无 API Key |
| MySQL 8.0 精确验证 | ⛔ 本机 9.4；Compose 提供 8.0 |
| Redis 7 精确验证 | ⛔ 本机便携 8.10.3；Compose 提供 7 |

**Phase 7 最终验证（2026-11-03）**：
- `ruff check app migrations tests`：All checks passed
- `pytest tests -q`：36 passed
- `pnpm --dir frontend build`：vue-tsc + vite build 通过
- `alembic current`：0005 (head)
- `scripts/verify_env.py`：MySQL/Redis OK；系统 Chrome fallback 可用
- UI：11 条项目路由 0 console error；完整 UI 流程已实跑
- `python scripts/e2e_demo.py`：5 pages / 1 workflow / 2 cases / 1 validated script / execution #5 passed

**剩余可选/环境阻塞事项（不影响已交付 MVP）**：
1. 用户提供 Docker 后实现 DockerRunner，并用容器网络出口策略做真正的隔离验证。
2. 用户提供真实 OpenAI 兼容 Key 后，跑通真实供应商的生成/失败分析并记录差异。
3. 迁移剩余页面的 Table，以及 Select/Checkbox/Toast 到官方 shadcn-vue 组件。
4. 清理演示数据与临时截图；保留 `storage/` 结构与最小演示数据。

> Phase 7 完成后，不再扩展功能；先保证干净环境可复现、文档与真实验证一致。

