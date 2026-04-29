# TA-配置后台项目技术总览

## 1. 环境、仓库和分支

| 项目 | 内容 |
| --- | --- |
| 线上地址 | https://teacherdesk.wen-su.com/admin/ |
| 测试地址 | https://teacherdesk-test.wen-su.com/admin/ |
| 仓库 | https://codeup.aliyun.com/6528ab78940b4e1cb0ce7abb/k9-fe/teacher-desk-admin |
| 主分支 | `yk_split` |

## 2. 技术栈和依赖包

### 2.1 前端框架

- React：v18.x
- Umi：v4.x，基于 `@umijs/max` 的企业级应用框架，提供路由、构建、状态管理等一体化解决方案。

### 2.2 UI 框架

- Ant Design：v4.24.1
- `@ant-design/pro-components`：v2.0.1，ProComponents 高级组件。

### 2.3 状态管理

- Zustand：v4.3.3，轻量级状态管理库。

### 2.4 表单解决方案

- Formily：v2.2.10

### 2.5 语言与类型

- TypeScript：v4.1.2，静态类型检查。

### 2.6 关键依赖包

#### 网络请求

- axios：v1.3.1
- qs：v6.12.1，查询字符串解析。

#### 工具库

- ahooks：v3.7.8，React Hooks 工具库。
- lodash：v4.17.21，JavaScript 工具库。
- dayjs：v1.11.11，日期处理库。
- moment：v2.29.4，日期处理库，兼容旧代码。
- clsx：v2.1.1，CSS 类名处理工具。

### 2.7 开发工具链

#### 包管理工具

- pnpm：使用 pnpm 进行包管理。

#### 代码规范

- ESLint：v8.34.0，代码检查工具。
- `@typescript-eslint/eslint-plugin`
- `eslint-plugin-react`
- `eslint-plugin-import`
- `eslint-plugin-prettier`
- `eslint-plugin-unused-imports`
- Prettier：v2.7.1，代码格式化工具。
- `prettier-plugin-organize-imports`：导入排序。
- `prettier-plugin-packagejson`：`package.json` 格式化。

#### Git 工作流

- Husky：v8.0.1，Git Hooks 管理。
- Lint-staged：v13.0.3，暂存文件代码检查。
- Commitlint：v17.4.4，commit 信息规范检查。
- Commitizen：v4.2.5，交互式 commit 工具，建议使用 `git cz` 代替 `git commit`。
- cz-git：v1.5.0，commitizen 适配器。

#### 开发辅助

- mockjs：v1.1.0，数据模拟。
- code-inspector-plugin：v0.14.2，代码定位工具。
- cross-env：v7.0.3，跨平台环境变量设置。

## 3. 启动流程

### 3.1 Node 版本

```bash
v18+
```

### 3.2 安装依赖

```bash
pnpm install
```

### 3.3 启动项目

```bash
pnpm run dev
```

dev 访问地址：

```text
http://localhost:8000/?hc_config_token=hc_config_user_7dc59e66ca804a51883a7459595ec9011770878796
```

`hc_config_token` 参数登录成功后能看到。

### 3.4 构建命令

```bash
npm run build                  # 生产环境构建
npm run build:dev              # 开发环境构建
npm run build:newtest          # 测试环境构建
```

## 4. 整体架构和核心模块介绍

### 4.1 项目结构

```text
teacher-desk-admin/
├── src/                      # 源代码目录
│   ├── apis/                 # API接口定义
│   ├── assets/               # 静态资源（图片、图标）
│   ├── components/           # 公共组件
│   ├── constants/            # 常量定义
│   ├── hooks/                # 自定义Hooks
│   ├── pages/                # 页面组件
│   ├── routes/               # 路由配置
│   ├── store/                # 状态管理
│   ├── type/                 # 类型定义
│   ├── utils/                # 工具函数
│   ├── app.tsx               # 应用入口配置
│   └── access.ts             # 权限配置
├── mock/                     # Mock数据
├── public/                   # 公共静态资源
├── dist/                     # 构建产物
```

### 4.2 核心架构设计

#### 4.2.1 应用初始化流程（app.tsx）

应用启动时执行以下关键步骤：

1. Token 认证处理（`auth()`）
   - 检查 URL 参数中的 token。
   - 验证 Cookie 中的 token 有效性。
   - 失败则跳转登录页。
2. 动态路由生成
   - 通过 `getUserMenuPerm()` 接口获取用户菜单权限。
   - 将接口返回的菜单与本地路由配置 `routerElementMap` 合并。
3. 页面布局渲染
   - 使用 `@ant-design/pro-components` 的布局组件。
   - 自定义菜单渲染、面包屑、顶部导航。

#### 4.2.2 路由架构

路由配置方式：

- 本地路由配置：`src/routes/routerElementMap.tsx`，定义所有页面组件和路由结构。
- 动态路由合并：服务端返回的权限菜单与本地配置合并。

#### 4.2.3 API 管理架构

```text
src/apis/
├── index.ts                    # 通用API
├── login.ts                    # 登录相关
├── role.ts                     # 角色管理
├── organizationalStructure.ts  # 组织架构
├── announcementConfig.ts       # 公告配置
└── type/                       # API类型定义
```

API 调用封装：

- 使用 axios 封装，文件位置为 `src/utils/axios.ts`。
- 统一错误处理。
- 请求/响应拦截器。

#### 4.2.4 状态管理架构

使用 Zustand 进行状态管理。

```ts
// src/store/user.ts
// 用户状态存储：用户信息、权限等
```

#### 4.2.5 样式方案

- 全局样式：`antd.cover.less`，覆盖 Ant Design 样式。
- Less 模块化：`*.module.less`，组件级样式隔离。
- TailwindCSS：工具类快速开发。

## 5. 业务流程

这是一个权限管理与配置后台系统，主要服务于教师工作台前台。系统通过「功能 - 权限包 - 角色」的权限体系控制不同角色用户的功能访问范围。

### 5.1 权限体系设计原则：RBAC

- 基于角色的权限访问控制。
- 权限包中配置页面、模块、字段、工具的权限。
- 角色下绑定权限包，一个角色可以绑定多个权限包。
- 给用户分配角色，一个用户只能配置一个角色。

### 5.2 新功能上线完整流程

1. 菜单管理
   - 添加新功能的菜单项。
   - 配置 URL 和排序。
2. 工具管理
   - 注册功能对应的工具入口。
   - 设置工具类型，支持单体工具和批量工具。
3. 模版管理（如涉及通信功能）
   - 从比翼平台获取模版。
   - 配置模版参数。
   - 设置支持模块。
4. 权限包管理
   - 创建或更新权限包。
   - 添加新菜单到权限包。
   - 配置工具权限。
   - 关联模版权限。
5. 角色管理
   - 为需要使用新功能的角色绑定或更新权限包。
6. 用户管理
   - 为用户分配角色。
   - 用户登录后即可使用新功能。

## 6. Q&A

### 6.1 新创建的工具在权限包中找不到？

原因：

- 工具创建后需要手动添加到权限包。

解决方案：

- 权限包管理 → 编辑权限 → 工具权限配置 → 从左侧选择新工具 → 移到右侧 → 保存。

### 6.2 角色权限修改后用户仍然看不到？

原因：

- 用户需要重新登录才能获取最新权限。

解决方案：

- 通知用户退出登录 → 重新登录 → 系统会重新获取权限菜单。

# 知音楼文档
https://yach-doc-shimo.zhiyinlou.com/docs/d4vaMKP1u0NTtpj3 《TWS-管理后台 前端 yk 交接文档 - 2025.11.14》