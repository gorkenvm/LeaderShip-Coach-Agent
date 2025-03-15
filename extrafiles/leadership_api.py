# leadership_api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from try2to import LeadershipChat  # Önceki kodunuzdan import

app = FastAPI()
chat_instance = LeadershipChat()  # Tek bir sohbet örneği

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        response = chat_instance.chat(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reset")
async def reset_memory():
    chat_instance.memory.clear()
    return {"message": "Hafıza sıfırlandı."}

# Çalıştırmak için: uvicorn leadership_api:app --reload