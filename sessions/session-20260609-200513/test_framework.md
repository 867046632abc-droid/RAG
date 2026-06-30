# 功能测试
## 实验列表页面（List View）
### 初始化加载
#### 默认请求参数组合
**测试内容** 进入实验列表页后自动触发首次查询；请求参数包含默认分页参数、固定参数`orderBy: update_time DESC`与`tenantId`；未设置筛选条件时`query`为空或为默认值，返回数据可正常渲染到表格
#### 空数据状态
**测试内容** 接口返回空列表且`total=0`时，表格展示空状态；分页器展示与空数据一致的状态（如仅1页/不可翻页），页面不报错
### Loading 状态联动
#### 首次加载 Loading
**测试内容** 首次进入页面请求期间筛选区与表格展示loading反馈；请求结束后loading关闭且内容更新
#### 筛选触发 Loading
**测试内容** 修改任一筛选条件触发查询时，筛选区与表格loading状态同步开启；响应完成后关闭且列表刷新为新条件结果
#### 分页触发 Loading
**测试内容** 切换页码/页大小触发查询时，表格loading正确展示；完成后列表与分页信息同步更新
### 分页与排序
#### 翻页与total展示
**测试内容** 使用分页器切换不同页码后按新分页参数请求；返回的`total`回填到分页器；列表展示与当前页一致
#### 修改pageSize
**测试内容** 修改每页条数后按新`pageSize`请求；列表条数变化符合`pageSize`；分页器页数与`total`匹配
#### 默认排序（按更新时间倒序）
**测试内容** 在无额外排序交互的情况下，列表默认以`update_time DESC`顺序呈现；分页切换后排序规则保持一致
### 请求中止（AbortController）
#### 快速连续筛选变更
**测试内容** 连续快速修改筛选条件触发多次查询时，上一次未完成请求被abort且不回填旧数据；最终仅最新请求结果展示
#### 快速分页切换
**测试内容** 快速切换页码触发并发请求时，上一次请求被abort；表格最终展示最新页数据且分页器状态一致
### 接口异常兜底
#### 接口失败回填规则
**测试内容** 接口返回错误/网络失败时，`list`置空、`total`置0；页面不崩溃且表格展示空状态；loading最终关闭
#### 失败后的可恢复操作
**测试内容** 在失败后再次修改筛选或分页可重新发起请求并成功回填；失败状态不影响后续正常使用

## 筛选区（Filter）
### 字段展示与取值
#### Experiment ID 输入框
**测试内容** 输入数字/非数字/空值时，筛选值按组件设计回传；触发查询时请求参数中对应`experiment_id`字段赋值符合输入（含清空后字段移除或置空的一致性）
#### Experiment name 输入框
**测试内容** 输入正常文本、空值与包含空格文本时，触发查询后请求参数`name`传递正确；清空后恢复不筛选状态并刷新列表
#### Stage 下拉框
**测试内容** 下拉选项包含`AB Confirm/Dryrun/AB Test/AB Finish`且与常量一致；选择任一项触发查询并正确传参；清空选择后取消该条件并刷新
#### Experiment status 下拉框
**测试内容** 下拉选项与`ExternalExperimentStatus`到文案映射一致；选择后请求参数传递为后端枚举值（而非文案）；清空后取消筛选
#### Review status 下拉框
**测试内容** 下拉选项与`ExternalExperimentReviewStatus`到文案映射一致；选择后请求参数传递为后端枚举值；清空后取消筛选
#### Creator 用户选择（FormUserSelector）
**测试内容** 选择单个/多个用户（按组件能力）后触发查询；请求参数中`creators`字段传递正确；清空选择后取消筛选并刷新
#### Updater 用户选择（FormUserSelector）
**测试内容** 选择单个/多个用户后触发查询；请求参数中`operators`字段传递正确；清空后取消筛选并刷新
#### Update time 时间范围（dateTimeRange）
**测试内容** 选择起止时间后触发查询；请求参数中起止时间字段（按IDl定义）传递正确（含时区/格式一致性）；仅选起或仅选止时按组件约束处理且不导致页面报错；清空后取消筛选并刷新
#### Only view mine 勾选框
**测试内容** 勾选/取消勾选均可触发查询；勾选状态在刷新列表后保持与UI一致
### Only view mine 联动逻辑
#### creators/operators均为空时的自动填充
**测试内容** 在Creator与Updater均未选择的情况下勾选Only view mine，自动将当前登录用户名填充到请求参数`creators`与`operators`；列表刷新为“与我相关”数据
#### creators已设置时的行为
**测试内容** 已手动选择Creator后勾选Only view mine，不覆盖已有`creators`值；若`operators`为空则仅自动填充`operators`；触发查询并按合并后的参数请求
#### operators已设置时的行为
**测试内容** 已手动选择Updater后勾选Only view mine，不覆盖已有`operators`值；若`creators`为空则仅自动填充`creators`；触发查询并按合并后的参数请求
#### 取消勾选后的参数恢复
**测试内容** 取消Only view mine后，请求参数不再强制注入当前用户名；若之前仅因自动填充产生的值，取消后应恢复为未筛选或回到用户手动设置的值（以实现为准保持一致）
### 500ms 防抖触发
#### 单字段连续输入
**测试内容** 在Experiment name/ID中连续输入时，500ms内不应频繁发起多次请求；停止输入超过500ms后仅发起一次查询且参数为最终输入值
#### 多字段快速连续修改
**测试内容** 在500ms内连续修改多个筛选字段时，仅在最后一次变更后等待500ms触发一次查询；请求参数包含所有最新筛选条件
### 筛选触发的分页重置
#### 变更筛选条件后的分页状态
**测试内容** 当前处于非第一页时修改任一筛选条件，分页重置为第一页并发起查询；返回数据与第一页一致且分页器当前页显示为1

