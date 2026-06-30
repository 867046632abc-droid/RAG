# 实验列表组件 Spec Coding 提示词

## 指导原则

你现在需要在一个大型、成熟的前端 Monorepo 仓库 `tsop-fe` 中，于 `apps/release` 应用内开发一个全新的“实验列表”页面。

**核心原则**：严格遵守 `apps/release` 应用内现有的“发布列表”（`release-management`）功能模块的开发模式。**禁止引入新的技术栈、状态管理方案或组件库**，最大化复用已有组件、Hooks 与工具函数。

---

### 一、目标与范围

**目标**：仅实现“实验列表”的核心视图（List View），提供筛选、分页、排序和查看基本信息的功能。

**范围约束**：

- **不包含**：实验的创建、编辑、或详情页内部的复杂业务逻辑。
- **列表跳转**：点击列表项中的“详情”按钮，仅需跳转到对应的实验详情页路由，不负责详情页的实现。
- **技术复用**：全面复用 `apps/release` 内已有的成熟组件，包括但不限于：

  - 表格：`@douyinfe/semi-ui` 的 `Table`。
  - 筛选器：基于 `@byted-materials/filter` 封装的 `Filter` 组件。
  - 状态标签：`@/components/ticket-status-tag` (`TicketStatusTag`)。
  - 用户信息：`@byted-materials/usercard` 的 `UserGroup` (`UserCard`)。
  - 时间格式化：`@tns-tsop/base` 的 `formatTZ`。

---

### 二、代码位置与文件结构

请在 `apps/release/src/expose/` 目录下创建新的模块 `experiment-management`，并参照 `release-management` 的结构创建以下文件：

- **组件目录**： `src/expose/experiment-management/components/`

  - `filter.tsx`：筛选区组件，对标 `release-management/components/filter.tsx`。
  - `list.tsx`：表格组件，对标 `release-management/components/list.tsx`。
- **Hooks 目录**：`src/expose/experiment-management/hooks/`

  - `use-experiment-list.ts`：列表核心逻辑 Hook，对标 `release-management/hooks/use-release-list.ts`。
- **常量与工具函数**：

  - `constants.ts`：存放筛选字段、下拉选项、状态映射等常量。
  - `utils/url.ts`：提供 URL 生成函数，如 `getExperimentDetailUrl`。
  - `context.ts`（可选）：如果需要 Tabs 等上下文配置，可参考 `release-management/context.ts` 创建。

---

### 三、接口与数据结构

#### 1. API 调用

- **首选方案**：如果后端 `ms_api_experiment` 服务已提供 `SearchExperiment` 接口，请使用 `httpService.SearchExperiment` 进行调用。其请求与返回类型参考 BAM IDL 定义。
- **占位方案**：若 `SearchExperiment` 接口暂不可用，为了联调和占位，请临时复用 `httpService.SearchReleaseTicket` 接口。调用时，需传入一个特殊的、约定好的筛选条件（如 `entityType` 或 `changeType` 的特定值），以确保仅拉取由“实验”创建的发布工单。此部分实现需要添加明确的 `// TODO: ...` 注释，待后端接口就绪后替换。

#### 2. 核心数据结构

列表项 `ExperimentItem` 的类型，应直接使用 `SearchExperiment` 返回的数组子项类型。如果自行定义，至少应包含以下字段，并注意与后端实际返回保持一致：

```TypeScript
export interface ExperimentItem {
  experiment_id: number;
  name: string;
  creator: string;
  operator: string;
  addTime: number; // or string, as timestamp
  updateTime: number; // or string, as timestamp
  
  // 阶段：对应后端 PipelineStage，用于 TicketStatusTag 组件
  // AB Confirm -> Draft
  // Dryrun -> Dryrun
  // AB Test -> ABTest
  // AB Finish -> Finish
  stage: PipelineStage;

  // 运行状态：对应后端 ExternalExperimentStatus
  status: ExternalExperimentStatus;

  // 评审状态：对应后端 ExternalExperimentReviewStatus
  review_status: ExternalExperimentReviewStatus;

  // 以下字段仅用于跳转，不在列表中直接展示
  review_id?: number;
  flight_id?: number;
}

```

