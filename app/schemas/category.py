from pydantic import AliasChoices, Field

from app.schemas.common import ORMModel


class CategoryBrief(ORMModel):
    id: int
    key: str = Field(description="Label kategori di model ML, mis. Kebutuhan_Rumah_Tangga")
    name: str = Field(
        validation_alias=AliasChoices("label", "name"),
        description="Nama tampilan, mis. Kebutuhan Rumah Tangga",
    )
    icon: str | None = Field(default=None, description="Nama Material Icon untuk Flutter")
    color: str | None = Field(default=None, description="Warna hex, mis. #2563EB")


class CategoryOut(CategoryBrief):
    description: str | None = None
    sort_order: int = 0
