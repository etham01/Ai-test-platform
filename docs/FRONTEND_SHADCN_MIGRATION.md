# 前端 shadcn-vue 正式接入与迁移计划

> 版本：v1.0（2026-11-03）
> 范围：`frontend/` 展示层组件迁移。**不修改** API client、TypeScript 业务类型、路由路径、后端接口与页面业务逻辑。
> 目标：从“shadcn-vue 风格手写组件”升级为“官方 CLI 生成组件 + 薄兼容层”。

---

## 1. 当前现状审查

| 项 | 现状 | 结论 |
| --- | --- | --- |
| 框架 | Vue 3.5 + TypeScript + Vite 8 | 可直接接入 |
| 样式 | Tailwind CSS 4 + `@tailwindcss/vite` | 官方 CLI 支持 Tailwind 4 |
| `components.json` | 不存在 | 需要 CLI 初始化 |
| 组件目录 | `src/components/ui/{Button,Input,Textarea,Card,Badge,Modal,EmptyState}.vue` | 手写 cva/tailwind-merge 组件 |
| `src/lib/utils.ts` | 已提供 `cn()` | 与官方 CLI 默认 utils 兼容 |
| 主题 | `src/style.css` 中 `:root` + `@theme inline`，indigo 主色、success/warning 自定义 token | 初始化时需保留自定义 token |
| 依赖 | `class-variance-authority`、`tailwind-merge`、`clsx`、`@lucide/vue` | 与官方组件兼容；CLI 可能补充 `reka-ui` 等 |
| 视图引用 | 统一从 `@/components/ui/Xxx.vue` 导入 | 用薄兼容层保持引用不变，避免大范围改 views |
| 业务状态 | API client、types、router、Pinia、任务轮询均可用 | **不修改** |
| 已有验证 | `pnpm build` 通过；11 条项目路由 0 console error；UI 端到端流程通过 | 迁移后必须回归 |

### 1.1 现有组件的 API 约束

- `Button`：`variant=default|outline|ghost|destructive`，`size=default|sm|icon`，支持 `type`、`disabled`。
- `Input` / `Textarea`：支持 `v-model`（`modelValue` + `update:modelValue`）。
- `Card`：默认 slot，支持外部 `class`（如 `p-5`）。
- `Badge`：`variant=default|success|warning|muted|destructive`。
- `Modal`：`open`、`title`、`@close`，默认 slot + `footer` slot。
- 视图大量使用原生 `<table>`、`<select>`、`<input type="checkbox">`；这些先保持，避免破坏业务交互。

---

## 2. 迁移策略

### 2.1 官方 CLI 初始化

在 `frontend/` 执行：

```bash
# 本仓库实际使用 defaults（生成 reka-nova / neutral / lucide / CSS variables）
# 注意：CLI 要求根 tsconfig.json 中存在 @/* 路径别名。
pnpm dlx shadcn-vue@2.9.0 init --defaults --yes --no-reinstall
```

生成：

- `components.json`（aliases、tailwind css 路径、base color、icon library）
- 官方依赖（`reka-ui` 等，具体以 CLI 输出为准）
- 官方基础样式/动画依赖（如 `tw-animate-css`）
- `src/lib/utils.ts`（若已存在则保留/合并）

**备份**：初始化前把 `frontend/` 源码与配置复制到 `.dev/frontend-pre-shadcn/`（gitignored），用于回退和 diff。

### 2.2 组件目录与兼容层

官方组件通常生成在 `src/components/ui/{button,input,textarea,card,badge,dialog,table,...}/`，并带 `index.ts`。

为了**不改 views 的导入路径和业务逻辑**，保留现有 `src/components/ui/Button.vue` 等文件名，但把内部实现改为薄兼容层：

