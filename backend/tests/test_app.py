import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import create_app
from src import utils
from src.db import BalanceTransaction, Payout, PayoutTransaction, WebhookEvent
from src.webhook import process_delivery


@pytest.fixture
def app():
    return create_app("sqlite://")


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def charge(
    object_id: str = "ch_1",
    created: str = "2026-09-01T10:00:00Z",
    amount: int = 1_000,
    status: str = "succeeded",
    available_on: str = "2026-09-02",
) -> dict:
    stripe_fee = 20
    application_fee = 50
    return {
        "id": object_id,
        "object": "charge",
        "created": created,
        "amount": amount,
        "currency": "gbp",
        "status": status,
        "order_ref": "TT-1",
        "fee_details": [
            {"type": "application_fee", "amount": application_fee},
            {"type": "stripe_fee", "amount": stripe_fee},
        ],
        "net": amount - stripe_fee - application_fee,
        "available_on": available_on,
    }


def refund(
    object_id: str = "re_1",
    target: str = "ch_1",
    amount: int = 500,
    created: str = "2026-09-01T09:00:00Z",
) -> dict:
    return {
        "id": object_id,
        "object": "refund",
        "created": created,
        "charge": target,
        "amount": amount,
        "currency": "gbp",
        "fee_details": [
            {"type": "stripe_fee", "amount": -10},
            {"type": "application_fee", "amount": -25},
        ],
        "net": -amount + 35,
        "available_on": "2026-09-02",
    }


def payout(
    object_id: str = "po_1",
    reference: str = "ch_1",
    amount: int = 930,
    created: str = "2026-09-01T08:00:00Z",
    references: list[str] | None = None,
) -> dict:
    return {
        "id": object_id,
        "object": "payout",
        "created": created,
        "amount": amount,
        "currency": "gbp",
        "status": "unpaid",
        "arrival_date": "2026-09-02",
        "included_balance_transactions": references or [reference],
    }


def test_ingestion_upsert_arithmetic_and_delivery_log(client: TestClient, app) -> None:
    original = charge()
    assert client.post("/api/webhooks", json=original).status_code == 201
    assert client.post("/api/webhooks", json=original).status_code == 409

    newer = charge(created="2026-09-01T11:00:00+01:00", amount=1_200)
    newer["fee_details"].reverse()
    response = client.post("/api/webhooks", json=newer)
    assert response.status_code == 409  # The same UTC instant is stale.

    newer["created"] = "2026-09-01T10:00:01Z"
    response = client.post("/api/webhooks", json=newer)
    assert response.status_code == 200
    assert response.json() == {"outcome": "updated"}

    with app.state.session_factory() as session:
        transaction = session.get(BalanceTransaction, "ch_1")
        assert transaction.amount == 1_200
        assert transaction.stripe_fee == 20
        assert transaction.application_fee == 50
        assert transaction.net == 1_130
        assert transaction.order_reference == "TT-1"
        assert transaction.source_created_at == datetime(2026, 9, 1, 10, 0, 1, tzinfo=UTC)
        assert session.scalar(select(func.count()).select_from(WebhookEvent)) == 4


def test_rejects_incorrect_net_and_empty_payout(client: TestClient) -> None:
    invalid_charge = charge()
    invalid_charge["net"] = 1
    assert client.post("/api/webhooks", json=invalid_charge).status_code == 422

    invalid_payout = payout()
    invalid_payout["included_balance_transactions"] = []
    assert client.post("/api/webhooks", json=invalid_payout).status_code == 422

    wrong_currency = charge("ch_usd")
    wrong_currency["currency"] = "usd"
    assert client.post("/api/webhooks", json=wrong_currency).status_code == 422


