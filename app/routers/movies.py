from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..database.madels_db import Movies

router = APIRouter()


@router.get("/api/movies")
async def list_movies_page(db: AsyncSession = Depends(get_db)):
    movies = (await db.execute(select(Movies))).scalars().all()
    return {
        "movies": [
            {
                "id": movie.id,
                "name": movie.name,
                "duration": movie.duration,
                "release_date": movie.release_date,
                "description": movie.description,
                "preview_foto": movie.preview_foto,
            }
            for movie in movies
        ]
    }