from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.session import init_db

app = FastAPI(title="国网价格分在线测算系统", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