- `Button.vue` → 包装官方 `./button` 的 `Button`，保留默认 `type="button"` 与现有 variant/size 命名。
- `Input.vue` / `Textarea.vue` → 包装官方输入组件，同时保留 `v-model` 适配（官方组件若不声明 modelValue，则由兼容层转发 `value`/`input`）。
- `Card.vue` → 包装官方 `./card` 的 `Card`，保留默认 slot 与 class 透传。
- `Badge.vue` → 包装官方 `./badge`；`success/warning/muted` 映射到官方 variant + 自定义语义色 class。
- `Modal.vue` → 使用官方 `./dialog` 组件重构；保持 `open`、`title`、`@close`、默认/footer slot API 不变。
- 新增 `ConfirmDialog.vue` → 基于官方 Dialog，替换 `window.confirm`（Projects/Requirements）。
- 新增官方 `Table` 组件；在页面列表/用例/脚本/执行等**只替换表格标记**，不动数据逻辑。
- 可选：官方 `Alert`、`Sonner`（Toast）、`Select`、`Checkbox`；先接入组件库，页面逐批替换。

### 2.3 视觉主题

CLI 可能重写 `src/style.css`。合并原则：

- 保留 `:root` 的 indigo 主色、`--success`、`--warning`、`--radius`。
- 采用官方 base style 的动画/暗色变量（如存在）。
- 保留现有 `@theme inline` 映射，避免 `bg-background`、`text-muted-foreground` 等现有 class 失效。
- 不引入 Tailwind 3 配置；继续使用 Tailwind 4 CSS-first。

### 2.4 不改动的内容

- `src/api/client.ts`
- `src/types/api.ts`
- `src/router/index.ts`
- `src/stores/*`
- `src/composables/useTaskPolling.ts`
- 所有后端接口、任务流程、DemoShop
- 页面业务状态与 API 调用顺序

---

## 3. 分阶段执行

### Phase A：基础设施（本次第一步）

- 备份前端源码/配置。
- 执行官方 CLI init。
- 检查 `components.json`、依赖、`src/style.css` 差异。
- `pnpm build`。
- 记录 CLI 生成文件与是否覆盖现有文件。

**验收**：build 通过；现有页面仍能启动；`components.json` 正确指向 `src/style.css` 与 `@/components/ui`。

### Phase B：基础组件替换（第一批）

- 添加官方 `button input textarea card badge dialog table alert`。
- 用兼容层重写现有 5 个基础组件 + Modal。
- `pnpm build`；Playwright 打开项目列表/页面/用例/脚本/执行。
- 汇报改动文件与破坏性变更。

### Phase C：ConfirmDialog 与高频交互

- 新增 `ConfirmDialog.vue`。
- ProjectsView、RequirementsView 的 `window.confirm` 替换为真实 Dialog。
- `pnpm build` + UI 创建/删除项目、需求验证。

### Phase D：Table / Alert / Toast

- 在 Pages/TestCases/Scripts/Executions 中用官方 Table 结构替换原生表格标记（保留数据逻辑）。
- 将关键成功/错误提示逐步替换为官方 Alert；需要 Toast 时接入 Sonner。
- 每次替换后 build + 页面 smoke。

### Phase E：回归与文档

- 11 条项目路由 0 console error。
- 创建项目 → 生成用例 → 生成脚本 → 执行 的 UI 流程回归。
- 更新 `KNOWN_LIMITATIONS`：移除“未接入 shadcn-vue CLI”的旧限制。
- 记录最终组件清单与回退方式。

---

## 4. 风险与回退

