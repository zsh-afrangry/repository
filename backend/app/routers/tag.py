from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bill import TagType
from app.schemas.tag import TagCreate, TagUpdate, TagOut
from app import crud

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagOut])
def list_tags(tag_type: TagType | None = None, db: Session = Depends(get_db)):
    return crud.list_root_tags(db, tag_type)


@router.get("/all", response_model=list[TagOut])
def list_all_tags(tag_type: TagType | None = None, db: Session = Depends(get_db)):
    return crud.list_tags(db, tag_type)


@router.post("/", response_model=TagOut, status_code=201)
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    return crud.create_tag(db, data)


@router.patch("/{tag_id}", response_model=TagOut)
def update_tag(tag_id: int, data: TagUpdate, db: Session = Depends(get_db)):
    tag = crud.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return crud.update_tag(db, tag, data)


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = crud.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    crud.delete_tag(db, tag)
