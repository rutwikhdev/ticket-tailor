from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Persist UTC as naive SQLite values and restore aware UTC datetimes."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetime must include a timezone")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


class WebhookEvent(Base):
    __tablename__ = "webhook_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_type: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class BalanceTransaction(Base):
    __tablename__ = "balance_transaction"
    __table_args__ = (
        CheckConstraint("type IN ('charge', 'refund')", name="balance_transaction_type"),
        CheckConstraint("currency = 'GBP'", name="balance_transaction_currency"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    order_reference: Mapped[str | None] = mapped_column(String)
    reference_charge_id: Mapped[str | None] = mapped_column(String)
    charge_id: Mapped[str | None] = mapped_column(
        ForeignKey("balance_transaction.id")
    )
    currency: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str | None] = mapped_column(String)
    stripe_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    application_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net: Mapped[int] = mapped_column(Integer, nullable=False)
    available_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class Payout(Base):
    __tablename__ = "payout"
    __table_args__ = (
        CheckConstraint(
            "status IN ('paid', 'unpaid', 'processing')", name="payout_status"
        ),
        CheckConstraint("currency = 'GBP'", name="payout_currency"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    arrival_date: Mapped[date] = mapped_column(Date, nullable=False)


class PayoutTransaction(Base):
    __tablename__ = "payout_transaction"
    __table_args__ = (
        UniqueConstraint(
            "reference_transaction_id", name="payout_transaction_reference"
        ),
    )

    payout_id: Mapped[str] = mapped_column(
        ForeignKey("payout.id", ondelete="CASCADE"), primary_key=True
    )
    reference_transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    balance_transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("balance_transaction.id")
    )


def create_database(url: str) -> tuple[Engine, sessionmaker]:
    options: dict[str, Any] = {}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine, sessionmaker(engine, expire_on_commit=False)


def _enable_sqlite_foreign_keys(connection: Any, connection_record: Any) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
