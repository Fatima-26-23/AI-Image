from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Post, PostVector
from app.services.suggestion_service import create_post_with_embedding, get_ranked_suggestions

router = APIRouter()


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)


@router.post("/posts", status_code=201)
def create_post(payload: PostCreate, db: Session = Depends(get_db)):
    post = create_post_with_embedding(db, title=payload.title, content=payload.content)
    return {"id": post.id, "title": post.title, "content": post.content}


@router.get("/posts/{post_id}/images")
def get_post_images(post_id: int, top_n: int = 5, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")

    vector_row = db.query(PostVector).filter(PostVector.post_id == post_id).first()
    if vector_row is None:
        raise HTTPException(status_code=422, detail="post has no embedding yet")

    return get_ranked_suggestions(db, post, vector_row.embedding, top_n=top_n)
