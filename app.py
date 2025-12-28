from fastapi import FastAPI
from config import init_db
from routers import user, conversations, messages, post, socket, signaling
from fastapi.middleware.cors import CORSMiddleware


init_db()
app = FastAPI()

origins = [
    "http://localhost:5173",                    # Vite dev server
    "http://127.0.0.1:5173",                    # Localhost alternativo
    "http://localhost:3000",                    # Create React App
    "https://localhost:5173",                   # HTTPS local (raro pero posible)
    "https://messagin-frontend.vercel.app",     # Tu dominio principal
    "https://messagin-frontend-git-main-santiagomorillodevs-projects.vercel.app",
    # Los wildcards con * no funcionan en FastAPI CORS, necesitas listarlos explícitamente
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
