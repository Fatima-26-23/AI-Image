from fastapi import FastAPI

from app.db import Base, engine
from app.routers import images, posts

app = FastAPI(title="FlyRank Capstone — AI Image Matching Engine")

# Dev convenience only — in a real deploy, migrations own table creation.
Base.metadata.create_all(bind=engine)

app.include_router(images.router)
app.include_router(posts.router)


@app.get("/health")
def health():
    return {"status": "ok"}
