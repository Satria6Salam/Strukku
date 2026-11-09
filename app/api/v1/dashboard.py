from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.core.timeutils import parse_month
from app.schemas.dashboard import CategoryBreakdownOut, DashboardOut, MonthlyPointOut
from app.services import dashboard_service

router = APIRouter(tags=["Dashboard & Analitik"])
MONTH_QUERY = Query(None, description="Bulan YYYY-MM. Kosong = bulan ini.", examples=["2026-10"])


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: DB, user: CurrentUser, month: str | None = MONTH_QUERY):
    """Semua data layar **Beranda** dalam satu panggilan."""
    return dashboard_service.dashboard(db, user, parse_month(month))


@router.get("/analytics/categories", response_model=CategoryBreakdownOut)
def category_breakdown(db: DB, user: CurrentUser, month: str | None = MONTH_QUERY):
    """Data layar **Kategori Pengeluaran**: nominal & persentase per kategori."""
    return dashboard_service.category_breakdown(db, user, parse_month(month))


@router.get("/analytics/monthly", response_model=list[MonthlyPointOut])
def monthly_trend(
    db: DB,
    user: CurrentUser,
    month: str | None = Query(None, description="Bulan terakhir (YYYY-MM). Kosong = bulan ini."),
    months: int = Query(6, ge=1, le=24, description="Jumlah bulan ke belakang"),
):
    """Tren total pengeluaran per bulan (untuk grafik)."""
    return dashboard_service.monthly_trend(db, user, parse_month(month), months)
