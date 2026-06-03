# 国网价格分在线测算系统

基于项目需求文档和技术选型实现的 MVP：Vue 3 + Vite + TypeScript + Element Plus 前端，FastAPI + Pydantic v2 后端，独立 Decimal 计算引擎，SQLite 匿名摘要沉淀，openpyxl 导入导出。

## 功能

- 支持 A01-A08 八种价格评分方法。
- 支持手工录入报价、`.xlsx` 导入。
- 输出基准价、折扣率、价格分、排名、目标公司分差、计算过程。
- 导出包含 `测算结果`、`报价明细`、`参数设置`、`计算过程` 四个工作表的 Excel。
- 默认只保存匿名测算摘要，不保存投标人名称和单家报价明细。

## 本地运行

后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

若默认端口被占用，可改用未占用端口，例如：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8002

cd ../frontend
VITE_API_TARGET=http://127.0.0.1:8002 npm run dev -- --host 0.0.0.0 --port 5174
```

## 测试

```bash
cd backend
pytest
```

## 业务说明

`国网报价算分模板全8套v1.2.xlsx` 作为当前对账基准。A07 按模板采用 `A2 * (1 - a)`。
