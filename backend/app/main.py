from fastapi import FastAPI
from .routers import router

app = FastAPI(title="Legal Doc Platform API")
app.include_router(router)