def test_out_of_order_refund_and_payout_reconcile(
    client: TestClient, app
) -> None:
    assert client.post("/api/webhooks", json=refund()).status_code == 201
    assert client.post("/api/webhooks", json=payout()).status_code == 201

    with app.state.session_factory() as session:
        stored_refund = session.get(BalanceTransaction, "re_1")
        stored_payout = session.get(Payout, "po_1")
        payout_link = session.scalar(select(PayoutTransaction))
        assert stored_refund.charge_id is None
        assert stored_payout.is_reconciled is False
        assert payout_link.balance_transaction_id is None

    refunds = client.get("/api/transactions?kind=refund").json()["items"]
    payouts = client.get("/api/payouts").json()["items"]
    assert refunds[0]["reconciled"] is False
    assert refunds[0]["included_in_reporting"] is False
    assert payouts[0]["reconciled"] is False

    assert client.post("/api/webhooks", json=charge()).status_code == 201
    with app.state.session_factory() as session:
        stored_refund = session.get(BalanceTransaction, "re_1")
        stored_payout = session.get(Payout, "po_1")
        payout_link = session.scalar(select(PayoutTransaction))
        assert stored_refund.charge_id == "ch_1"
        assert stored_payout.is_reconciled is True
        assert payout_link.balance_transaction_id == "ch_1"

    refunds = client.get("/api/transactions?kind=refund").json()["items"]
    payouts = client.get("/api/payouts").json()["items"]
    assert refunds[0]["reconciled"] is True
    assert refunds[0]["order_reference"] == "TT-1"
    assert refunds[0]["net"] == -465
    assert payouts[0]["reconciled"] is True


def test_pending_and_failed_charges_are_listed_but_not_reported(client: TestClient) -> None:
    for payload in (
        charge("ch_ok"),
        charge("ch_pending", status="pending"),
        charge("ch_failed", status="failed"),
    ):
        assert client.post("/api/webhooks", json=payload).status_code == 201

    transactions = client.get("/api/transactions?kind=sale&page_size=100").json()
    assert transactions["total"] == 3
    included = {item["id"]: item["included_in_reporting"] for item in transactions["items"]}
    assert included == {"ch_ok": True, "ch_pending": False, "ch_failed": False}
    assert client.get("/api/reports/overview").json()["summary"]["net_revenue"] == 930


def test_payout_requires_reportable_transactions(client: TestClient, app) -> None:
    assert client.post(
        "/api/webhooks", json=charge("ch_failed", status="failed")
    ).status_code == 201
    assert client.post(
        "/api/webhooks", json=payout(reference="ch_failed")
    ).status_code == 201

    with app.state.session_factory() as session:
        assert session.get(Payout, "po_1").is_reconciled is False

    payout_item = client.get("/api/payouts").json()["items"][0]
    assert payout_item["reconciled"] is False
    assert client.get("/api/reports/overview").json()["summary"] == {
        "net_revenue": 0,
        "payouts_completed": 0,
        "available_to_payout": 0,
        "pending": 0,
    }


def test_transaction_cannot_be_assigned_to_multiple_payouts(
    client: TestClient,
) -> None:
    assert client.post("/api/webhooks", json=charge()).status_code == 201
    assert client.post("/api/webhooks", json=payout("po_1")).status_code == 201
    response = client.post("/api/webhooks", json=payout("po_2"))
    assert response.status_code == 422


def test_over_refunded_charge_is_excluded(client: TestClient, app) -> None:
    assert client.post("/api/webhooks", json=charge()).status_code == 201
    assert client.post(
        "/api/webhooks", json=refund("re_1", amount=700)
    ).status_code == 201
    assert client.post(
        "/api/webhooks", json=refund("re_2", amount=400)
    ).status_code == 201

    with app.state.session_factory() as session:
        stored_refunds = session.scalars(
            select(BalanceTransaction).where(BalanceTransaction.type == "refund")
        ).all()
        assert all(item.charge_id is None for item in stored_refunds)

    refunds = client.get("/api/transactions?kind=refund").json()["items"]
    assert all(item["reconciled"] is False for item in refunds)
    report = client.get("/api/reports/overview").json()
    assert report["summary"]["net_revenue"] == 930
    assert report["excluded_unreconciled_count"] == 2


def test_newer_charge_update_reconciles_linked_payout(client: TestClient, app) -> None:
    assert client.post("/api/webhooks", json=charge()).status_code == 201
    assert client.post("/api/webhooks", json=payout()).status_code == 201

    with app.state.session_factory() as session:
        assert session.get(Payout, "po_1").is_reconciled is True

    failed_charge = charge(created="2026-09-01T10:00:01Z", status="failed")
    assert client.post("/api/webhooks", json=failed_charge).status_code == 200

    with app.state.session_factory() as session:
        assert session.get(Payout, "po_1").is_reconciled is False


def test_newer_payout_update_recalculates_reconciliation(
    client: TestClient, app
) -> None:
    assert client.post("/api/webhooks", json=charge()).status_code == 201
    assert client.post("/api/webhooks", json=payout()).status_code == 201

    mismatched = payout(amount=900, created="2026-09-01T08:00:01Z")
    assert client.post("/api/webhooks", json=mismatched).status_code == 200
    with app.state.session_factory() as session:
        assert session.get(Payout, "po_1").is_reconciled is False

    corrected = payout(created="2026-09-01T08:00:02Z")
    assert client.post("/api/webhooks", json=corrected).status_code == 200
    with app.state.session_factory() as session:
        assert session.get(Payout, "po_1").is_reconciled is True


