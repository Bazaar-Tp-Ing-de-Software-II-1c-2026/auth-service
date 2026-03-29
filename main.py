from fastapi import FastAPI
from app.database import engine
from app import models
from app.api import auth

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bazaar Auth Service")

app.include_router(auth.router)

@app.get("/")
def home():
    return {"message": "Bazaar Auth Service is running. "}

@app.get("/status")
def status():
    return {"status": "OK"}