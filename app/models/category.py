from sqlalchemy import Boolean, Integer, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Category(Base):
    """Kategori pengeluaran.

    `name` berisi *key* kategori yang sama persis dengan label keluaran model
    ML (mis. "Kebutuhan_Rumah_Tangga"). Tampilan untuk pengguna memakai
    `display_name`, `icon`, dan `color` yang diisi dari
    `app/data/category_catalog.json`.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(9), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    @property
    def key(self) -> str:
        return self.name

    @property
    def label(self) -> str:
        return self.display_name or self.name.replace("_", " ")