def test_newer_refund_update_restores_reconciliation(client: TestClient, app) -> None:
    assert client.post("/api/webhooks", json=charge()).status_code == 201
    assert client.post(
        "/api/webhooks", json=refund("re_1", amount=700)
    ).status_code == 201
    assert client.post(
        "/api/webhooks", json=refund("re_2", amount=400)
    ).status_code == 201

    corrected = refund(
        "re_2", amount=300, created="2026-09-01T09:00:01Z"
    )
    assert client.post("/api/webhooks", json=corrected).status_code == 200
    with app.state.session_factory() as session:
        stored_refunds = session.scalars(
            select(BalanceTransaction).where(BalanceTransaction.type == "refund")
        ).all()
        assert all(item.charge_id == "ch_1" for item in stored_refunds)


def test_payout_reconciles_after_charge_and_refund_arrive(
    client: TestClient, app
) -> None:
    combined_payout = payout(
        amount=465, references=["ch_1", "re_1"]
    )
    assert client.post("/api/webhooks", json=combined_payout).status_code == 201
    assert client.post("/api/webhooks", json=refund()).status_code == 201
    with app.state.session_factory() as session:
        assert session.get(Payout, "po_1").is_reconciled is False

    assert client.post("/api/webhooks", json=charge()).status_code == 201
    with app.state.session_factory() as session:
        assert session.get(Payout, "po_1").is_reconciled is True


def test_fixture_outcomes_and_reporting_totals(
    app, client: TestClient, monkeypatch
) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 3, 12, 0, tzinfo=UTC)

    monkeypatch.setattr(utils, "datetime", FixedDateTime)
    fixture_root = Path(__file__).parents[2]
    outcomes = []
    with app.state.session_factory() as session:
        for name in ("records.json", "records2.json"):
            with (fixture_root / name).open(encoding="utf-8") as fixture:
                for payload in json.load(fixture):
                    outcomes.append(process_delivery(session, payload))

    assert outcomes.count("created") == 82
    assert outcomes.count("stale") == 2
    report = client.get("/api/reports/overview?period=all_time&timezone=UTC").json()
    assert report["summary"] == {
        "net_revenue": 126_267,
        "payouts_completed": 49_291,
        "available_to_payout": 5_406,
        "pending": 71_570,
    }
    assert report["revenue_breakdown"] == {
        "gross_sales": 146_400,
        "refunds": 11_950,
        "ticket_tailor_fees": 4_719,
        "stripe_fees": 3_464,
        "net_revenue": 126_267,
    }
    assert report["excluded_unreconciled_count"] == 0
    assert [item["id"] for item in report["payout_schedule"]] == [
        "po_1001",
        "po_1002",
        "po_1003",
    ]


def test_periods_use_browser_timezone_and_full_calendar_ranges(monkeypatch) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 3, 0, 30, tzinfo=UTC)

    monkeypatch.setattr(utils, "datetime", FixedDateTime)
    los_angeles = utils.get_period("today", "America/Los_Angeles")
    tokyo = utils.get_period("today", "Asia/Tokyo")
    this_week = utils.get_period("this_week", "UTC")
    this_month = utils.get_period("this_month", "UTC")

    assert los_angeles.as_dict()["start_date"] == "2026-09-02"
    assert tokyo.as_dict()["start_date"] == "2026-09-03"
    assert this_week.as_dict()["start_date"] == "2026-08-31"
    assert this_week.as_dict()["end_date_exclusive"] == "2026-09-07"
    assert this_month.as_dict()["end_date_exclusive"] == "2026-10-01"


def test_transaction_period_filter_is_inclusive_exclusive(
    client: TestClient, monkeypatch
) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 3, 12, 0, tzinfo=UTC)

    monkeypatch.setattr(utils, "datetime", FixedDateTime)
    assert client.post(
        "/api/webhooks", json=charge("ch_today", available_on="2026-09-03")
    ).status_code == 201
    assert client.post(
        "/api/webhooks", json=charge("ch_next", available_on="2026-09-04")
    ).status_code == 201

    response = client.get(
        "/api/transactions?kind=sale&period=today&timezone=UTC&page_size=100"
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["ch_today"]