---

### 四、筛选区实现（Filter）

**位置**：`src/expose/experiment-management/components/filter.tsx`

1. **组件复用**：

   - 使用 `@byted-materials/filter` 的 `Filter` 组件和 `@douyinfe/semi-ui` 的 `Form`。
   - 整体结构和交互逻辑仿照 `release-management/components/filter.tsx`。
2. **筛选字段**：

   - `Experiment ID`: `Form.Input`，对应 `experiment_id`。
   - `Experiment name`: `Form.Input`，对应 `name`。
   - `Stage`: `Form.Select`，选项为 `AB Confirm`, `Dryrun`, `AB Test`, `AB Finish`。
   - `Experiment status`: `Form.Select`，选项为 `进行中`, `已结束`, `失败` 等（需将 `ExternalExperimentStatus` 枚举映射为文案）。
   - `Review status`: `Form.Select`，选项为 `评审中`, `已通过`, `未通过` 等（需将 `ExternalExperimentReviewStatus` 枚举映射为文案）。
   - `Creator`: `FormUserSelector` 组件。
   - `Updater`: `FormUserSelector` 组件。
   - `Update time`: `Form.DatePicker`，类型为 `dateTimeRange`。
   - `Only view mine`: `Form.Checkbox`。
3. **交互逻辑**：

   - **防抖查询**：所有筛选条件的变更，都应通过 `useDebounceFn` 在 **500ms** 后触发一次列表查询。
   - **"Only view mine" 逻辑**：当 `Only view mine` 被勾选时，自动将当前登录用户的 `username` 填充到 `creators` 和 `operators` 查询参数中（如果这两个字段为空）。此逻辑参考 `release-management` 的实现。

---

### 五、表格实现（List）

**位置**：`src/expose/experiment-management/components/list.tsx`

1. **组件复用**：

   - 使用 `@douyinfe/semi-ui` 的 `Table` 组件。
   - 表格顶部应具备 `sticky` 效果。
2. **表格列（Columns）定义**：

   - **Experiment ID**：
   
     - `dataIndex`: `experiment_id`
   - **Experiment name**：
   
     - `dataIndex`: `name`
   - **Stage**：
   
     - `dataIndex`: `stage`
     - `render`: 复用 `TicketStatusTag` 组件进行渲染，传入映射后的 `PipelineStage` 枚举值。如果后端直接返回 `Draft`/`Dryrun` 等，确保与 `TicketStatusTag` 的 `stage` prop 兼容。
   - **Status**：
   
     - `dataIndex`: `status`
     - `render`: 将后端的 `ExternalExperimentStatus` 枚举值映射为对应的运行状态文案（如：进行中、已暂停、已结束）。可参考 `release-management/helper.ts` 中的 `getReleaseStatusByPipelineRunStatus` 实现一个实验专用的映射函数。
   - **Creator & create time**：
   
     - `dataIndex`: `creator`
     - `render`: 使用 `UserCard` 展示创建者信息，下方展示格式化后的创建时间（`formatTZ(record.addTime, 'YYYY-MM-DD HH:mm:ss')`）。
   - **Updater & update time**：
   
     - `dataIndex`: `operator`
     - `render`: 使用 `UserCard` 展示更新者信息，下方展示格式化后的更新时间。
   - **Action** (右侧固定列 `fixed: 'right'`)：
   
     - `render`:
     
       - **Experiment detail** 按钮：
       
         - `theme="borderless"`。
         - `onClick`: `() => window.open(getExperimentDetailUrl(record))`。
       - **Operation record** 按钮：
       
         - `theme="borderless"`。
         - `onClick`: 仿照 `release-management` 的实现，通过 URL 参数控制操作记录侧边栏的展示。如果暂不支持，可先隐藏此按钮。

---

### 六、核心 Hook 实现 (`use-experiment-list`)

**位置**：`src/expose/experiment-management/hooks/use-experiment-list.ts`

此 Hook 是列表页的数据流和交互核心，严格对标 `use-release-list.ts`。

