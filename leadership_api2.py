from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.agents.leadership import LeadershipChat  # veya from RagClass import LeadershipChat

app = FastAPI()
chat_instance = LeadershipChat()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)