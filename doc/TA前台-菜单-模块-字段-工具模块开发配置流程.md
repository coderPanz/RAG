# TA前台-菜单-模块-字段-工具模块开发配置流程

教师工作台是一个 Vue 3 + Vite + TSX 项目，权限体系、模块配置、字段服务和批量工具均通过 `getUserMenuPerm` 接口统一驱动。理解这条主线是高效接入各类功能的前提。

## 核心接口：getUserMenuPerm

`/haichuan/api/getUserMenuPerm` 是全局权限的唯一入口，返回的 `detail_menus` 同时承载了：
- 菜单路由权限（有 `url` 字段的节点）
- 模块配置（`url` 为空串的 child_menu 节点，包含 sop_ids）
- 批量工具列表（`menu_info.batch_tool` / `single_tool`）

---

## 一、新增菜单

### 实现原理

路由分两类：
- `homeRouter`（`src/router/index.ts`）：需要权限校验的页面
- `routes`：系统级通用路由（404、redirect 等），无需权限

前端启动后通过 `src/hooks/auth/index.ts` 中的 `menuRouter` 注册支持的页面路由，再用 `getRoutesAuth` 与后端返回的权限列表做交叉过滤，动态注册最终路由树。

关键函数位置：
- `src/store/common.ts` → `getMenuList()`：拉取权限接口并缓存
- `src/hooks/auth/index.ts` → `depthTraverse()`、`dealMenuAuthority()`、`getRoutesAuth()`

### 接入步骤

1. 确定路由地址和中文名称
2. 在 `src/router/index.ts` 的 `homeRouter` 中添加路由配置（需权限）或 `routes` 中添加（不需权限）
3. 提供以下 SQL 给后端执行，完成后端路由注册：

```sql
INSERT INTO `hc_config`.`xwx_config_url`
  (`url_path`, `name`, `status`, `system_id`, `system_type`, `create_time`, `update_time`)
VALUES
  ('/your-page-path', '页面中文名称', 0, 1, 1, NOW(), NOW());
```

4. 在 TA 配置后台系统中，将新路由加入对应角色的权限包
5. 确认前台用户登录角色包含该权限包，重新登录验证

---

## 二、模块配置（SOP）

### 实现原理

`getUserMenuPerm` 返回的 `child_menu` 中，`url` 为空串的节点即为模块（而非菜单）。模块通过 `menu_info` 携带：
- `sop_ids`：通用 SOP 列表
- `sop_ids_long_class`：长期班 SOP
- `sop_ids_short_class`：短期班 SOP

关键代码位置：
- `src/store/common.ts` → `getMenuList()`：权限信息缓存至 Auth store
- `src/pages/newMyClass/index.tsx`：从 `store.allAuth` 读取对应菜单的 `menu_info`，组装 SOP ids 注入模块渲染组件

课程类型切换逻辑示例：
```ts
const currentSopIds = computed(() =>
  newCourseInfo.class_type === 1
    ? props.sopInfo.long_class_sop_ids
    : props.sopInfo.short_class_sop_ids
);
```

### 接入步骤

1. 在测试环境创建 SOP（分班级类型或讲次类型）
2. 在 SOP 中配置字段、批量/单体工具、学员筛选条件
3. 将 SOP 关联到对应角色权限包（长期/短期班）
4. 验证 `getUserMenuPerm` 接口中可以看到该 SOP id
5. 切换到对应模块后，`getOrder`、`getStudentInfo`、`performance` 等接口会自动按 `mod_id` 拉取数据

---

## 三、新增字段

### 实现原理

字段展示基于字段服务（FieldService）驱动，流程如下：

1. `src/components/tableCap/utils/tableColumn.ts`：并行调用 `getHeadOrder` + `getAppSetting`，拉取字段配置
2. `headDiff()`：对表头做 diff 合并，处理主键 fixed 字段
3. `src/pages/myClass/components/Students.tsx` → `getTableData()`：按 module 拉取 datasource 数据
4. `RowCom`、`HeaderCom`：决定通用渲染还是自定义渲染器

### 扩展入口

| 需求 | 入口位置 |
|------|---------|
| 新增字段筛选规则 | `HeaderCom` → `filterFnMap` |
| 新增搜索规则 | `searchRule` 组件 |
| 字段排序规则 | `TableCap/utils` → `sorterFn` |
| 字段自定义展示 | `RowCom` → `specialRow` 注册渲染函数 |
| 通用交互渲染 | `RowCom` → `operateMap` |
| 样式类型渲染 | `RowCom` → `showRowMap` |
| 特殊字段导出转换 | `BatchOperateMap` 中配置导出逻辑 |

### 接入步骤

1. 与产品确认字段功能、筛选规则、导出规则（参考《TA字段服务配置梳理》）
2. 由后端通过字段服务平台创建字段
   - 字段服务能覆盖的能力直接创建
   - 不支持的能力需先新增字段类型，后端扩展平台配置
3. 后端创建完毕后，在配置后台将字段添加至角色权限包
4. 在 `getOrder` 和表格数据接口中验证字段出现
5. 按需扩展 `HeaderCom`、`RowCom`、`BatchOperateMap`

---

## 四、配置批量工具

### 实现原理

批量工具同样来自 `getUserMenuPerm`，存于对应模块的 `menu_info.batch_tool`（批量）/ `single_tool`（单体）。

关键链路：
- `src/store/common.ts` → `getTools(model, type)`：按模块和工具类型取工具列表
- `src/router/index.ts` → `router.beforeEach`：路由切换时调用 `setCurAuth` 更新当前页面权限
- `src/components/operationTable/index.tsx` → `batchMap`：所有批量工具的注册中心
- `batchOperate()`：执行时从 `batchMap` 查找配置，通过校验后执行 `callback`

`batchMap` 中每个工具可配置的拦截行为：
- `is_students`：是否校验已选学生
- `check_app_label`：双端上课校验
- `custom_verification`：自定义校验器
- `is_wechat`：是否青鸟在线

### 接入步骤

1. 确认批量工具中文名称和 `action_name`
2. 在配置后台新增批量工具
3. 将批量工具关联到对应权限包的模块下
4. 验证 `getUserMenuPerm` 的对应模块中可以看到该工具
5. 在 `src/components/operationTable/index.tsx` 的 `batchMap` 中以 `action_name` 为键注册 `callback` 和校验逻辑

---

## 项目信息速查

| 项目 | 值 |
|------|---|
| 线上地址 | https://teacherdesk.wen-su.com/teacherdesktest |
| 测试地址 | https://teacherdesk-test.wen-su.com/teacherdesktest |
| 仓库 | https://codeup.aliyun.com/6528ab78940b4e1cb0ce7abb/k9-fe/teacher-desk |
| 主分支 | `yk_split` |
| 测试分支 | `test` |
| Node 版本 | v20.11.0 |
| 启动命令 | `npm run dev`（端口 4000） |

### 本地开发鉴权

1. 登录测试环境，取 localStorage 中的 `userInfo` 和 Cookie 中的 `user_token_test`
2. 本地 localStorage 设置 `userInfo` 和 `DEV_TOKEN`（值为 `user_token_test`）
3. 刷新页面即可


# 参考来源
知音楼文档：
- [TWS 开发指南](https://yach-doc-shimo.zhiyinlou.com/docs/5xkGMLOYBKs9am3X)
- [《TWS 前台交接文档》](https://yach-doc-shimo.zhiyinlou.com/docs/gO3oxDREJ6umW5qD)
- [《用户、角色、短信、群发企微开发分享-tws》](https://yach-doc-shimo.zhiyinlou.com/docs/RKAWVw2gv0hvWDk8)
