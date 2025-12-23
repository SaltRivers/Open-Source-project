# 安全说明（SECURITY）

本仓库是研究原型，历史实现包含多处**严重的远程代码执行（RCE）风险**。本次优化的目标是：在不引入新依赖的前提下，**默认彻底移除 `exec()`/`eval()` 路径**，用“结构化输出（JSON）+ 白名单执行器”替代，从工程层面消除 RCE 原语，并加强默认安全策略（本地-only benchmark）。

## 1. 现有严重问题（准确说明）

### 1.1 LLM 输出被 `exec()` 直接执行（RCE）
- `halligan/halligan/stages/stage1.py`、`stage2.py`、`stage3.py` 旧实现会从模型回复中提取 Python 代码块，并直接 `exec()` 执行。
- 这意味着：**只要模型输出包含恶意 Python 语句**（例如读取本地文件、发起网络请求、执行系统命令等），就可能在运行环境中执行，属于典型 RCE。

### 1.2 LLM 输出被 `eval()` 解析（RCE）
- `halligan/halligan/utils/vision_tools.py` 旧实现用 `eval()` 解析模型返回的列表（如 `answer(numbers=[...])` / `rank(ids=[...])`）。
- `eval()` 同样会执行任意表达式，是常见 RCE 原语。

### 1.3 import-time 副作用导致不可控行为
- `halligan/halligan/utils/vision_tools.py` 旧实现会在模块 import 时读取 `.env` 并创建 `GPTAgent`。
- 结果是：在环境变量缺失时**导入即崩溃**，也不利于测试、复现与依赖注入。

## 2. 解决方案（本次改造）

### 2.1 用 JSON 输出替代 Python 代码输出
- Stage1/Stage2/Stage3 的 prompt 均改为要求输出 **纯 JSON**（不允许 markdown fence / 多余解释文本）。
- 解析采用标准库 `json.loads`，并支持从 fenced code block 或夹杂文本中提取 JSON（见 `halligan/halligan/runtime/parser.py`）。

### 2.2 Schema 校验（标准库实现）
- 对每个 stage 的 JSON 结构进行严格字段/类型校验（见 `halligan/halligan/runtime/schemas.py`），在不符合时给模型结构化反馈并重试。

### 2.3 白名单执行器替代 `exec()`
- Stage2：模型只输出“结构标注动作列表”，本地执行器按白名单调用 `split/grid/get_element/set_frame_as/set_element_as`（见 `halligan/halligan/runtime/executor.py`）。
- Stage3：模型输出受限 DSL（JSON steps），执行器仅允许：
  - 调用白名单注册工具（`halligan/halligan/runtime/registry.py`）。
  - 对特定对象调用允许的方法（严格方法白名单）。
  - 受限的表达式（变量、frame/interactable/keypoint 引用、attr/index/map/filter/len/sum）。

### 2.4 用 `ast.literal_eval()` 替代 `eval()`
- `vision_tools.ask/rank/compare` 的列表解析改为 `ast.literal_eval()`，并且只接受 list literal（见 `halligan/halligan/utils/vision_tools.py`）。

### 2.5 默认启用“本地-only benchmark”防护
- 新增 `RuntimeConfig`（`halligan/halligan/runtime/config.py`）：
  - 默认仅允许 `localhost/127.0.0.1/host.docker.internal/0.0.0.0` 等本地地址作为 benchmark URL。
  - 若确有需要，显式设置 `HALLIGAN_ALLOW_NONLOCAL_BENCHMARK=1` 才允许非本地 URL。
- 入口脚本 `halligan/execute.py` 与 `halligan/generate.py` 已接入该校验。

## 3. 如何验证安全改造有效

### 3.1 运行单元测试（不依赖外部服务）
在 `halligan/` 目录下执行：
```bash
pixi run pytest -m 'not integration' -q
```

### 3.2 检查仓库内是否仍存在 `exec()`/`eval()` 用于处理模型输出
在仓库根目录执行：
```bash
rg -n "\\bexec\\(|\\beval\\(" halligan/halligan
```
期望结果：不再出现 stage 代码路径中的 `exec/eval`（只允许出现在文档/注释中）。

## 4. 重要提示
- 本次改造是**安全与工程化**导向：减少 RCE 面、提升可测性/可复现性/可维护性，并不以提升绕过能力为目标。
- 若你要在受控环境中进行研究复现，请确保：
  - 在隔离环境运行（容器/沙盒/最小权限账号）。
  - 仅连接本地 benchmark 服务。

