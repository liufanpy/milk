from sqlalchemy.orm import Session
from app.models.shelf import Shelf
from app.repositories.base import BaseRepository


class ShelfRepository(BaseRepository[Shelf]):
    def __init__(self, db: Session):
        super().__init__(Shelf, db)

    def get_by_name(self, name: str):
        return self.db.query(Shelf).filter(Shelf.name == name).first()
