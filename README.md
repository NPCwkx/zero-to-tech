# 文字实验室

一个中文文本分析小工具：输入中文文本，获得全文拼音及情感倾向评分，并按访客会话保存分析历史。不同浏览器会话的历史记录相互隔离。

本项目是「零到全栈」课程的贯穿练习，现已完成第 7.2 节的服务器部署改造。

> 本 README 按课程 7.1 的完整项目说明和 7.2 的更新要求整理，并适配当前阿里云 Ubuntu 用户 `admin`。它不是教师 GitHub 上现成的 7.2 README 原文件。

## 技术栈

- 前端：Next.js（静态导出）+ React
- 后端：FastAPI + Uvicorn
- 中文分析：pypinyin（拼音）+ SnowNLP（情感）
- 数据存储：SQLite；通过会话区分不同访问者
- 部署：Ubuntu + Nginx（静态文件及 `/api/` 反向代理）+ systemd（服务管理）

## 功能与接口

- 首页：通过 `GET /api/profile` 获取展示内容。
- 文字实验室：通过 `POST /api/analyze` 生成文本分析结果。
- 历史记录：通过 `GET /api/history` 查看当前会话的历史。
- 开发文档：FastAPI 本地提供 `/docs`；生产环境 Nginx 只代理 `/api/`，不对公网转发 `/docs`。

## 本地跑起来

要求：Node.js 18+、Python 3.10+。

**1. 启动后端**

在项目根目录下：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env
```

在 `backend/.env` 中配置：

```env
ALLOWED_ORIGINS=http://localhost:3000
```

启动开发服务器：

```bash
fastapi dev
```

后端默认可通过 `http://127.0.0.1:8000` 访问。

> Windows PowerShell：如果 `python3` 不可用，请使用 `python -m venv .venv`；激活虚拟环境使用 `.venv\Scripts\Activate.ps1`。Windows 上不支持 Bash 的 `cp` 写法时，可使用 `Copy-Item .env.example .env`。

**2. 启动前端（另开一个终端）**

回到项目根目录：

```bash
npm install
cp -n .env.example .env.local
```

在 `.env.local` 中配置：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

启动开发服务器：

```bash
npm run dev
```

浏览器打开 `http://localhost:3000`。

本地前端和后端运行在不同端口，属于跨源请求，因此开发环境仍需要 FastAPI 的 CORS 配置。

## 部署到服务器

以下步骤针对当前阿里云 Ubuntu 环境，项目目录为 `/home/admin/zero-to-tech`。第一次部署需安装 Python 3.10+、Node.js 18+、Nginx，并将代码放到这个目录。

**1. 更新代码**

```bash
cd ~/zero-to-tech
git pull
```

**2. 前端：配置和构建**

```bash
cd ~/zero-to-tech
npm install
cp -n .env.example .env.production
```

编辑 `.env.production`，将变量值留空：

```env
NEXT_PUBLIC_API_BASE_URL=
```

构建前检查服务器上是否还有 `.env.local`，因为它可能优先于 `.env.production` 生效。确定最终生产配置正确后执行：

```bash
npm run build
```

Next.js 静态导出生成 `out/`，Nginx 将直接提供其中的 HTML、CSS、JavaScript 文件。运行这些静态文件不需要常驻 Node.js 进程。

**3. 后端：虚拟环境、依赖、配置**

```bash
cd ~/zero-to-tech/backend
python3 -m venv --prompt=zero-to-tech .venv  # 首次创建时执行
source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env
```

服务器的 `backend/.env` 中配置：

```env
ALLOWED_ORIGINS=http://101.132.189.39
```

生产环境前后端通过 Nginx 同源访问；仍保留此项配置，以满足项目的启动要求及本地跨源开发需要。不要把 `.env` 中的私密信息提交到 Git 仓库。

**4. 使用 systemd 托管后端**

首次部署时创建 `/etc/systemd/system/zero-backend.service`：

