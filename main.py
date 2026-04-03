from fastapi import FastAPI
from app.database import engine
from app import models
from app.api import auth
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bazaar Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"], 
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/")
def home():
    return {"message": "Bazaar Auth Service is running. "}

@app.get("/status")
def status():
    return {"status": "OK"}