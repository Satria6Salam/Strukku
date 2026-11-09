"""Copy application data from SQLite to PostgreSQL/Supabase.

Usage:
  python scripts/migrate_sqlite_to_postgres.py --source sqlite:///./strukku.db --target "postgresql+psycopg://..."

Run Alembic against the target database before copying this data.
"""
import argparse

from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert


TABLE_ORDER = [
    "users",
    "categories",
    "receipts",
    "receipt_items",
    "password_reset_tokens",
    "security_events",
    "refresh_tokens",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--truncate", action="store_true")
    args = parser.parse_args()

    source = create_engine(args.source)
    target = create_engine(args.target)
    source_metadata = MetaData()
    target_metadata = MetaData()

    copied = {}
    with source.connect() as src, target.begin() as dst:
        for table_name in TABLE_ORDER:
            source_table = Table(table_name, source_metadata, autoload_with=source)
            target_table = Table(table_name, target_metadata, autoload_with=target)
            if args.truncate:
                dst.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
            rows = [dict(row) for row in src.execute(source_table.select()).mappings()]
            if not rows:
                copied[table_name] = 0
                continue

            if args.truncate:
                dst.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
            for row in rows:
                dst.execute(insert(target_table).values(**row).on_conflict_do_nothing())
            copied[table_name] = len(rows)

        if target.dialect.name == "postgresql":
            for table_name in TABLE_ORDER:
                dst.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                    f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM \"{table_name}\""
                ))

    print("Data migration completed:")
    for table_name, count in copied.items():
        print(f"- {table_name}: {count} rows")


if __name__ == "__main__":
    main()
