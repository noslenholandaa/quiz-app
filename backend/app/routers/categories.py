from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, CategoryDB, TagDB
from app.schemas.models import CategoryResponse, TagResponse

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(CategoryDB).order_by(CategoryDB.name).all()


@router.get("/tags", response_model=list[TagResponse])
def list_tags(db: Session = Depends(get_db)):
    return db.query(TagDB).order_by(TagDB.name).all()
