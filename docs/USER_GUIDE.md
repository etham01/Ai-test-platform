# SmartTest 使用指南

> 版本：v1.0（2026-11-03）
> 适用：本地开发/毕业设计演示。生产部署前请阅读安全文档。

---

## 1. 启动顺序

```bash
# 1) 开发服务（项目独立 MySQL 3307 + 便携 Redis 6379）
bash scripts/fetch_redis.sh
bash scripts/dev_services.sh start
bash scripts/dev_services.sh status

# 2) Python 依赖
source .venv/Scripts/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# 3) 迁移
cd backend && alembic upgrade head && cd ..

# 4) DemoShop
python -m uvicorn demo_site.main:app --host 127.0.0.1 --port 8001

# 5) 后端
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 6) worker（Windows）
cd backend
celery -A app.tasks.celery_app:celery_app worker --loglevel=INFO --pool=solo --concurrency=1

# 7) 前端
pnpm --dir frontend install
pnpm --dir frontend dev
```

访问：

- 前端：http://127.0.0.1:5173
- API 文档：http://127.0.0.1:8000/docs
- DemoShop：http://127.0.0.1:8001

演示账号：`demo / demo123`。

自动端到端冒烟（会创建并软删除临时项目）：

```bash
python scripts/e2e_demo.py
```

---

## 2. 第一次演示

1. 进入「项目」→「新建项目」。
   - 名称：DemoShop 演示项目
   - 起始 URL：`http://127.0.0.1:8001`
   - 浏览器：系统 Chrome（或 Chromium）
2. 进入项目 →「页面」→「开始探索」。
   - 默认 8 页、深度 2；进度条会轮询任务状态。
3. 打开任意页面查看元素、截图、DOM 和关系。
4. 「测试需求」创建需求并勾选关联页面。
5. 「业务流程」选择需求 →「分析流程」；确认候选流程。
6. 「测试用例」选择需求 →「生成用例」；查看 `needs_review` 的 model_inference 断言。
7. 「脚本」勾选用例 →「生成脚本」；预览/编辑/重新校验/下载。
8. 「执行与报告」勾选已验证脚本 →「开始执行」；进入详情查看统计、逐条结果、截图、日志、HTML 报告。
9. 对失败结果点击「失败分析」，查看 observed_error 与 inferred_causes。

---

## 3. LLM 配置

进入项目 →「设置」：

- **Mock（默认）**：不需要 Key；结果来自确定性模板，页面会显示黄色 Mock 徽标/横幅。
- **OpenAI 兼容**：
  - Base URL：建议包含 `/v1`（如 `https://api.example.com/v1`）。
  - 模型名：供应商支持的模型 ID。
  - API Key：只写；保存后只显示 `****xxxx`，不会回传明文。
  - 「测试连接」会实际请求上游；失败会显示明确错误。
- 密钥通过 `SMARTTEST_SECRET_KEY`（生产）或 `.dev/secret.key`（开发）加密；不要提交 `.env`/`.dev`。

---

## 4. 任务与进度

- 探索、流程分析、用例/脚本生成、执行、失败分析都是异步任务。
- 任务状态：`queued → running → succeeded/failed/cancelled`。
- 前端轮询约 1.5s；终态停止。
- 「执行」页面可以取消运行中的任务；runner 会尝试终止 pytest/浏览器进程树。
- 任务失败时先看任务 `error`，再查看执行日志/后端日志。

---

## 5. 常见问题

### MySQL 未启动/端口占用

```bash
bash scripts/dev_services.sh status
bash scripts/dev_services.sh restart
```

默认项目实例使用 3307，避免和系统 MySQL 3306 冲突。不要同时运行 `docker-compose.yml` 的 MySQL（同样映射 3307）。

### Redis/Celery 任务一直 queued

- 确认 `bash scripts/dev_services.sh status` 中 Redis 为 UP。
- 确认 Celery worker 使用 `--pool=solo` 且已显示 ready。
- 查看 worker 输出与任务日志；`TASK_ENQUEUE_FAILED` 表示 Redis/worker 未就绪。

### 浏览器启动失败

- 优先设置 `PLAYWRIGHT_CHANNEL=chrome` 使用系统 Chrome。
- 或执行 `python -m playwright install chromium`。
- 执行器与页面采集都读取 `PLAYWRIGHT_CHANNEL`。

### 扫描被拒绝

- 默认只允许项目 base_url 同源；私网/环回/元数据地址被 SSRF 策略拒绝。
- 本地 demo 需要 `.env` 中精确的 `SMARTTEST_DEV_ALLOWED_TARGETS=http://127.0.0.1:8001`。
- 不要全局关闭 SSRF 检查。

### 执行失败/超时

- 查看执行日志与 traceback；失败截图在结果行「截图」。
- 默认本地执行不是沙箱；只对受控 demo 使用。
- 超时/取消会杀掉进程树；残留 Chrome 可在任务管理器检查。

### 报告打不开

- 报告接口要求项目归属；使用前端按钮或带登录态/同源访问。
- 报告是下载附件；浏览器下载后本地打开。

---

## 6. 数据与重置

- 业务库：`smarttest`；测试库：`smarttest_test`。
- 执行工作区：`storage/executions/{id}/`。
- 页面 DOM/截图：`storage/projects/{project_id}/pages/{page_id}/`。
- 删除项目为软删除，执行历史保留；不要直接删 MySQL 数据文件。
- 重新演示可新建项目/需求，或在明确备份后清理 storage 与业务表。

---

## 7. 重要限制

- 本机无 Docker/WSL：Docker 执行器未实现/未验证；`mode=docker` 会返回 409。
- 真实 LLM 供应商未用真实 Key 验证；Mock 与真实客户端不是同一质量。
- 本地执行不是安全沙箱。
- 基础组件、Table/Select/Checkbox/Alert/Dialog/Sonner 已接入官方 shadcn-vue CLI。
- 详见 `docs/KNOWN_LIMITATIONS.md` 与 `docs/SECURITY.md`。
