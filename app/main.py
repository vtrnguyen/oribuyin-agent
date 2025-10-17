from fastapi import FastAPI
from app.routers import ai_router

app = FastAPI(title="OriBuyin AI Service")

app.include_router(ai_router.router, prefix="/ai")

@app.get("/")
def root():
    return {"message": "welcome to the OriBuyin AI Service!"}