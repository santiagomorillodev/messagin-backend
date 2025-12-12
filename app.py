from fastapi import FastAPI
from config import init_db
from routers import user, conversations, messages, post, socket, signaling
from fastapi.middleware.cors import CORSMiddleware


init_db()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://messagin-backend.onrender.com", "https://messagin-frontend.vercel.app/"],  # 🌐 orígenes permitidos
    allow_credentials=True,                   # 🔑 necesario para cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(user)
app.include_router(conversations)
app.include_router(messages)
app.include_router(post)
app.include_router(socket)
app.include_router(signaling)

@app.get('/')
def root():
    return {'message': 'Api running'}
