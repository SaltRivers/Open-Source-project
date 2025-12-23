# 使用说明（USAGE）

本文档以“安全默认”的方式说明如何运行本仓库。

## 1. 环境变量

在 `halligan/` 目录复制示例：
```bash
cp .env.example .env
```

常用变量：
- `OPENAI_API_KEY`: OpenAI key（用于 Agent）
- `BROWSER_URL`: Playwright browser WebSocket（例如 `ws://127.0.0.1:5001/`，与 `docker-compose.yml` 的端口映射一致）
- `BENCHMARK_URL`: benchmark 服务地址（**会在远程 browser 容器内加载**，建议 `http://host.docker.internal:3334`）
- `BENCHMARK_HTTP_URL`:（可选）用于**宿主机**纯 HTTP 检测的地址；若你使用 dockerized browser，推荐 `http://127.0.0.1:3334`

安全防护开关：
- `HALLIGAN_ALLOW_NONLOCAL_BENCHMARK=1`：允许连接非本地 benchmark（默认不允许）

## 2. 启动 benchmark 与 browser（Docker）

仓库根目录：
```bash
docker compose up -d --build
```

健康检查：
```bash
curl -fsS http://127.0.0.1:3334/health
```

## 3. 运行单元测试（推荐先跑）

```bash
cd halligan
pixi run pytest -m 'not integration' -q
```

如果你想在仓库根目录运行（不 `cd`），请使用 `--manifest-path` 指向 Pixi workspace：
```bash
pixi run --manifest-path halligan pytest -m 'not integration' -q
```

或直接使用 Makefile（等价于进入 `halligan/` 再运行 Pixi task）：
```bash
make test
```

## 4. 运行集成测试（需要服务）

集成测试依赖 Playwright browser 与 benchmark 服务：
```bash
cd halligan
pixi run pytest -m integration -q
```

仓库根目录运行（不 `cd`）：
```bash
pixi run --manifest-path halligan pytest -m integration -q
```

## 5. 执行（示例）

执行脚本会校验环境变量与本地-only benchmark 安全策略：
```bash
cd halligan
pixi run python execute.py
```

生成 trace（研究用途）：
```bash
cd halligan
pixi run python generate.py
```

## 6. 常见错误

### 6.1 “Detected non-local BENCHMARK_URL”
这是默认安全策略在阻止非本地 benchmark。
- 解决：把 `BENCHMARK_URL` 改成 `http://127.0.0.1:3334` 这类本地地址；
- 或者（你明确知道风险且确实需要）设置：
  ```bash
  export HALLIGAN_ALLOW_NONLOCAL_BENCHMARK=1
  ```

### 6.2 “Vision tools agent is not set”
表示你在调用 `ask/rank/compare` 前没有注入 Agent。
在正常 pipeline 中已自动处理；若你单独调用 vision tools，请先：
```python
import halligan.utils.vision_tools as vision_tools
vision_tools.set_agent(agent)
```

### 6.3 “could not find pixi.toml or pyproject.toml with tool.pixi”
说明你在**仓库根目录**运行了 `pixi ...`，但 Pixi workspace 位于 `halligan/` 子目录。
- 解决：`cd halligan` 后再运行；或使用 `pixi run --manifest-path halligan ...`。

### 6.4 Docker 构建时报 “pip SSL EOF / Could not fetch URL https://pypi.org/…”
如果你在构建 `benchmark` 镜像时看到类似日志：
- `Installing pip packages: ...`
- `SSLError(SSLEOFError(... UNEXPECTED_EOF_WHILE_READING ...))`

这通常不是 Docker registry mirror 的问题，而是容器内 `pip` 无法稳定访问 `pypi.org`（被 MITM/阻断/网络不稳定）。

推荐解决方案（更可复现）：不要在 Docker build 期间走 `pip:` 安装，改为尽量从 `conda-forge` 安装依赖。
本仓库已在 `benchmark/environment.yml` 移除 `pip:` 段并改用 conda 包；更新后请重新构建：
```bash
docker compose build --no-cache benchmark
```
