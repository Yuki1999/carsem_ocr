# carsem_ocr (Vite + Vue + FastAPI)

## 用户文档
- [用户使用说明](./用户使用说明.md)

## 架构
- `app/`: FastAPI 后端（仅 API + 生产静态托管）
- `frontend/`: Vite + Vue 前端工程

## 开发模式
### 1) 启动后端
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 16068 --reload
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
python -m uvicorn app.main:app --host 0.0.0.0 --port 16068
```

生产模式下，FastAPI 自动托管 `frontend/dist`。

## PM2 部署（推荐）
- 前端端口固定：`16066`
- 后端端口：`16068`（可改，但需同步前端代理目标）

```bash
cd /home/sip-telecom/Services/carsem_ocr
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

## LLM 配置
支持两种方式配置大模型服务：

1. 在前端“高级设置”中填写（`llm_base_url`、`llm_model`、`llm_api_key`）
2. 使用后端环境变量
```bash
export LLM_BASE_URL="http://127.0.0.1:11434/v1"
export LLM_MODEL="qwen2.5:14b"
export LLM_API_KEY=""
```

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
