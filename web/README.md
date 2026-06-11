# channel-analytics 前端(Vue 3 + Vite)

最小骨架:登录页 + 仪表盘页,演示与 FastAPI 后端的 JWT 流程。

## 开发

```bash
cd web
npm install
npm run dev    # http://localhost:5173
```

Vite dev server 自动把 `/api/*` 反代到 `http://localhost:8000/*`(见 `vite.config.ts`)。

## 生产构建

```bash
npm run build
# 输出 web/dist/,可被 nginx / caddy / 任何静态服务托管
```

## 部署到 FastAPI

把 `dist/` 放到 `channel_analytics/api/static/`,FastAPI 用 `StaticFiles` mount:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="channel_analytics/api/static", html=True))
```

## 目录结构

```
web/
├── index.html         # 入口 HTML
├── vite.config.ts     # Vite 配置(dev proxy + build)
├── package.json
├── tsconfig.json
└── src/
    ├── main.ts        # Vue 入口(createApp + Pinia + Router)
    ├── App.vue        # 根组件(header + nav + RouterView)
    ├── api/
    │   └── index.ts   # axios 拦截器(自动带 token)
    ├── router/
    │   └── index.ts   # vue-router 配置
    └── pages/
        ├── LoginPage.vue      # 登录(POST /api/auth/login)
        └── DashboardPage.vue  # 仪表盘(GET /api/auth/me + /api/reports)
```

## 不做的事

- 不引入大型 UI 库(Element Plus / Ant Design Vue)— 部署方可按需加
- 不写复杂状态管理(只用 Pinia 单 store)— 部署方可扩
- 不内嵌任何真实品牌名 / 客户代号 / 厂商字符串