## 表格展示（Table Columns）
### 基础字段列
#### Experiment ID 列
**测试内容** 列表中`experiment_id`展示完整且与接口返回一致；空值/异常值（如0、超大数）展示符合组件默认行为且不影响渲染
#### Experiment name 列
**测试内容** `name`展示完整；超长文本按表格默认策略处理（省略/换行以实现为准）且不破坏布局
### Stage 列（TicketStatusTag）
#### PipelineStage 兼容映射
**测试内容** 后端返回Stage为`AB Confirm/Dryrun/AB Test/AB Finish`或等价枚举时，映射后传入TicketStatusTag的`stage`值与组件要求兼容；展示的标签样式与release-management一致
#### 异常Stage兜底
**测试内容** 后端返回未识别Stage值时，Stage列展示不报错；兜底展示策略（空/默认标签/原值）与实现保持一致
### Status 列（运行状态文案）
#### 枚举到文案映射
**测试内容** 不同`ExternalExperimentStatus`枚举值在表格中展示为对应文案（如进行中/已结束/失败等）；映射结果与constants中的配置一致
#### 异常Status兜底
**测试内容** 未识别的status值展示不报错；兜底显示策略一致且不影响其他列渲染
### Creator & create time 列
#### 用户信息展示（UserCard）
**测试内容** `creator`字段使用UserCard展示；缺失/空creator时组件渲染不崩溃且展示符合默认占位策略
#### 创建时间展示（formatTZ）
**测试内容** `addTime`为时间戳或字符串时能被formatTZ正确格式化为`YYYY-MM-DD HH:mm:ss`；时间为空/非法时展示兜底不报错
### Updater & update time 列
#### 用户信息展示（UserCard）
**测试内容** `operator`字段使用UserCard展示；缺失/空operator时渲染正常且有一致占位
#### 更新时间展示（formatTZ）
**测试内容** `updateTime`格式化展示正确；为空/非法时兜底不报错
### Action 列
#### 右侧固定与按钮样式
**测试内容** Action列固定在右侧（横向滚动时保持可见）；按钮主题为`borderless`且样式与release-management一致
#### Experiment detail 跳转
**测试内容** 点击某行“Experiment detail”后调用`window.open(getExperimentDetailUrl(record))`；新窗口打开的URL包含该行必要标识（如experiment_id及所需的review_id/flight_id等拼接策略）且不依赖详情页实现
#### Operation record 按钮显示策略
**测试内容** 若实现操作记录：按钮展示且点击后通过URL参数控制侧边栏展示，刷新页面后参数仍能保持打开状态（以实现逻辑为准）；若暂不支持：按钮不展示且Action列布局不异常

## 跳转与 URL 生成（utils/url.ts）
### getExperimentDetailUrl
#### 必填字段拼接
**测试内容** 传入包含`experiment_id`的record时生成完整详情页路由；不同记录生成的URL可区分且稳定
#### 可选字段拼接
**测试内容** record包含`review_id`或`flight_id`时，URL按约定规则追加参数；缺失可选字段时仍可生成可用URL且不出现`undefined/null`字样
#### 异常输入兜底
**测试内容** record缺少关键字段或字段类型异常时，函数返回值符合兜底策略（如返回基础路径或空字符串）且点击跳转不会导致页面崩溃

## 接口调用策略
### 优先 SearchExperiment
#### 正常调用与类型回填
**测试内容** 接口可用时调用`httpService.SearchExperiment`；请求参数与`SearchExperimentReq`一致；返回数组子项回填到`list`并驱动表格渲染
### 占位 SearchReleaseTicket（SearchExperiment 不可用）
#### 特殊筛选条件注入
**测试内容** 在占位模式下调用`httpService.SearchReleaseTicket`时会注入约定的特殊筛选条件（如`entityType/changeType`特定值）以仅返回实验数据；列表字段映射到ExperimentItem所需字段后可正常展示
#### 切换策略一致性
**测试内容** 占位接口与正式接口在分页、筛选、防抖、abort、失败兜底等行为上一致；不会出现因字段不齐导致的渲染崩溃（缺失字段按兜底策略处理）

## 常量与枚举映射（constants.ts）
### FILTER_FIELD 字段管理
#### 字段名一致性
**测试内容** Filter表单各字段的name与FILTER_FIELD常量一致；提交/变更时回传的values键名与query合并逻辑一致，避免出现字段错传或遗漏
### 下拉选项常量
#### STAGE_OPTIONS
**测试内容** Stage下拉项与PRD定义一致；value与后端枚举/请求参数一致，label为页面展示文案
#### EXPERIMENT_RUN_STATUS_OPTIONS
**测试内容** 运行状态下拉项覆盖需求所列典型状态；value为后端枚举值、label为中文文案；选择后表格Status列展示与筛选含义一致
#### REVIEW_STATUS_OPTIONS
**测试内容** 评审状态下拉项与后端枚举值映射一致；选择后请求参数正确传递并影响列表结果
### 枚举映射能力
#### ExternalExperimentStatus 映射
**测试内容** 映射函数/对象对已知枚举返回稳定中文文案；对未知枚举有明确兜底返回且不影响表格渲染
#### ExternalExperimentReviewStatus 映射
**测试内容** 映射对已知评审状态返回稳定文案；未知值兜底策略一致
#### PipelineStage 映射到 TicketStatusTag 入参
**测试内容** 后端返回的stage经过映射后满足TicketStatusTag要求；映射表缺失项时不导致组件报错