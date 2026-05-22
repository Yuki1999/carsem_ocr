# carsem_ocr (Vite + Vue + FastAPI)

## 用户文档
- [用户使用说明](./docs/user-guide.md)

## 架构
- `app/api/`: FastAPI 应用与路由入口
- `app/services/`: OCR、LLM、报关提交等后端服务
- `app/store/`: 历史记录、模板、LLM 设置持久化
- `app/main.py`: 兼容入口，继续暴露 `app.main:app`
- `frontend/`: Vite + Vue 前端工程
- `frontend/src/features/`: 前端按功能拆分的模块目录
- `samples/`: 样例 PDF 文件

## 开发模式
### 1) 启动后端
```bash
./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 16068 --reload
```

### 2) 启动前端
```bash
cd frontend
npm install
npm run dev
```

- 前端开发地址: `http://101.132.68.191:5173`
- 前端开发地址: `http://127.0.0.1:16066`
- 后端 API 地址: `http://127.0.0.1:16068`
- Vite 已代理 `/api` 到后端。

## 生产模式
```bash
cd frontend
npm install
npm run build
cd ..
./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 16068
```

生产模式下，FastAPI 自动托管 `frontend/dist`。

## PM2 部署（推荐）
- 前端端口固定：`16066`
- 后端端口：`16068`（可改，但需同步前端代理目标）

```bash
cd /home/qqr/carsem_ocr
mkdir -p output/logs
pm2 start ecosystem.config.cjs
pm2 save
```

常用命令：
```bash
pm2 restart carsem-ocr-backend
pm2 restart carsem-ocr-frontend
pm2 logs carsem-ocr-backend
pm2 logs carsem-ocr-frontend
```

## API
- `GET /api/health`
- `POST /api/extract`
- `GET /api/history`
- `GET /api/history/{record_id}`
- `GET /api/history/{record_id}/download`
- `GET /api/history/{record_id}/asset/{file_path}`
- `GET /api/history/{record_id}/text/{file_path}`

## 两阶段 Pipeline
`/api/extract` 默认按以下顺序执行：
1. MinerU 官方 API 识别文档（OCR/解析）
2. 大模型按用户提示词提取结构化结果（JSON）
3. 服务端持久化本次解析记录（压缩包 + 解压文件 + 提取结果）

前端提取页面已增加“提示词”输入框，作为第二阶段抽取指令。

## OCR 引擎选择
前端“提取工作台”与“模板管理”支持选择 OCR 引擎：

- `MinerU`：默认引擎，保持现有官方 API 流程
- `OpenDataLoader PDF`：本地解析/混合 OCR 管道，适合部署机可安装本地依赖的场景
- `Qwen3.5-Plus 端到端`：通过阿里云百炼兼容 OpenAI 接口直接完成多模态 OCR 与字段抽取
- `Excel .xlsx`：上传 `.xlsx` 时后端直接解析工作表文本，再进入大模型字段抽取链路；第一版不支持 `.xls`

后端接口新增表单字段：

- `ocr_engine=mineru|opendataloader|qwen_vision`

未传该字段时默认使用 `mineru`。

## OpenDataLoader PDF 部署
如果要启用 `OpenDataLoader PDF`，部署机需要额外准备：

```bash
java -version   # 需要 Java 11+
pip install -U opendataloader-pdf
pip install -U "opendataloader-pdf[hybrid]"
```

如果要处理扫描件 OCR，需额外启动 hybrid 服务。官方 README 示例：

```bash
opendataloader-pdf-hybrid --port 5002 --force-ocr --ocr-lang "ch_sim,en"
```

本项目后端默认通过本机命令 `opendataloader-pdf` 调用该管道，可用以下环境变量调整：

```bash
export OPENDATALOADER_PDF_COMMAND="opendataloader-pdf"
export OPENDATALOADER_PDF_OUTPUT_FORMAT="markdown,json,text"
export OPENDATALOADER_PDF_EXTRA_ARGS="--hybrid docling-fast"
```

说明：

- `OPENDATALOADER_PDF_EXTRA_ARGS` 会原样追加到命令行，适合传递 hybrid 相关参数
- 若命令未安装或执行失败，后端会返回明确错误信息
- `OpenDataLoader PDF` 结果会统一整理为 `text/markdown/json/middle_json` 后再进入 LLM 抽取与历史记录

## LLM 配置
支持两种方式配置大模型服务：

1. 在前端“高级设置”中填写（`llm_base_url`、`llm_model`、`llm_api_key`）
2. 使用后端环境变量
```bash
export LLM_BASE_URL="http://127.0.0.1:11434/v1"
export LLM_MODEL="qwen2.5:14b"
export LLM_API_KEY=""
```

如果要启用 `Qwen3.5-Plus 端到端`，可直接复用这套配置，推荐填写：

```bash
export LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export LLM_MODEL="qwen3.5-plus"
export LLM_API_KEY="sk-..."
```

说明：

- `qwen_vision` 复用前端“高级设置”中的 `llm_base_url`、`llm_model`、`llm_api_key`
- 选择 `qwen_vision` 时，不再走现有文本型 `run_llm_extract()` 二阶段抽取，而是由多模态模型直接返回最终 JSON
- 当前 `qwen_vision` 仅支持 `PDF` 和图片文件，不支持 `doc/docx/ppt/pptx/xlsx`；`.xlsx` 会走后端 Excel 文本解析链路

## MinerU 官方 Token 配置
支持两种方式配置官方 API Token：

1. 在前端“高级设置 / 系统设置”中填写 `MinerU API Token`
2. 使用后端环境变量
```bash
export MINERU_API_TOKEN="官网申请的token"
```

## 历史记录与持久化
- 历史记录默认保存在 `output/history/`
- 模板配置保存在 `output/settings/templates.json`
- LLM 配置保存在 `output/settings/llm_settings.json`
- 每条记录会保存：
  - 本次接口响应快照（`meta.json`）
  - MinerU 解析结果压缩包（`result.zip`）
  - 解压后的文件目录（`unzipped/`）
- 前端“结果中心”可查看历史记录、查看解压文件内容、下载压缩包。
