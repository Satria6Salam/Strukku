"""Menjalankan migrasi database (Alembic) dari kode.

Dipakai otomatis saat server start (AUTO_MIGRATE=true) dan bisa dipanggil
manual: `python -m app.db.migrate`.

Jika database sudah berisi tabel dari backend versi lama (dibuat dengan
`create_all`, tanpa tabel `alembic_version`), database ditandai sebagai
revisi baseline lebih dulu, lalu ditingkatkan ke skema terbaru. Data lama
tidak dihapus.
"""
import logging

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import BASE_DIR, settings
from app.db.session import engine

logger = logging.getLogger("strukku")
BASELINE_REVISION = "0001_baseline"


def alembic_config() -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    cfg.attributes["configure_logger"] = False
    return cfg


def upgrade_database() -> None:
    cfg = alembic_config()
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and "receipts" in tables:
        logger.info("Database versi lama terdeteksi, menandai revisi baseline.")
        command.stamp(cfg, BASELINE_REVISION)
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    upgrade_database()
    print("Database sudah pada skema terbaru.")
