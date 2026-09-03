from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from .db import BalanceTransaction, Payout, PayoutTransaction
from .utils import DatePeriod, get_period
from .webhook import process_delivery


router = APIRouter()
PeriodKey = Literal[
    "today",
    "yesterday",
    "this_week",
    "last_week",
    "this_month",
    "last_month",
    "all_time",
]


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def requested_period(period: str, timezone: str) -> DatePeriod:
    try:
        return get_period(period, timezone)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def filter_dates(statement: Select, column, period: DatePeriod) -> Select:
    if period.start is not None:
        statement = statement.where(column >= period.start)
    if period.end is not None:
        statement = statement.where(column < period.end)
    return statement


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "fastapi",
        "message": "The API is connected and ready.",
    }


@router.post("/webhooks")
def webhook(
    response: Response,
    payload: object = Body(...),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    try:
        outcome = process_delivery(session, payload)
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    response.status_code = 201 if outcome == "created" else 409 if outcome == "stale" else 200
    return {"outcome": outcome}


@router.get("/transactions")
def transactions(
    kind: Literal["sale", "refund"] = "sale",
    period: PeriodKey = "all_time",
    timezone: str = "UTC",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    selected = requested_period(period, timezone)
    transaction_type = "charge" if kind == "sale" else "refund"
    base = filter_dates(
        select(BalanceTransaction).where(BalanceTransaction.type == transaction_type),
        BalanceTransaction.available_on,
        selected,
    )
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.scalars(
        base.order_by(
            BalanceTransaction.available_on.desc(),
            BalanceTransaction.source_created_at.desc(),
            BalanceTransaction.id.desc(),
        ).offset((page - 1) * page_size).limit(page_size)
    ).all()
    charge_ids = {
        transaction.charge_id for transaction in rows if transaction.charge_id
    }
    charges = {
        charge.id: charge
        for charge in session.scalars(
            select(BalanceTransaction).where(BalanceTransaction.id.in_(charge_ids))
        )
    } if charge_ids else {}
    items = []
    for transaction in rows:
        is_reconciled = (
            transaction.type == "charge" or transaction.charge_id is not None
        )
        target = charges.get(transaction.charge_id)
        included = (
            transaction.status == "succeeded"
            if transaction.type == "charge"
            else is_reconciled
        )
        items.append(
            {
                "id": transaction.id,
                "type": "sale" if transaction.type == "charge" else "refund",
                "order_reference": transaction.order_reference or (target.order_reference if target else None),
                "related_charge_id": transaction.reference_charge_id,
                "currency": transaction.currency,
                "amount": transaction.amount,
                "stripe_fee": transaction.stripe_fee,
                "ticket_tailor_fee": transaction.application_fee,
                "net": transaction.net,
                "status": transaction.status,
                "available_on": transaction.available_on.isoformat(),
                "reconciled": is_reconciled,
                "included_in_reporting": included,
            }
        )
    return _page(items, page, page_size, total)


@router.get("/payouts")
def payouts(
    status: Literal["all", "paid", "unpaid", "processing"] = "all",
    period: PeriodKey = "all_time",
    timezone: str = "UTC",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    selected = requested_period(period, timezone)
    base = select(Payout)
    if status != "all":
        base = base.where(Payout.status == status)
    base = filter_dates(base, Payout.arrival_date, selected)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.scalars(
        base.order_by(Payout.arrival_date.desc(), Payout.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    counts = dict(
        session.execute(
            select(PayoutTransaction.payout_id, func.count())
            .where(PayoutTransaction.payout_id.in_([row.id for row in rows]))
            .group_by(PayoutTransaction.payout_id)
        ).all()
    ) if rows else {}
    items = [
        {
            "id": payout.id,
            "currency": payout.currency,
            "amount": payout.amount,
            "status": payout.status,
            "arrival_date": payout.arrival_date.isoformat(),
            "transaction_count": counts.get(payout.id, 0),
            "reconciled": payout.is_reconciled,
            "included_in_reporting": payout.is_reconciled,
        }
        for payout in rows
    ]
    return _page(items, page, page_size, total)


@router.get("/reports/overview")
def overview(
    period: PeriodKey = "all_time",
    timezone: str = "UTC",
    session: Session = Depends(get_session),
) -> dict:
    selected = requested_period(period, timezone)
    transaction_rows = session.scalars(
        filter_dates(select(BalanceTransaction), BalanceTransaction.available_on, selected)
    ).all()
    reportable_transactions = [
        transaction
        for transaction in transaction_rows
        if (
            transaction.status == "succeeded"
            if transaction.type == "charge"
            else transaction.charge_id is not None
        )
    ]

    payout_rows = session.scalars(
        filter_dates(select(Payout), Payout.arrival_date, selected)
    ).all()
    reportable_payouts = [
        payout
        for payout in payout_rows
        if payout.is_reconciled
    ]

    net_revenue = sum(transaction.net for transaction in reportable_transactions)
    completed = sum(
        payout.amount
        for payout in reportable_payouts
        if payout.status == "paid" and payout.arrival_date <= selected.today
    )
    available = sum(
        payout.amount
        for payout in reportable_payouts
        if payout.status == "unpaid" and payout.arrival_date <= selected.today
    )
    schedule = [
        {
            "id": payout.id,
            "amount": payout.amount,
            "currency": payout.currency,
            "status": payout.status,
            "arrival_date": payout.arrival_date.isoformat(),
        }
        for payout in sorted(reportable_payouts, key=lambda item: (item.arrival_date, item.id))
        if payout.status != "paid"
    ]
    excluded_transactions = sum(
        transaction.type == "refund" and transaction.charge_id is None
        for transaction in transaction_rows
    )
    excluded_payouts = sum(not payout.is_reconciled for payout in payout_rows)
    return {
        "currency": "GBP",
        "period": selected.as_dict(),
        "summary": {
            "net_revenue": net_revenue,
            "payouts_completed": completed,
            "available_to_payout": available,
            "pending": net_revenue - completed - available,
        },
        "revenue_breakdown": {
            "gross_sales": sum(
                transaction.amount
                for transaction in reportable_transactions
                if transaction.type == "charge"
            ),
            "refunds": sum(
                transaction.amount
                for transaction in reportable_transactions
                if transaction.type == "refund"
            ),
            "ticket_tailor_fees": sum(
                transaction.application_fee for transaction in reportable_transactions
            ),
            "stripe_fees": sum(
                transaction.stripe_fee for transaction in reportable_transactions
            ),
            "net_revenue": net_revenue,
        },
        "payout_schedule": schedule,
        "excluded_unreconciled_count": excluded_transactions + excluded_payouts,
    }


def _page(items: list[dict], page: int, page_size: int, total: int) -> dict:
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "page_count": (total + page_size - 1) // page_size,
    }
