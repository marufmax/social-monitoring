from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.post import PostCreate
from app.models.post import Post
from app.database import get_db

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("/")
async def create_post(post: PostCreate, db: AsyncSession = Depends(get_db)):
    new_post = Post(title=post.title, content=post.content)
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    return new_post
