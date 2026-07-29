from pydantic import BaseModel


class CatalogItem(BaseModel):
    id: int
    nombre: str
