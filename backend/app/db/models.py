from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CalculationRecord(Base):
    __tablename__ = "calculation_records"
    __table_args__ = (UniqueConstraint("param_hash", "method_code", "benchmark_price", name="uq_calc_summary"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    method_code: Mapped[str] = mapped_column(String(10), nullable=False)
    ceiling_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    benchmark_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    discount_rate: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    bidder_count: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_count: Mapped[int] = mapped_column(Integer, nullable=False)
    param_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CalculationLog(Base):
    __tablename__ = "calculation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    method_code: Mapped[str] = mapped_column(String(10), nullable=False)
    bidder_count: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    benchmark_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    param_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