1. **State 管理**：

   ```TypeScript
   const [loading, setLoading] = useState(false);
   const [list, setList] = useState<ExperimentItem[]>([]);
   const [pagination, setPagination] = useState(DEFAULT_PAGINATION);
   const [query, setQuery] = useState<Partial<SearchExperimentReq>>({});
   // 可选，如果需要 Tabs
   const [activeTab, setActiveTab] = useState(...);
   
   ```
2. **核心数据获取 (`fetchData`)**：

   - **请求参数组合**：
   
     - 合并 `pagination`、`query` 和固定参数。
     - 固定参数应包含：`orderBy: 'update_time DESC'` 和 `tenantId: getTenant().tenantId`。
   - **请求中止**：
   
     - 使用 `AbortController` 实例。在每次发起新请求前，调用 `abort()` 中止上一次未完成的请求。
   - **数据回填与异常处理**：
   
     - 请求成功后，更新 `list` 和 `pagination.total`。
     - `catch` 异常时，将 `list` 置为空数组，`total` 置为 0，并打印错误日志。
     - `finally` 中设置 `setLoading(false)`。
3. **暴露方法**：

   - `handleFilter(values: Partial<SearchExperimentReq>)`: 使用 `useDebounceFn` 包装，接收 `filter.tsx` 传来的值，更新 `query` state，并将分页重置为第一页。
   - `handlePaginationChange(currentPage: number, pageSize: number)`: 更新 `pagination` state。
   - `handleTabChange(key: string)`: （可选）如果实现 Tabs，用于更新 `activeTab` state 并重置分页。

---

### 七、常量与映射 (`constants.ts`)

**位置**：`src/expose/experiment-management/constants.ts`

- 定义 `FILTER_FIELD` 常量枚举，用于统一管理筛选表单的字段名。
- 定义 `STAGE_OPTIONS`，用于 `Stage` 筛选器的下拉列表。
- 定义 `EXPERIMENT_RUN_STATUS_OPTIONS`，用于 `Experiment status` 筛选器的下拉列表。
- 定义 `REVIEW_STATUS_OPTIONS`，用于 `Review status` 筛选器的下拉列表。
- 提供状态映射函数或对象，用于将后端的 `ExternalExperimentStatus`, `ExternalExperimentReviewStatus`, `PipelineStage` 枚举值转换为前端展示的文案标签。

---

### 八、URL 与跳转 (`utils/url.ts`)

**位置**：`src/expose/experiment-management/utils/url.ts`

- 实现 `getExperimentDetailUrl(record: ExperimentItem): string` 函数。
- 该函数负责根据实验列表项的数据，拼接生成跳转到“实验详情页”的完整路由。其逻辑对标 `getEntityReleaseDetailUrl`。
- 关于进入 Libra 详情页的逻辑，由实验详情页内部处理，列表页无需关心。

---

### 九、性能与容错

- **防抖**：筛选查询必须有 500ms 防抖。
- **分页**：数据必须通过分页请求，禁止一次性拉取全量数据。
- **请求中止**：快速切换筛选条件或分页时，必须中止上一次未完成的查询。
- **异常兜底**：接口请求失败时，表格应展示空状态，页面不应崩溃。
- **加载状态**：在数据请求期间，表格和筛选区应有明确的 `loading` 状态反馈。

---

### 十、文案与样式

- **文案**：所有 UI 文案（按钮、标签、标题等）风格与 `apps/release` 保持一致。
- **样式**：

  - 复用 `TicketStatusTag` 的已有样式。
  - 表格 Action 列的按钮使用 `borderless` 主题。
  - 整体布局、间距、字体等，与 `release-management` 页面保持视觉统一。

---

### 十一、交互附加（可选）

- 如果后端支持按实验对象或实体类型（如 `strategy`, `strategy-group`, `feature`）进行筛选，可以在列表顶部增加一个 `Tabs` 组件。
- Tab 的实现方式参考 `release-management`，通过 `activeTab` 状态来动态修改 `fetchData` 的请求参数。
- 如果后端暂不支持，此功能可以不做。