```ini
[Unit]
Description=zero-to-tech backend

[Service]
User=admin
WorkingDirectory=/home/admin/zero-to-tech/backend
ExecStart=/home/admin/zero-to-tech/backend/.venv/bin/fastapi run --host 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

应用服务配置并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl start zero-backend
sudo systemctl enable zero-backend
sudo systemctl status zero-backend
```

后端只监听 `127.0.0.1:8000`。Nginx 与 FastAPI 在同一台服务器上通信，无需向公网开放 8000 端口。

**5. 配置 Nginx 静态服务和反向代理**

编辑 `/etc/nginx/sites-available/default` 中本项目对应的 `server` 块，不要误删其他站点配置：

```nginx
server {
    listen 80 default_server;
    server_name _;

    root /home/admin/zero-to-tech/out;
    index index.html;

    location / {
        try_files $uri $uri.html $uri/ =404;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`proxy_pass` 的目标不要额外加尾部 `/`，以便向后端保留原始 `/api/...` 路径。

```bash
sudo nginx -t
sudo systemctl reload nginx
```

**6. 配置云平台防火墙**

- TCP 22：SSH 管理（推荐进一步限制允许访问的来源地址）。
- TCP 80：HTTP 网站访问。
- TCP 8000：不要对公网放行。

本节仍使用 HTTP；后续配置 HTTPS 时需额外开放 TCP 443。

**7. 验证部署**

在云服务器上：

```bash
sudo systemctl status zero-backend
sudo ss -lntp | grep :8000
curl -i http://127.0.0.1:8000/docs
curl -i http://127.0.0.1/api/profile
```

`ss` 应显示 FastAPI 监听 `127.0.0.1:8000`。本机访问 `/docs` 和经 Nginx 访问 `/api/profile` 应正常返回 HTTP 响应。

在个人电脑浏览器访问 `http://101.132.189.39`，验证首页、文字分析、拼音和历史记录。用无痕窗口再次访问，确认不同会话的历史不会混在一起。

打开开发者工具的 Network 面板，确认 API 请求使用与网页相同的协议、主机和端口，并且不再直接请求公网 `:8000`。最后确认公网 `http://101.132.189.39:8000` 无法连接。

## 配置说明

实际配置文件不纳入 Git。请根据对应目录里的 `.env.example` 创建。

**前端**：本地使用 `.env.local`，生产构建使用 `.env.production`。

| 变量 | 作用 | 本地开发 | 生产环境 |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | API 请求的基础地址 | `http://localhost:8000` | 留空，浏览器使用同源相对路径 |

**后端**：`backend/.env`。

| 变量 | 作用 | 本地开发 | 当前生产环境 |
| --- | --- | --- | --- |
| `ALLOWED_ORIGINS` | CORS 允许的前端来源 | `http://localhost:3000` | `http://101.132.189.39` |

注意：`NEXT_PUBLIC_` 前缀变量可能在构建时进入浏览器端代码，绝不能用于保存 API 密钥或密码。修改生产环境前端变量后必须重新构建。

## 日常发布

```bash
cd ~/zero-to-tech
git pull

# 改动前端源代码或构建配置时
npm run build

# 改动后端代码时
sudo systemctl restart zero-backend
```

如更新了后端依赖，还需在 `backend/.venv` 中重新安装 `requirements.txt` 中的依赖，然后重启后端。

## 常用运维命令

```bash
# 后端进程管理
sudo systemctl status zero-backend
sudo systemctl start zero-backend
sudo systemctl stop zero-backend
sudo systemctl restart zero-backend

# 查看后端日志
journalctl -u zero-backend -n 50
journalctl -u zero-backend -f

# 修改 Nginx 配置后
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status nginx

# 检查监听和反向代理
sudo ss -lntp | grep :8000
curl -i http://127.0.0.1/api/profile
```

## 课程参考

- [零到全栈：7.1 先上线](https://xn--ygr25xpohxwz.com/zero-to-fullstack/lessons/module-7-1/)
- [零到全栈：7.2 systemd 与 Nginx 反向代理](https://xn--ygr25xpohxwz.com/zero-to-fullstack/lessons/module-7-2/)
- [老师的 GitHub 配套代码仓库](https://github.com/joylibo/zero-to-tech-demos)
