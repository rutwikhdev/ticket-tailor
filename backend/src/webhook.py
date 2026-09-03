import argparse
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .db import (
    Base,
    BalanceTransaction,
    Payout,
    PayoutTransaction,
    WebhookEvent,
    create_database,
)
from .utils import parse_date, parse_utc_datetime


def process_delivery(session: Session, payload: object) -> str:
    event = _validate_event(payload)
    session.add(
        WebhookEvent(
            object_type=event["object"],
            object_id=event["id"],
            payload=payload,
        )
    )
    # SQLite takes its write lock here, before the last-write-wins read.
    session.flush()

    model = BalanceTransaction if event["object"] in {"charge", "refund"} else Payout
    existing = session.get(model, event["id"])
    if existing is not None and existing.source_created_at >= event["created"]:
        session.commit()
        return "stale"

    if event["object"] == "payout":
        _store_payout(session, event, existing)
    else:
        _store_balance_transaction(session, event, existing)
    session.commit()
    return "updated" if existing is not None else "created"


def _validate_event(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("webhook body must be a JSON object")
    event = dict(payload)
    object_id = event.get("id")
    object_type = event.get("object")
    if not isinstance(object_id, str) or not object_id:
        raise ValueError("id must be a non-empty string")
    if object_type not in {"charge", "refund", "payout"}:
        raise ValueError("object must be charge, refund, or payout")
    event["created"] = parse_utc_datetime(event.get("created"))
    event["amount"] = _integer(event.get("amount"), "amount", minimum=1)
    currency = event.get("currency")
    if not isinstance(currency, str) or not currency:
        raise ValueError("currency must be a non-empty string")
    event["currency"] = currency.upper()
    if event["currency"] != "GBP":
        raise ValueError("currency must be GBP")

    if object_type == "payout":
        status = event.get("status")
        if status not in {"paid", "unpaid", "processing"}:
            raise ValueError("payout status must be paid, unpaid, or processing")
        event["arrival_date"] = parse_date(event.get("arrival_date"), "arrival_date")
        references = event.get("included_balance_transactions")
        if not isinstance(references, list) or not all(
            isinstance(reference, str) and reference for reference in references
        ):
            raise ValueError("included_balance_transactions must be a list of IDs")
        if not references:
            raise ValueError("included_balance_transactions must not be empty")
        if len(references) != len(set(references)):
            raise ValueError("included_balance_transactions must not contain duplicates")
        return event

    event["available_on"] = parse_date(event.get("available_on"), "available_on")
    fees = event.get("fee_details", [])
    if not isinstance(fees, list):
        raise ValueError("fee_details must be a list")
    totals = {"stripe_fee": 0, "application_fee": 0}
    for fee in fees:
        if not isinstance(fee, dict) or not isinstance(fee.get("type"), str):
            raise ValueError("each fee detail must include a type")
        amount = _integer(fee.get("amount"), "fee amount")
        if fee["type"] in totals:
            totals[fee["type"]] += amount
    event.update(totals)

    net = _integer(event.get("net"), "net")
    expected_net = (
        -event["amount"] - event["stripe_fee"] - event["application_fee"]
        if object_type == "refund"
        else event["amount"] - event["stripe_fee"] - event["application_fee"]
    )
    if net != expected_net:
        raise ValueError(f"net must equal {expected_net} for the supplied amount and fees")
    event["net"] = net

    if object_type == "charge":
        if event.get("status") not in {"succeeded", "pending", "failed"}:
            raise ValueError("charge status must be succeeded, pending, or failed")
        order_ref = event.get("order_ref")
        if order_ref is not None and not isinstance(order_ref, str):
            raise ValueError("order_ref must be a string")
    else:
        charge = event.get("charge")
        if not isinstance(charge, str) or not charge:
            raise ValueError("refund charge must be a non-empty string")
    return event


def _integer(value: object, field: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} must be at least {minimum}")
    return value


def _store_balance_transaction(
    session: Session,
    event: dict[str, Any],
    transaction: BalanceTransaction | None,
) -> None:
    is_refund = event["object"] == "refund"
    if transaction is not None and transaction.type != event["object"]:
        raise ValueError("an existing balance transaction cannot change object type")
    reference = event.get("charge") if is_refund else None
    previous_reference = transaction.reference_charge_id if transaction else None
    values = {
        "type": event["object"],
        "order_reference": event.get("order_ref"),
        "reference_charge_id": reference,
        "charge_id": None,
        "currency": event["currency"],
        "amount": event["amount"],
        "status": event.get("status"),
        "stripe_fee": event["stripe_fee"],
        "application_fee": event["application_fee"],
        "net": event["net"],
        "available_on": event["available_on"],
        "source_created_at": event["created"],
    }
    if transaction is None:
        transaction = BalanceTransaction(id=event["id"], **values)
        session.add(transaction)
    else:
        for name, value in values.items():
            setattr(transaction, name, value)
    session.flush()

    charge_ids = {transaction.id} if transaction.type == "charge" else {
        charge_id for charge_id in (previous_reference, reference) if charge_id
    }
    reconciled_refund_ids = _reconcile_refunds(session, charge_ids)
    session.execute(
        update(PayoutTransaction)
        .where(PayoutTransaction.reference_transaction_id == transaction.id)
        .values(balance_transaction_id=transaction.id)
    )
    session.flush()
    _reconcile_payouts_for_transactions(
        session, {transaction.id, *reconciled_refund_ids}
    )


def _reconcile_refunds(session: Session, charge_ids: set[str]) -> set[str]:
    affected_refund_ids: set[str] = set()
    for charge_id in charge_ids:
        charge = session.get(BalanceTransaction, charge_id)
        refunds = session.scalars(
            select(BalanceTransaction).where(
                BalanceTransaction.type == "refund",
                BalanceTransaction.reference_charge_id == charge_id,
            )
        ).all()
        affected_refund_ids.update(refund.id for refund in refunds)

        matching_refund_total = sum(
            refund.amount
            for refund in refunds
            if charge and refund.currency == charge.currency
        )
        charge_is_valid = bool(
            charge
            and charge.type == "charge"
            and charge.status == "succeeded"
            and matching_refund_total <= charge.amount
        )
        for refund in refunds:
            refund.charge_id = (
                charge.id
                if charge_is_valid and refund.currency == charge.currency
                else None
            )
    session.flush()
    return affected_refund_ids


def _transaction_is_reportable(transaction: BalanceTransaction) -> bool:
    if transaction.type == "charge":
        return transaction.status == "succeeded"
    return transaction.charge_id is not None


def _reconcile_payouts_for_transactions(
    session: Session, transaction_ids: set[str]
) -> None:
    if not transaction_ids:
        return
    payout_ids = session.scalars(
        select(PayoutTransaction.payout_id)
        .where(PayoutTransaction.reference_transaction_id.in_(transaction_ids))
        .distinct()
    ).all()
    for payout_id in payout_ids:
        payout = session.get(Payout, payout_id)
        if payout:
            _reconcile_payout(session, payout)


def _reconcile_payout(session: Session, payout: Payout) -> None:
    links = session.scalars(
        select(PayoutTransaction).where(PayoutTransaction.payout_id == payout.id)
    ).all()
    transactions = [
        session.get(BalanceTransaction, link.balance_transaction_id)
        if link.balance_transaction_id
        else None
        for link in links
    ]
    payout.is_reconciled = bool(links) and all(
        transaction
        and _transaction_is_reportable(transaction)
        and transaction.currency == payout.currency
        for transaction in transactions
    ) and sum(
        transaction.net for transaction in transactions if transaction
    ) == payout.amount


def _store_payout(
    session: Session, event: dict[str, Any], payout: Payout | None
) -> None:
    assigned_reference = session.scalar(
        select(PayoutTransaction.reference_transaction_id).where(
            PayoutTransaction.reference_transaction_id.in_(
                event["included_balance_transactions"]
            ),
            PayoutTransaction.payout_id != event["id"],
        ).limit(1)
    )
    if assigned_reference:
        raise ValueError(
            f"balance transaction {assigned_reference} is already assigned to a payout"
        )

    values = {
        "amount": event["amount"],
        "currency": event["currency"],
        "status": event["status"],
        "is_reconciled": False,
        "source_created_at": event["created"],
        "arrival_date": event["arrival_date"],
    }
    if payout is None:
        payout = Payout(id=event["id"], **values)
        session.add(payout)
    else:
        for name, value in values.items():
            setattr(payout, name, value)
    session.flush()
    session.execute(delete(PayoutTransaction).where(PayoutTransaction.payout_id == payout.id))
    for reference in event["included_balance_transactions"]:
        resolved = session.get(BalanceTransaction, reference)
        session.add(
            PayoutTransaction(
                payout_id=payout.id,
                reference_transaction_id=reference,
                balance_transaction_id=resolved.id if resolved else None,
            )
        )
    session.flush()
    _reconcile_payout(session, payout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest webhook fixture files")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./ticket_tailor.db"),
    )
    args = parser.parse_args()

    engine, session_factory = create_database(args.database_url)
    Base.metadata.create_all(engine)
    summary = {"created": 0, "updated": 0, "stale": 0, "invalid": 0}
    with session_factory() as session:
        for path in args.files:
            with path.open(encoding="utf-8") as fixture:
                records = json.load(fixture)
            if not isinstance(records, list):
                raise ValueError(f"{path} must contain a JSON array")
            for payload in records:
                try:
                    summary[process_delivery(session, payload)] += 1
                except ValueError as error:
                    session.rollback()
                    summary["invalid"] += 1
                    print(f"{path}: skipped invalid delivery: {error}")
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
