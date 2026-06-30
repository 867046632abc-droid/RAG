# 功能测试
## 实验列表页面（List View）
### 初始化加载
#### 默认请求参数组合
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
**[tag]** e2e
###### **操作步骤** 1. 等待页面完成加载
####### **预期结果** 表格中展示实验列表数据，包含Experiment ID、Experiment name、Stage、Status、Creator & create time、Updater & update time和Action列
####### **预期结果** 分页器显示当前页码为1，每页条数为默认值，且展示总条数total
####### **预期结果** 表格顶部呈现sticky效果，滚动页面时表头固定
#### 空数据状态
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 等待页面加载完成
####### **预期结果** 表格区域展示空状态
####### **预期结果** 分页器显示总页数为1页且不可翻页
####### **预期结果** 页面无报错信息
### Loading 状态联动
#### 首次加载 Loading
##### **前置条件** 访问 apps/release/src/expose/experiment-management
**[tag]** e2e
###### **操作步骤** 1. 页面开始加载
####### **预期结果** 筛选区展示loading状态反馈
####### **预期结果** 表格区域展示loading状态反馈
####### **操作步骤** 2. 等待接口请求完成
######## **预期结果** 筛选区loading状态关闭
######## **预期结果** 表格区域loading状态关闭
######## **预期结果** 表格内容更新为接口返回数据
#### 筛选触发 Loading
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
实验列表页面已加载完成
筛选区存在至少一个可修改的筛选条件
**[tag]** e2e
###### **操作步骤** 1. 点击筛选区中的Stage下拉框
2. 从下拉选项中选择任意一个非当前选中的选项（如选择'Dryrun'）
####### **预期结果** 筛选区与表格区域同步显示loading状态
####### **操作步骤** 等待接口响应完成
######## **预期结果** 筛选区与表格区域的loading状态关闭
######## **预期结果** 表格数据刷新为符合新筛选条件（Stage为'Dryrun'）的实验列表
#### 分页触发 Loading
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
2. 点击分页器中的第2页页码
####### **预期结果** 表格区域展示loading状态
####### **操作步骤** 等待接口请求完成
######## **预期结果** 表格loading状态关闭
######## **预期结果** 表格展示第2页的实验列表数据
######## **预期结果** 分页器当前页码更新为2
###### **操作步骤** 1. 页面加载完毕
2. 点击分页器中的页大小下拉框
3. 选择页大小为20
####### **预期结果** 表格区域展示loading状态
####### **操作步骤** 等待接口请求完成
####### **预期结果** 表格loading状态关闭
####### **预期结果** 表格每页展示20条实验列表数据
####### **预期结果** 分页器页大小显示为20
####### **预期结果** 分页器页码重置为1
### 分页与排序
#### 翻页与total展示
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
1. 实验列表页面已加载完成
2. 分页器已初始化且默认展示第一页数据
3. 接口返回的total值大于当前页pageSize
**[tag]** e2e
###### **操作步骤** 1. 点击分页器中的第2页页码
####### **预期结果** 表格区域展示loading状态
####### **操作步骤** 等待接口请求完成
######## **预期结果** 分页器当前页码高亮显示为2
######## **预期结果** 分页器显示的total值与接口返回的total一致
######## **预期结果** 表格中展示的数据为第2页对应的数据
####### **操作步骤** 点击分页器中的最后一页页码
######## **预期结果** 表格区域展示loading状态
######## **操作步骤** 等待接口请求完成
######### **预期结果** 分页器当前页码高亮显示为最后一页
######### **预期结果** 分页器显示的total值与接口返回的total一致
######### **预期结果** 表格中展示的数据为最后一页对应的数据
#### 修改pageSize
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
1. 实验列表页面已加载完成
2. 表格已展示至少一页数据
3. 分页器处于可用状态
**[tag]** e2e
###### **操作步骤** 1. 点击分页器中的pageSize下拉选择框
2. 从下拉选项中选择不同于当前值的新pageSize（如从10条/页切换为20条/页）
####### **预期结果** 表格数据开始重新加载，展示loading状态
####### **操作步骤** 等待数据加载完成
######## **预期结果** 表格中展示的记录条数等于新选择的pageSize（若总数据量不足新pageSize则展示实际总条数）
######## **预期结果** 分页器上显示的当前pageSize已更新为新选择的值
######## **预期结果** 分页器的总页数根据total和新pageSize重新计算并正确展示（总页数=Math.ceil(total / newPageSize)）
#### 默认排序（按更新时间倒序）
##### **前置条件** 访问 <uri: src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
####### **预期结果** 列表数据按update_time字段降序排列，最新更新的实验项排在最前面
####### **操作步骤** 1. 点击分页器的下一页按钮
######## **预期结果** 当前页切换为第二页，列表数据仍按update_time字段降序排列
######## **操作步骤** 1. 点击分页器的上一页按钮
######### **预期结果** 当前页切换回第一页，列表数据保持按update_time字段降序排列
### 请求中止（AbortController）
#### 快速连续筛选变更
##### **前置条件** 访问 https://example.com/experiment-management
筛选区各字段（Experiment ID、name、Stage等）均可正常交互
表格数据已加载完成且分页器处于初始状态
**[tag]** e2e
###### **操作步骤** 1. 在Experiment ID输入框快速连续输入"123"→删除→输入"456"（整个过程在500ms内完成）
####### **预期结果** 网络请求中仅最后一次输入"456"的请求成功，之前输入"123"的请求被abort
####### **预期结果** 表格最终展示的数据与Experiment ID为"456"的筛选条件匹配
####### **预期结果** 表格未出现短暂展示"123"对应数据后又切换为"456"数据的闪烁现象
####### **预期结果** 分页器重置为第一页，total数值与最新筛选结果匹配
#### 快速分页切换
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
1. 实验列表页面已加载完成
2. 分页器可正常操作
3. 表格数据支持多页展示
**[tag]** e2e
###### **操作步骤** 1. 快速点击分页器中的第2页
2. 在第2页数据加载完成前，立即点击第3页
####### **预期结果** 表格最终展示第3页数据
####### **预期结果** 分页器当前页码显示为3
####### **预期结果** 网络请求中第2页的请求被abort
### 接口异常兜底
#### 接口失败回填规则
##### **前置条件** 访问 apps/release/src/expose/experiment-management
**[tag]** e2e
###### **操作步骤** 1. 等待页面完成加载
####### **预期结果** 表格展示空状态
####### **预期结果** 分页器显示total为0且仅1页
####### **预期结果** 页面无报错信息
####### **预期结果** 筛选区与表格的loading状态已关闭
#### 失败后的可恢复操作
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 等待页面加载完成
2. 观察表格区域是否展示空状态
####### **预期结果** 表格展示空状态，页面无报错
####### **操作步骤** 1. 在筛选区Experiment name输入框中输入"test"
2. 等待500ms防抖触发查询
######## **预期结果** 表格展示根据"test"筛选后的实验列表数据，分页信息同步更新
####### **操作步骤** 1. 点击分页器第2页
######## **预期结果** 表格展示第2页的实验列表数据，分页器当前页显示为2
## 筛选区（Filter）
### 字段展示与取值
#### Experiment ID 输入框
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/components/filter.tsx>
**[tag]** e2e
###### **操作步骤** 1. 在Experiment ID输入框中输入数字'12345'
2. 等待500ms防抖触发查询
####### **预期结果** 请求参数中包含experiment_id: 12345
###### **操作步骤** 1. 在Experiment ID输入框中输入非数字'abc'
2. 等待500ms防抖触发查询
####### **预期结果** 请求参数中包含experiment_id: 'abc'（按组件设计回传非数字值）
###### **操作步骤** 1. 清空Experiment ID输入框（删除所有内容）
2. 等待500ms防抖触发查询
####### **预期结果** 请求参数中experiment_id字段被移除或置空
#### Experiment name 输入框
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. 筛选区已加载完成
2. Experiment name 输入框可见且可交互
**[tag]** e2e
###### **操作步骤** 1. 在Experiment name输入框中输入"test experiment"
####### **预期结果** 500ms后触发查询，请求参数中包含"name":"test experiment"
####### **操作步骤** 1. 清空Experiment name输入框
######## **预期结果** 500ms后触发查询，请求参数中不包含"name"字段或"name"字段为空
###### **操作步骤** 1. 在Experiment name输入框中输入"  with spaces  "
####### **预期结果** 500ms后触发查询，请求参数中包含"name":"  with spaces  "
#### Stage 下拉框
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/components/filter.tsx>
1. 实验列表页面已加载完成
2. 筛选区组件已渲染完成
**[tag]** e2e
###### **操作步骤** 1. 点击Stage下拉框
####### **预期结果** 下拉选项包含AB Confirm、Dryrun、AB Test、AB Finish，与STAGE_OPTIONS常量一致
####### **操作步骤** 1. 选择下拉选项中的AB Confirm
######## **预期结果** 500ms防抖后触发列表查询，请求参数中包含stage: AB Confirm
######## **操作步骤** 1. 点击Stage下拉框
2. 选择清空选项
######### **预期结果** 500ms防抖后触发列表查询，请求参数中stage字段被移除或置空，列表刷新为不筛选Stage的结果
####### **操作步骤** 1. 点击Stage下拉框
2. 选择下拉选项中的Dryrun
######## **预期结果** 500ms防抖后触发列表查询，请求参数中包含stage: Dryrun
######## **操作步骤** 1. 点击Stage下拉框
2. 选择清空选项
######### **预期结果** 500ms防抖后触发列表查询，请求参数中stage字段被移除或置空，列表刷新为不筛选Stage的结果
####### **操作步骤** 1. 点击Stage下拉框
2. 选择下拉选项中的AB Test
######## **预期结果** 500ms防抖后触发列表查询，请求参数中包含stage: AB Test
######## **操作步骤** 1. 点击Stage下拉框
2. 选择清空选项
######### **预期结果** 500ms防抖后触发列表查询，请求参数中stage字段被移除或置空，列表刷新为不筛选Stage的结果
####### **操作步骤** 1. 点击Stage下拉框
2. 选择下拉选项中的AB Finish
######## **预期结果** 500ms防抖后触发列表查询，请求参数中包含stage: AB Finish
######## **操作步骤** 1. 点击Stage下拉框
2. 选择清空选项
######### **预期结果** 500ms防抖后触发列表查询，请求参数中stage字段被移除或置空，列表刷新为不筛选Stage的结果
#### Experiment status 下拉框
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/components/filter.tsx>
1. 实验列表页面已加载完成
2. 筛选区组件已渲染完成
**[tag]** e2e
###### **操作步骤** 1. 点击Experiment status下拉框
####### **预期结果** 下拉选项包含与ExternalExperimentStatus枚举映射一致的文案（如进行中、已结束、失败等）
###### **操作步骤** 1. 从Experiment status下拉框中选择一个选项（例如“进行中”）
####### **预期结果** 请求参数中experiment status字段传递对应后端枚举值（而非文案）
####### **操作步骤** 1. 清空Experiment status下拉框的选择
######## **预期结果** 请求参数中移除experiment status筛选条件
#### Review status 下拉框
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
2. 点击筛选区中'Review status'下拉框
####### **预期结果** 下拉选项包含'评审中'、'已通过'、'未通过'，且与ExternalExperimentReviewStatus枚举到文案的映射一致
####### **操作步骤** 1. 选择下拉选项中的'评审中'
######## **预期结果** 请求参数中'review_status'字段传递为对应'评审中'的后端枚举值
######## **操作步骤** 1. 清空'Review status'下拉框的选择
######### **预期结果** 请求参数中不再包含'review_status'字段，取消该筛选条件
####### **操作步骤** 1. 选择下拉选项中的'已通过'
######## **预期结果** 请求参数中'review_status'字段传递为对应'已通过'的后端枚举值
######## **操作步骤** 1. 清空'Review status'下拉框的选择
######### **预期结果** 请求参数中不再包含'review_status'字段，取消该筛选条件
####### **操作步骤** 1. 选择下拉选项中的'未通过'
######## **预期结果** 请求参数中'review_status'字段传递为对应'未通过'的后端枚举值
######## **操作步骤** 1. 清空'Review status'下拉框的选择
######### **预期结果** 请求参数中不再包含'review_status'字段，取消该筛选条件
#### Creator 用户选择（FormUserSelector）
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. 筛选区已加载完成
2. Creator 用户选择组件（FormUserSelector）可见且可交互
**[tag]** e2e
###### **操作步骤** 1. 点击 Creator 用户选择组件（FormUserSelector）的输入框
2. 在弹出的用户选择面板中选择单个用户
3. 等待 500ms 防抖触发
####### **预期结果** 请求参数中包含 creators 字段，值为所选单个用户的 username
####### **预期结果** 表格列表刷新为仅包含所选用户创建的实验数据
####### **预期结果** 分页器重置为第一页，total 数值与筛选结果匹配
###### **操作步骤** 1. 点击 Creator 用户选择组件（FormUserSelector）的输入框
2. 在弹出的用户选择面板中选择多个用户
3. 等待 500ms 防抖触发
####### **预期结果** 请求参数中包含 creators 字段，值为所选多个用户的 username 组成的数组
####### **预期结果** 表格列表刷新为包含任一所选用户创建的实验数据
####### **预期结果** 分页器重置为第一页，total 数值与筛选结果匹配
###### **操作步骤** 1. 点击 Creator 用户选择组件（FormUserSelector）已选择用户后的清除按钮
2. 等待 500ms 防抖触发
####### **预期结果** 请求参数中 creators 字段被移除或置空
####### **预期结果** 表格列表刷新为取消 Creator 筛选条件后的全部数据
####### **预期结果** 分页器重置为第一页，total 数值与取消筛选后的结果匹配
#### Updater 用户选择（FormUserSelector）
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
实验列表页面已加载完成
**[tag]** e2e
###### **操作步骤** 1. 点击Updater用户选择框
2. 从下拉列表中选择单个用户（如“张三”）
####### **预期结果** Updater用户选择框显示已选用户“张三”
####### **操作步骤** 等待500ms防抖时间
######## **预期结果** 发起列表查询请求，请求参数中包含operators字段且值为所选用户“张三”的唯一标识（如用户ID或username）
######## **预期结果** 表格展示筛选后的数据，仅包含更新者为“张三”的实验记录
###### **操作步骤** 1. 点击Updater用户选择框
2. 从下拉列表中选择多个用户（如“张三”和“李四”）
####### **预期结果** Updater用户选择框显示已选用户“张三”和“李四”
####### **操作步骤** 等待500ms防抖时间
######## **预期结果** 发起列表查询请求，请求参数中包含operators字段且值为所选多个用户“张三”和“李四”的唯一标识数组
######## **预期结果** 表格展示筛选后的数据，仅包含更新者为“张三”或“李四”的实验记录
###### **操作步骤** 1. 点击Updater用户选择框
2. 点击已选用户旁边的删除按钮或清空选择
####### **预期结果** Updater用户选择框为空，无已选用户
####### **操作步骤** 等待500ms防抖时间
######## **预期结果** 发起列表查询请求，请求参数中不包含operators字段或operators字段值为空
######## **预期结果** 表格展示取消Updater筛选后的完整数据列表
#### Update time 时间范围（dateTimeRange）
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
2. 点击Update time时间范围选择框
3. 选择开始时间为2024-01-01 00:00:00
4. 选择结束时间为2024-01-31 23:59:59
####### **预期结果** 500ms后触发列表查询，请求参数中包含符合IDL定义格式的起止时间字段，且时区处理正确
###### **操作步骤** 1. 页面加载完毕
2. 点击Update time时间范围选择框
3. 仅选择开始时间为2024-02-01 00:00:00
4. 不选择结束时间
####### **预期结果** 按组件约束处理仅选开始时间的情况，页面不报错且500ms后触发查询
###### **操作步骤** 1. 页面加载完毕
2. 点击Update time时间范围选择框
3. 不选择开始时间
4. 仅选择结束时间为2024-02-29 23:59:59
####### **预期结果** 按组件约束处理仅选结束时间的情况，页面不报错且500ms后触发查询
###### **操作步骤** 1. 页面加载完毕
2. 点击Update time时间范围选择框
3. 选择开始时间为2024-03-01 00:00:00
4. 选择结束时间为2024-03-31 23:59:59
5. 点击时间选择框内的清空按钮
####### **预期结果** Update time筛选条件被取消，500ms后触发查询且请求参数中不含时间范围字段，列表刷新为不筛选时间的结果
#### Only view mine 勾选框
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. 筛选区已加载完成
2. 表格数据已完成初始加载
**[tag]** e2e
###### **操作步骤** 1. 点击“Only view mine”勾选框
####### **预期结果** 勾选框状态变为勾选
####### **操作步骤** 2. 等待500ms防抖触发查询
######## **预期结果** 表格数据重新加载并展示与当前用户相关的实验列表
######## **操作步骤** 3. 点击浏览器刷新按钮
######### **预期结果** 页面重新加载后，“Only view mine”勾选框保持勾选状态
######### **操作步骤** 4. 点击“Only view mine”勾选框取消勾选
########## **预期结果** 勾选框状态变为未勾选
########## **操作步骤** 5. 等待500ms防抖触发查询
########### **预期结果** 表格数据重新加载并展示全部实验列表（非仅当前用户相关）
########### **操作步骤** 6. 点击浏览器刷新按钮
############ **预期结果** 页面重新加载后，“Only view mine”勾选框保持未勾选状态
### Only view mine 联动逻辑
#### creators/operators均为空时的自动填充
##### **前置条件** 访问 apps/release/src/expose/experiment-management
1. 筛选区中Creator字段未选择任何用户
2. 筛选区中Updater字段未选择任何用户
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
2. 勾选Only view mine复选框
####### **预期结果** 请求参数中包含creators字段，值为当前登录用户名
####### **预期结果** 请求参数中包含operators字段，值为当前登录用户名
####### **预期结果** 表格数据刷新为仅与当前用户相关的实验数据
####### **预期结果** 分页器total值更新为与当前用户相关的实验总数
#### creators已设置时的行为
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. 已手动选择Creator筛选条件
2. Updater筛选条件为空
**[tag]** e2e
###### **操作步骤** 1. 勾选“Only view mine”复选框
####### **预期结果** 500ms后触发列表查询
####### **预期结果** 请求参数中creators字段保持手动选择的值不变
####### **预期结果** 请求参数中operators字段自动填充当前登录用户名
####### **预期结果** 分页重置为第一页
####### **预期结果** 表格展示按合并后的creators和operators参数筛选的结果
#### operators已设置时的行为
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. 已通过Updater用户选择组件手动选择至少一个用户
2. Creator用户选择组件未选择任何用户
**[tag]** e2e
###### **操作步骤** 1. 勾选Only view mine复选框
####### **预期结果** 触发500ms防抖后发起列表查询
####### **预期结果** 请求参数中operators字段保持手动选择的用户值不变
####### **预期结果** 请求参数中creators字段自动填充当前登录用户的username
####### **预期结果** 分页重置为第一页
#### 取消勾选后的参数恢复
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. Only view mine 处于勾选状态
2. 已通过自动填充将当前登录用户名注入到请求参数 creators 和/或 operators 中
**[tag]** e2e
###### **操作步骤** 1. 点击 Only view mine 勾选框取消勾选
####### **预期结果** 筛选区触发 500ms 防抖查询
####### **操作步骤** 2. 等待 500ms 防抖结束后观察请求参数
######## **预期结果** 请求参数中 creators 和 operators 字段不再包含当前登录用户名（若之前仅为自动填充值）
######## **预期结果** 分页器重置为第一页
######## **预期结果** 表格数据刷新为取消 Only view mine 后的未筛选状态或用户手动设置的筛选值对应结果
### 500ms 防抖触发
#### 单字段连续输入
##### **前置条件** 访问 https://example.com/experiment-management
筛选区已加载完成
**[tag]** e2e
###### **操作步骤** 1. 在Experiment name输入框中快速连续输入"test123"（总耗时不超过500ms）
####### **预期结果** 500ms内未发起多次请求，仅在停止输入500ms后发起一次查询
####### **预期结果** 请求参数中name字段值为最终输入值"test123"
####### **操作步骤** 2. 在Experiment ID输入框中快速连续输入"456"（总耗时不超过500ms）
######## **预期结果** 500ms内未发起多次请求，仅在停止输入500ms后发起一次查询
######## **预期结果** 请求参数中experiment_id字段值为最终输入值"456"
#### 多字段快速连续修改
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
实验列表页面已加载完成
筛选区各字段处于初始状态（未输入/未选择）
**[tag]** e2e
###### **操作步骤** 1. 在Experiment ID输入框中输入"123"
2. 在Stage下拉框中选择"AB Test"
3. 在Experiment status下拉框中选择"进行中"
4. 勾选Only view mine复选框
####### **预期结果** 在500ms内仅触发一次列表查询请求
####### **预期结果** 请求参数包含experiment_id: 123、stage: AB Test、status: 进行中对应的后端枚举值、creators: 当前登录用户名、operators: 当前登录用户名
####### **预期结果** 表格数据更新为符合所有筛选条件的实验列表
####### **预期结果** 分页器重置为第一页，且total值与筛选结果匹配
### 筛选触发的分页重置
#### 变更筛选条件后的分页状态
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. 实验列表页面已加载完成
2. 当前分页处于非第一页
3. 表格已展示非第一页的实验数据
**[tag]** e2e
###### **操作步骤** 1. 在筛选区修改任一筛选条件（如在Experiment name输入框中输入测试关键词）
####### **预期结果** 分页器当前页重置为1
####### **操作步骤** 2. 等待500ms防抖结束
######## **预期结果** 发起新的列表查询请求，请求参数中分页参数currentPage为1
######## **预期结果** 表格展示第一页的实验数据
######## **预期结果** 分页器当前页显示为1
## 表格展示（Table Columns）
### 基础字段列
#### Experiment ID 列
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/components/list.tsx>
1. 实验列表页面已加载完成
2. 表格组件已初始化并成功请求到数据
**[tag]** e2e
###### **操作步骤** 1. 定位表格中的Experiment ID列
####### **预期结果** 列标题显示为'Experiment ID'
####### **操作步骤** 1. 查看表格中所有行的Experiment ID值
######## **预期结果** 每个Experiment ID值完整展示，无截断或省略
######## **预期结果** 展示的Experiment ID值与接口返回的experiment_id字段一致
####### **操作步骤** 1. 筛选包含experiment_id为空值的实验数据
######## **预期结果** 对应行的Experiment ID列展示空值，符合组件默认空值展示行为
######## **预期结果** 表格整体渲染正常，无布局错乱或报错
####### **操作步骤** 1. 筛选包含experiment_id为0的实验数据
######## **预期结果** 对应行的Experiment ID列显示'0'
######## **预期结果** 表格整体渲染正常，无布局错乱或报错
####### **操作步骤** 1. 筛选包含experiment_id为超大数（如999999999999999999）的实验数据
######## **预期结果** 对应行的Experiment ID列完整展示该超大数，无截断或科学计数法显示
######## **预期结果** 表格整体渲染正常，无布局错乱或报错
#### Experiment name 列
##### **前置条件** 访问 <uri: /apps/release/src/expose/experiment-management/components/list.tsx>
1. 实验列表页面已加载完成
2. 表格数据已成功渲染
**[tag]** e2e
###### **操作步骤** 1. 查看表格中所有实验的Experiment name列内容
####### **预期结果** 所有实验的name文本完整展示，无截断或省略
###### **操作步骤** 1. 定位到name字段包含超长文本的实验行
####### **预期结果** 超长文本按表格默认策略处理（省略或换行）
####### **预期结果** 超长文本所在单元格及整行布局未被破坏，不影响其他列内容展示
### Stage 列（TicketStatusTag）
#### PipelineStage 兼容映射
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
1. 后端接口返回的ExperimentItem数据中包含Stage字段，且值为`AB Confirm`、`Dryrun`、`AB Test`或`AB Finish`
2. 实验列表页面已加载完成，表格组件成功渲染
**[tag]** e2e
###### **操作步骤** 1. 查看表格中Stage列的所有标签元素
####### **预期结果** Stage列中所有标签均使用TicketStatusTag组件渲染
####### **预期结果** 后端返回Stage为`AB Confirm`的行，对应TicketStatusTag的stage属性值与组件要求兼容
####### **预期结果** 后端返回Stage为`Dryrun`的行，对应TicketStatusTag的stage属性值与组件要求兼容
####### **预期结果** 后端返回Stage为`AB Test`的行，对应TicketStatusTag的stage属性值与组件要求兼容
####### **预期结果** 后端返回Stage为`AB Finish`的行，对应TicketStatusTag的stage属性值与组件要求兼容
####### **预期结果** 所有Stage标签的样式（颜色、形状、文字）与release-management页面的TicketStatusTag样式一致
#### 异常Stage兜底
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/components/list.tsx>
1. 后端接口返回的ExperimentItem中包含未识别的Stage值
2. 实验列表页面已加载完成
**[tag]** e2e
###### **操作步骤** 1. 定位表格中Stage列存在未识别Stage值的行
####### **预期结果** 页面不报错，Stage列渲染正常
####### **预期结果** 未识别Stage值的单元格采用与实现一致的兜底展示策略（空/默认标签/原值）
### Status 列（运行状态文案）
#### 枚举到文案映射
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/components/list.tsx>
1. 表格已加载完成
2. 后端返回包含不同`ExternalExperimentStatus`枚举值的实验数据
3. `constants.ts`中已配置`ExternalExperimentStatus`到文案的映射关系
**[tag]** e2e
###### **操作步骤** 1. 定位表格中的Status列
####### **预期结果** Status列中每个单元格的展示文案与`constants.ts`中`ExternalExperimentStatus`映射配置一致
####### **操作步骤** 1. 遍历表格中所有行的Status列值
######## **预期结果** 每一行Status列展示的文案与该行对应`ExternalExperimentStatus`枚举值的映射结果完全匹配
#### 异常Status兜底
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/components/list.tsx>
1. 后端接口返回包含未识别的ExternalExperimentStatus枚举值的实验数据
2. 列表页已加载完成
**[tag]** e2e
###### **操作步骤** 1. 观察表格中Status列的展示内容
####### **预期结果** 未识别status值的行在Status列展示兜底内容（如空字符串、默认文案或原值）
####### **预期结果** Status列展示不报错，无控制台错误信息
####### **预期结果** 其他列（Experiment ID、Experiment name、Stage等）正常渲染，不受异常Status值影响
####### **预期结果** 表格整体布局未被破坏，行高一致，无错位或内容溢出
### Creator & create time 列
#### 用户信息展示（UserCard）
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
1. 实验列表页面已加载完成
2. 表格数据已渲染
**[tag]** e2e
###### **操作步骤** 1. 观察表格中Creator & create time列的用户信息展示
####### **预期结果** 存在creator字段的列表项使用UserCard组件展示用户信息
####### **预期结果** creator字段为空的列表项，UserCard组件渲染正常不崩溃
####### **预期结果** creator字段缺失的列表项，UserCard组件展示符合默认占位策略
#### 创建时间展示（formatTZ）
##### **前置条件** 访问 <uri: /src/expose/experiment-management/components/list.tsx>
1. 实验列表页面已加载完成
2. 表格数据已成功渲染
**[tag]** e2e
###### **操作步骤** 1. 定位表格中Creator & create time列的时间展示区域
####### **预期结果** 时间格式为YYYY-MM-DD HH:mm:ss
###### **操作步骤** 1. 查找addTime字段为空值的表格行
####### **预期结果** 时间展示区域显示兜底内容（如“-”或空字符串）
###### **操作步骤** 1. 查找addTime字段为非法值（如字符串“invalid”或非时间戳数字）的表格行
####### **预期结果** 时间展示区域显示兜底内容（如“-”或空字符串）
### Updater & update time 列
#### 用户信息展示（UserCard）
##### **前置条件** 访问 https://example.com/experiment-management
1. 实验列表页面已加载完成
2. 表格数据已成功渲染
**[tag]** e2e
###### **操作步骤** 1. 遍历表格所有数据行
####### **预期结果** 所有行的Updater & update time列中operator字段均使用UserCard组件展示
####### **操作步骤** 1. 定位operator字段非空的行
######## **预期结果** UserCard组件正确展示operator的用户信息
####### **操作步骤** 1. 定位operator字段缺失的行
######## **预期结果** UserCard组件渲染正常，展示预设的一致占位内容
####### **操作步骤** 1. 定位operator字段为空值的行
######## **预期结果** UserCard组件渲染正常，展示预设的一致占位内容
#### 更新时间展示（formatTZ）
##### **前置条件** 访问 https://example.com/experiment-management
表格已加载完成且展示实验数据
**[tag]** e2e
###### **操作步骤** 1. 查看表格中Updater & update time列的更新时间展示
####### **预期结果** 所有非空updateTime均格式化为'YYYY-MM-DD HH:mm:ss'格式
####### **预期结果** updateTime为空或非法值时，展示兜底内容（如'-'或空字符串）且不报错
### Action 列
#### 右侧固定与按钮样式
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
1. 实验列表页面已加载完成
2. 表格中存在至少一行实验数据
**[tag]** e2e
###### **操作步骤** 1. 拖动浏览器窗口宽度至小于表格总宽度，使表格出现横向滚动条
2. 向右拖动横向滚动条至表格最右侧
####### **预期结果** Action列始终固定在表格右侧可见区域，不随滚动条移动而隐藏
####### **操作步骤** 1. 观察表格中Action列的“Experiment detail”按钮样式
2. 观察表格中Action列的“Operation record”按钮样式（若存在）
######## **预期结果** 所有按钮主题为borderless，无背景色和边框，仅文字和图标展示
######## **预期结果** 按钮样式（字体大小、颜色、间距）与release-management页面的Action列按钮保持一致
#### Experiment detail 跳转
##### **前置条件** 访问 https://example.com/experiment-management
实验列表页面已加载完成
表格中存在至少一条实验数据
**[tag]** e2e
###### **操作步骤** 1. 找到表格中任意一行数据
2. 点击该行Action列中的“Experiment detail”按钮
####### **预期结果** 浏览器新窗口打开实验详情页路由
####### **预期结果** 新窗口URL中包含当前行实验数据的experiment_id参数
####### **预期结果** 若当前行数据包含review_id字段，新窗口URL中包含review_id参数
####### **预期结果** 若当前行数据包含flight_id字段，新窗口URL中包含flight_id参数
####### **预期结果** URL中不包含undefined或null字样
#### Operation record 按钮显示策略
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/list.tsx
1. 实验列表页面已加载完成
2. 表格数据已成功渲染
**[tag]** e2e
###### **操作步骤** 1. 检查表格Action列中是否存在Operation record按钮
####### **预期结果** Action列中不展示Operation record按钮，且Action列布局正常无异常
## 跳转与 URL 生成（utils/url.ts）
### getExperimentDetailUrl
#### 必填字段拼接
##### **前置条件** 访问 https://example.com/experiment-management
1. 实验列表页面已加载完成
2. 表格中存在至少一条包含有效experiment_id的实验记录
**[tag]** e2e
###### **操作步骤** 1. 找到表格中任意一条实验记录
2. 点击该记录Action列的“Experiment detail”按钮
####### **预期结果** 新窗口打开的URL中包含该记录的experiment_id参数
####### **操作步骤** 1. 关闭详情页窗口
2. 选择表格中另一条不同的实验记录
3. 点击该记录Action列的“Experiment detail”按钮
######## **预期结果** 新窗口打开的URL中包含第二条记录的experiment_id参数，且与第一条记录生成的URL不同
#### 可选字段拼接
##### **前置条件** 访问 https://example.com/experiment-management
1. 实验列表页已加载完成
2. 表格中存在包含`review_id`或`flight_id`字段的实验列表项
**[tag]** e2e
###### **操作步骤** 1. 找到表格中包含review_id字段的实验列表项
2. 点击该列表项Action列的Experiment detail按钮
####### **预期结果** 新窗口打开的URL中包含review_id参数及其对应值，格式符合约定规则（如?review_id=xxx）
###### **操作步骤** 1. 找到表格中包含flight_id字段的实验列表项
2. 点击该列表项Action列的Experiment detail按钮
####### **预期结果** 新窗口打开的URL中包含flight_id参数及其对应值，格式符合约定规则（如?flight_id=xxx）
###### **操作步骤** 1. 找到表格中同时包含review_id和flight_id字段的实验列表项
2. 点击该列表项Action列的Experiment detail按钮
####### **预期结果** 新窗口打开的URL中同时包含review_id和flight_id参数及其对应值，参数间用&连接（如?review_id=xxx&flight_id=yyy）
###### **操作步骤** 1. 找到表格中缺失review_id字段的实验列表项
2. 点击该列表项Action列的Experiment detail按钮
####### **预期结果** 新窗口打开的URL中不包含review_id参数，且不存在undefined或null字样
###### **操作步骤** 1. 找到表格中缺失flight_id字段的实验列表项
2. 点击该列表项Action列的Experiment detail按钮
####### **预期结果** 新窗口打开的URL中不包含flight_id参数，且不存在undefined或null字样
#### 异常输入兜底
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/utils/url.ts>
1. 存在包含异常record数据的实验列表项（如缺少experiment_id或字段类型非预期）
2. 实验列表页面已加载完成且表格中展示包含异常record的列表项
**[tag]** e2e
###### **操作步骤** 1. 点击表格中包含异常record的列表项的“Experiment detail”按钮
####### **预期结果** 函数返回值符合兜底策略（如基础路径或空字符串）
####### **预期结果** 点击跳转不会导致页面崩溃
## 接口调用策略
### 优先 SearchExperiment
#### 正常调用与类型回填
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
####### **预期结果** 调用 httpService.SearchExperiment 接口
####### **预期结果** 请求参数包含 orderBy: 'update_time DESC' 和 tenantId
####### **预期结果** 请求参数符合 SearchExperimentReq 类型定义
####### **预期结果** 返回数组子项正确回填到 list 状态
####### **预期结果** 表格成功渲染返回的实验列表数据
### 占位 SearchReleaseTicket（SearchExperiment 不可用）
#### 特殊筛选条件注入
##### **前置条件** 访问 https://example.com/experiment-management
SearchExperiment 接口不可用
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
####### **预期结果** 调用 httpService.SearchReleaseTicket 接口时，请求参数中包含约定的特殊筛选条件（如 entityType 或 changeType 的特定值）
####### **预期结果** 表格中展示的实验数据仅为通过特殊筛选条件返回的实验相关数据
####### **预期结果** 表格各列（Experiment ID、Experiment name、Stage、Status、Creator & create time、Updater & update time、Action）均正常展示，无字段缺失或渲染异常
#### 切换策略一致性
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management>
**[tag]** e2e
###### **操作步骤** 1. 页面加载完毕
2. 观察表格初始加载状态
####### **预期结果** 表格展示实验列表数据，无字段缺失导致的渲染异常
####### **操作步骤** 1. 点击分页器第2页
######## **预期结果** 表格加载第2页数据，分页器当前页显示为2
####### **操作步骤** 1. 在Experiment name输入框中输入'测试实验'
2. 等待500ms
######## **预期结果** 表格展示名称包含'测试实验'的筛选结果，分页重置为第1页
####### **操作步骤** 1. 快速连续修改Stage下拉框选项3次
######## **预期结果** 仅最后一次选择的Stage条件生效，表格展示对应筛选结果
####### **操作步骤** 1. 模拟接口返回500错误
######## **预期结果** 表格展示空状态，list为空数组且total为0，页面不崩溃
## 常量与枚举映射（constants.ts）
### FILTER_FIELD 字段管理
#### 字段名一致性
##### **前置条件** 访问 https://example.com/experiment-management
**[tag]** e2e
###### **操作步骤** 1. 打开浏览器开发者工具
2. 切换至Network选项卡
3. 清空当前网络请求记录
4. 在筛选区修改Experiment ID输入框的值
5. 等待500ms防抖触发查询
####### **预期结果** Network中最新请求的query参数包含experiment_id字段，且值与输入一致
####### **操作步骤** 1. 清空Experiment ID输入框
2. 在Experiment name输入框中输入测试文本
3. 等待500ms防抖触发查询
######## **预期结果** Network中最新请求的query参数包含name字段，且值与输入的测试文本一致
######## **操作步骤** 1. 清空Experiment name输入框
2. 在Stage下拉框中选择任意选项
3. 等待500ms防抖触发查询
######### **预期结果** Network中最新请求的query参数包含stage字段，且值与选择的Stage选项对应
######### **操作步骤** 1. 重置Stage下拉框为未选择状态
2. 在Experiment status下拉框中选择任意选项
3. 等待500ms防抖触发查询
########## **预期结果** Network中最新请求的query参数包含status字段，且值与选择的Experiment status选项对应
########## **操作步骤** 1. 重置Experiment status下拉框为未选择状态
2. 在Review status下拉框中选择任意选项
3. 等待500ms防抖触发查询
########### **预期结果** Network中最新请求的query参数包含review_status字段，且值与选择的Review status选项对应
########### **操作步骤** 1. 重置Review status下拉框为未选择状态
2. 在Creator用户选择器中选择任意用户
3. 等待500ms防抖触发查询
############ **预期结果** Network中最新请求的query参数包含creators字段，且值与选择的Creator用户对应
############ **操作步骤** 1. 清空Creator用户选择器
2. 在Updater用户选择器中选择任意用户
3. 等待500ms防抖触发查询
############# **预期结果** Network中最新请求的query参数包含operators字段，且值与选择的Updater用户对应
############# **操作步骤** 1. 清空Updater用户选择器
2. 在Update time日期选择器中选择任意时间范围
3. 等待500ms防抖触发查询
############## **预期结果** Network中最新请求的query参数包含updateTime相关的起止时间字段，且值与选择的时间范围对应
############## **操作步骤** 1. 清空Update time日期选择器
2. 勾选Only view mine复选框
3. 等待500ms防抖触发查询
############### **预期结果** Network中最新请求的query参数包含creators和operators字段，且值为当前登录用户的username
### 下拉选项常量
#### STAGE_OPTIONS
##### **前置条件** 访问 https://example.com/experiment-management
筛选区已加载完成
**[tag]** e2e
###### **操作步骤** 1. 点击筛选区中的Stage下拉框
####### **预期结果** 下拉选项包含AB Confirm、Dryrun、AB Test、AB Finish四个选项
####### **操作步骤** 1. 选择下拉选项中的AB Confirm
######## **预期结果** 请求参数中stage字段的值为AB Confirm对应的后端枚举值
######## **预期结果** 下拉框显示的选中文案为AB Confirm
####### **操作步骤** 1. 选择下拉选项中的Dryrun
######## **预期结果** 请求参数中stage字段的值为Dryrun对应的后端枚举值
######## **预期结果** 下拉框显示的选中文案为Dryrun
####### **操作步骤** 1. 选择下拉选项中的AB Test
######## **预期结果** 请求参数中stage字段的值为AB Test对应的后端枚举值
######## **预期结果** 下拉框显示的选中文案为AB Test
####### **操作步骤** 1. 选择下拉选项中的AB Finish
######## **预期结果** 请求参数中stage字段的值为AB Finish对应的后端枚举值
######## **预期结果** 下拉框显示的选中文案为AB Finish
#### EXPERIMENT_RUN_STATUS_OPTIONS
##### **前置条件** 访问 apps/release/src/expose/experiment-management/components/filter.tsx
1. 实验列表页面已加载完成
2. 筛选区的Experiment status下拉框可见
**[tag]** e2e
###### **操作步骤** 1. 点击Experiment status下拉框
####### **预期结果** 下拉选项包含需求所列典型状态（进行中、已结束、失败等）
####### **操作步骤** 2. 查看下拉选项的value值
######## **预期结果** 每个选项的value为对应的后端枚举值
####### **操作步骤** 3. 查看下拉选项的label值
######## **预期结果** 每个选项的label为中文文案
####### **操作步骤** 4. 选择下拉选项中的任意一个状态
######## **预期结果** 表格Status列展示的内容与所选筛选状态的含义一致
#### REVIEW_STATUS_OPTIONS
##### **前置条件** 访问 <uri: src/expose/experiment-management/components/filter.tsx>
1. 筛选区组件已加载完成
2. Review status 下拉框可见且可交互
**[tag]** e2e
###### **操作步骤** 1. 点击 Review status 下拉框
2. 查看下拉选项列表
####### **预期结果** 下拉选项包含与 ExternalExperimentReviewStatus 枚举映射一致的文案（如“评审中”、“已通过”、“未通过”等）
####### **操作步骤** 1. 选择下拉列表中的“评审中”选项
######## **预期结果** 500ms 防抖后触发列表查询，请求参数中 review_status 字段值为对应后端枚举值
######## **预期结果** 表格列表展示仅包含评审状态为“评审中”的实验数据
######## **操作步骤** 1. 点击 Review status 下拉框
2. 选择“已通过”选项
######### **预期结果** 500ms 防抖后触发列表查询，请求参数中 review_status 字段值更新为“已通过”对应的后端枚举值
######### **预期结果** 表格列表展示仅包含评审状态为“已通过”的实验数据
######### **操作步骤** 1. 点击 Review status 下拉框
2. 选择“未通过”选项
########## **预期结果** 500ms 防抖后触发列表查询，请求参数中 review_status 字段值更新为“未通过”对应的后端枚举值
########## **预期结果** 表格列表展示仅包含评审状态为“未通过”的实验数据
########## **操作步骤** 1. 点击 Review status 下拉框
2. 选择清空选项
########### **预期结果** 500ms 防抖后触发列表查询，请求参数中 review_status 字段被移除或置空
########### **预期结果** 表格列表展示恢复为不筛选评审状态的实验数据
### 枚举映射能力
#### ExternalExperimentStatus 映射
##### **前置条件** 访问 <uri: apps/release/src/expose/experiment-management/constants.ts>
**[tag]** e2e
###### **操作步骤** 1. 查找文件中定义的ExternalExperimentStatus枚举映射函数或对象
####### **预期结果** 存在将ExternalExperimentStatus枚举值映射为中文文案的映射函数或对象
###### **操作步骤** 1. 检查映射对已知枚举值（如进行中、已结束、失败等）的返回结果
####### **预期结果** 已知枚举值均返回稳定且符合需求的中文文案
###### **操作步骤** 1. 模拟传入未识别的ExternalExperimentStatus枚举值到映射函数或对象
####### **预期结果** 对未知枚举值有明确的兜底返回（如空字符串、'未知状态'或原值）
#### ExternalExperimentReviewStatus 映射
##### **前置条件** 访问 https://example.com/experiment-management
1. 实验列表页面已加载完成
2. 表格中存在包含已知和未知ExternalExperimentReviewStatus枚举值的实验数据
**[tag]** e2e
###### **操作步骤** 1. 定位表格中所有实验数据的Review status列
####### **预期结果** 已知ExternalExperimentReviewStatus枚举值对应的表格单元格展示稳定中文文案，与constants中配置的映射结果一致
####### **预期结果** 未知ExternalExperimentReviewStatus枚举值对应的表格单元格展示一致的兜底文案，且不影响其他列渲染
#### PipelineStage 映射到 TicketStatusTag 入参
##### **前置条件** 访问 https://example.com/experiment-management
1. 实验列表页面已加载完成
2. 表格组件已初始化
**[tag]** e2e
###### **操作步骤** 1. 查看表格中所有实验项的Stage列标签展示状态
####### **预期结果** 所有已知PipelineStage值（AB Confirm/Dryrun/AB Test/AB Finish）对应的Stage列标签均使用TicketStatusTag组件正确渲染，样式与release-management页面一致
####### **预期结果** 若存在映射表缺失的Stage值，对应列展示兜底内容（空/默认标签/原值）且页面无报错