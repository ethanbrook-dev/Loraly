from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000" # When ready to publish switch this to your frontend url (the one that should be able to make api calls here)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate-voice")
async def generate_voice(request: Request):
    data = await request.json()
    print("Received data:", data)
    return {"status": "success", "message": "Voice generation started!"}