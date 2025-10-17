from fastapi import APIRouter
from app.ai_agent import handle_question

router = APIRouter()

@router.post("/ask")
async def ask_ai(request: dict):
    question = request.get("question")
    if not question:
        return {"error": "question is required"}
    
    result = handle_question(question)
    return {"answer": result}