| 风险 | 应对 |
| --- | --- |
| CLI 覆盖 `style.css` / `utils.ts` | 先备份；逐文件 diff；只保留必要变更并合并自定义 token |
| 官方 Input 不支持现有 `v-model` | 兼容层内部转发 `value`/`input`，views 不改 |
| 官方 Badge variant 不包含 success/warning | 兼容层映射到官方 variant + 语义色 class |
| 官方 Dialog 受控 open 行为变化 | Modal 兼容层保持 `open`/`@close` API；build + 交互验证 |
| Table/Select/Checkbox 改动破坏业务 | 先只替换基础组件；表格在独立阶段逐个替换；Select/Checkbox 保持原生或最后处理 |
| Tailwind 4 与官方样式冲突 | 不降级 Tailwind；使用 CSS-first；build 和视觉 smoke 双重验证 |
| 依赖版本冲突 | 以 pnpm-lock 锁定；只接受 CLI 推荐的兼容版本；出现冲突回退备份 |

---

## 5. 验收标准

- `pnpm --dir frontend build` 通过。
- 项目列表、页面管理、用例、脚本、执行页面可打开。
- 创建项目、生成用例、生成脚本、执行仍可用。
- 代码中存在官方 `components.json` 与 `src/components/ui/*` 官方组件目录。
- 基础组件内部使用官方 shadcn-vue 组件，而非纯手写 div。
- 不修改 API client、业务类型、路由和后端接口。

---

## 6. 当前进度（2026-11-03）

| 阶段 | 状态 | 实际结果 |
| --- | --- | --- |
| 现状审查 | ✅ 完成 | 已确认现状与依赖 |
| 迁移计划 | ✅ 本文档 | v1.0 |
| Phase A 基础设施 | ✅ 完成 | `components.json`、官方依赖、官方 CSS、`pnpm build` 通过 |
| Phase B 基础组件 | ✅ 完成 | Button/Input/Textarea/Card/Badge/Modal 已改为官方组件兼容层 |
| Phase C ConfirmDialog | ✅ 完成 | 项目/需求删除已使用官方 Dialog；UI 实测通过 |
| Phase D Table/Alert/Toast | ✅ 完成 | 所有列表/详情表格使用官方 Table；Select/Checkbox/Alert/Dialog/Sonner 已接入；views 层无原生 table/select/checkbox/input/textarea |
| Phase E 回归/文档 | ✅ 完成 | `pnpm build` 通过；11 条路由 0 console error；创建项目/生成用例/脚本/执行回归通过；本文档更新 |

### 6.1 实际生成/变更

- 官方 CLI 初始化：`components.json`（style `reka-nova`、baseColor `neutral`、icon `lucide`、CSS variables）。
- 官方组件目录：`src/components/ui/{button,input,textarea,card,badge,dialog,table,alert,select,checkbox,sonner}/`。
- 兼容层：`src/components/ui/{Button,Input,Textarea,Card,Badge,Modal}.vue` 内部改为官方组件；views 导入路径未变。
- 新增：`src/components/ConfirmDialog.vue`；替换 `window.confirm`。
- 所有列表/详情表格替换为官方 `Table`；Select/Checkbox 全部替换为官方组件；Requirements/Pages 使用官方 `Alert`；`AppLayout` 挂载官方 Sonner，关键成功操作触发 Toast。
- 修复 CLI 覆盖的 `src/lib/utils.ts`，恢复 `formatDate`/`errorMessage`，保留官方 `cn` 导出。
- **未修改**：API client、`src/types/api.ts`、router、stores、composables、后端接口。

### 6.2 构建/回归记录

- `pnpm --dir frontend build`：通过（官方组件 + 兼容层）。
- 11 条项目路由：项目列表/概览/页面/页面详情/流程/需求/用例/脚本/执行/执行详情/设置，0 console error。
- UI 实测：创建项目、删除项目、创建需求、删除需求（ConfirmDialog）、打开用例/脚本 Dialog、生成用例/脚本、创建执行。
- 兼容性：Button 默认 `type=button` 仍保留；Input/Textarea `v-model` 正常；Badge success/warning/muted 映射正常。

### 6.3 后续可选

- 目前 views 层已完成基础组件、表格、Select/Checkbox 全量迁移。
- 后续只做视觉微调/更多 Toast 场景，不涉及结构性迁移。

