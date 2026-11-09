"""Ekspor data barang berlabel untuk melatih ulang model ML.

Contoh:
    python -m scripts.export_training_data                 # semua barang berkategori
    python -m scripts.export_training_data --corrected-only # hanya hasil koreksi pengguna
    python -m scripts.export_training_data -o data_latih.csv

Kolom CSV: item_name, category (label model), predicted_category,
prediction_source, confidence_score, is_user_corrected
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import aliased  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Category, ReceiptItem  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default="training_data.csv")
    parser.add_argument("--corrected-only", action="store_true")
    args = parser.parse_args()

    predicted = aliased(Category)
    stmt = (
        select(
            ReceiptItem.item_name,
            Category.name,
            predicted.name,
            ReceiptItem.prediction_source,
            ReceiptItem.confidence_score,
            ReceiptItem.is_user_corrected,
        )
        .join(Category, Category.id == ReceiptItem.category_id)
        .outerjoin(predicted, predicted.id == ReceiptItem.predicted_category_id)
        .order_by(ReceiptItem.id)
    )
    if args.corrected_only:
        stmt = stmt.where(ReceiptItem.is_user_corrected.is_(True))

    with SessionLocal() as db, open(args.output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["item_name", "category", "predicted_category", "prediction_source", "confidence_score", "is_user_corrected"]
        )
        count = 0
        for row in db.execute(stmt):
            writer.writerow(row)
            count += 1
    print(f"{count} baris ditulis ke {args.output}")


if __name__ == "__main__":
    main()
