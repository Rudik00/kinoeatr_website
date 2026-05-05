from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..database.madels_db import Movies, MovieSession, CinemaHall

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


@router.get("/api/movies/{movie_id}")
async def movie_detail_page(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(Movies, movie_id)
    if not movie:
        return {"error": "Фильм не найден"}

    sessions = (
        await db.execute(
            select(MovieSession)
            .where(MovieSession.movie_id == movie_id)
            .order_by(MovieSession.starts_at.asc())
        )
    ).scalars().all()

    halls = (await db.execute(select(CinemaHall))).scalars().all()
    hall_name_by_id = {h.id: h.name_hall for h in halls}

    return {
        "id": movie.id,
        "name": movie.name,
        "duration": movie.duration,
        "release_date": movie.release_date,
        "description": movie.description,
        "preview_foto": movie.preview_foto,
        "sessions": [
            {
                "id": session.id,
                "hall_id": session.hall_id,
                "hall_name": hall_name_by_id.get(session.hall_id),
                "starts_at": session.starts_at.isoformat(),
                "base_price": session.base_price,
            }
            for session in sessions
        ],
    }
