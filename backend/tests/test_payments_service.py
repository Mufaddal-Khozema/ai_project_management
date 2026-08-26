from datetime import datetime
from types import SimpleNamespace

import pytest
import stripe
from litestar.exceptions import HTTPException

from services import payments as svc


TEST_PLANS = [
    {
        "id": "starter",
        "name": "Starter",
        "price_monthly": 4900,
        "price_yearly": 49000,
        "price_id_monthly": "price_starter_month",
        "price_id_yearly": "price_starter_year",
    },
    {
        "id": "professional",
        "name": "Professional",
        "price_monthly": 14900,
        "price_yearly": 149000,
        "price_id_monthly": "price_prof_month",
        "price_id_yearly": "price_prof_year",
    },
]


@pytest.fixture
def plans(monkeypatch):
    monkeypatch.setattr(svc, "PLANS", TEST_PLANS)
    return TEST_PLANS


def _user(user_id=1):
    return {"id": user_id, "email": "a@b.com"}


def _sub_row(**overrides):
    row = {
        "id": 1,
        "user_id": 1,
        "stripe_customer_id": "cus_1",
        "stripe_subscription_id": "sub_123",
        "price_id": "price_month",
        "plan_id": "professional",
        "billing_interval": "monthly",
        "status": "active",
        "cancel_at_period_end": False,
    }
    row.update(overrides)
    return row


def _price(id, interval):
    return SimpleNamespace(id=id, interval=interval)


def _stripe_sub(**overrides):
    sub = SimpleNamespace(
        id="sub_123",
        customer="cus_1",
        status="active",
        cancel_at_period_end=False,
        current_period_end=2000000000,
        trial_end=None,
        created=1900000000,
        items=SimpleNamespace(data=[SimpleNamespace(price=_price("price_prof_month", "month"))]),
        metadata={"email": "a@b.com"},
    )
    for k, v in overrides.items():
        setattr(sub, k, v)
    return sub


class _MethodItemsSub:
    """Mirrors real stripe.Subscription where `items` is a callable (list method)."""

    def __init__(self, price_id):
        self._price_id = price_id
        self.id = "sub_123"
        self.customer = "cus_1"
        self.status = "active"
        self.cancel_at_period_end = False
        self.current_period_end = 2000000000
        self.trial_end = None
        self.created = 1900000000
        self.metadata = {"email": "a@b.com"}
        self._items = [{"price": {"id": price_id}}]

    def items(self):  # callable, like stripe.Subscription.items
        return dict_items(self._items)

    def __getitem__(self, key):
        if key == "items":
            return SimpleNamespace(data=[SimpleNamespace(price=SimpleNamespace(id=self._price_id))])
        raise KeyError(key)

    def __contains__(self, key):
        return key == "items"


class dict_items(list):
    pass


# ─── price id extraction (regression: items is a method on this Stripe lib) ──

def test_price_id_from_subscription_method_items():
    sub = _MethodItemsSub("price_prof_month")
    assert svc._price_id_from_subscription(sub) == "price_prof_month"


def test_price_id_from_subscription_attribute_items():
    sub = _stripe_sub()
    assert svc._price_id_from_subscription(sub) == "price_prof_month"


def test_price_id_from_subscription_empty_items():
    sub = _stripe_sub(items=SimpleNamespace(data=[]))
    assert svc._price_id_from_subscription(sub) == ""


# ─── get_current_subscription ─────────────────────────────────────────────────

def test_current_free_plan_when_no_row(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: None)
    result = svc.get_current_subscription("a@b.com")
    assert result["plan_id"] == "free"
    assert result["plan_name"] == "Free"
    assert result["status"] == "free"
    assert result["price"] == 0


def test_current_user_not_found(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: None)
    with pytest.raises(HTTPException) as exc:
        svc.get_current_subscription("ghost@b.com")
    assert exc.value.status_code == 404


def test_current_maps_active_subscription(plans, monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(svc.stripe.Subscription, "retrieve", lambda sid: _stripe_sub())
    result = svc.get_current_subscription("a@b.com")
    assert result["plan_id"] == "professional"
    assert result["status"] == "active"
    assert result["price"] == 14900
    assert result["billing_interval"] == "monthly"
    assert result["current_period_end"] == datetime.fromtimestamp(2000000000)


def test_current_trialing(monkeypatch):
    sub = _stripe_sub(status="trialing", trial_end=2100000000)
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(svc.stripe.Subscription, "retrieve", lambda sid: sub)
    result = svc.get_current_subscription("a@b.com")
    assert result["status"] == "trialing"
    assert result["trial_end"] == datetime.fromtimestamp(2100000000)


def test_current_active_with_cancel_at_period_end_is_canceled(monkeypatch):
    sub = _stripe_sub(cancel_at_period_end=True)
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(svc.stripe.Subscription, "retrieve", lambda sid: sub)
    result = svc.get_current_subscription("a@b.com")
    assert result["status"] == "canceled"
    assert result["cancel_at_period_end"] is True


def test_current_stripe_error_502(monkeypatch):
    class _StripeError(stripe.StripeError):
        pass

    def boom(sid):
        raise _StripeError("down")

    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(svc.stripe.Subscription, "retrieve", boom)
    with pytest.raises(HTTPException) as exc:
        svc.get_current_subscription("a@b.com")
    assert exc.value.status_code == 502


# ─── cancel_subscription ──────────────────────────────────────────────────────

def test_cancel_happy_path(monkeypatch):
    modified = _stripe_sub(cancel_at_period_end=True)
    updated = {}

    def fake_modify(sid, cancel_at_period_end):
        return modified

    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(svc.stripe.Subscription, "modify", fake_modify)
    monkeypatch.setattr(svc.payment_repo, "update", lambda sid, values: updated.update(values) or {})
    result = svc.cancel_subscription("a@b.com")
    assert result["status"] == "canceled"
    assert result["cancel_at_period_end"] is True
    assert result["effective_end"] == datetime.fromtimestamp(2000000000)
    assert updated["status"] == "canceled"
    assert updated["cancel_at_period_end"] is True


def test_cancel_no_subscription_404(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: None)
    with pytest.raises(HTTPException) as exc:
        svc.cancel_subscription("a@b.com")
    assert exc.value.status_code == 404


def test_cancel_already_cancelled_409(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row(cancel_at_period_end=True))
    with pytest.raises(HTTPException) as exc:
        svc.cancel_subscription("a@b.com")
    assert exc.value.status_code == 409


def test_cancel_stripe_error_502(monkeypatch):
    class _StripeError(stripe.StripeError):
        pass

    def boom(sid, cancel_at_period_end):
        raise _StripeError("down")

    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(svc.stripe.Subscription, "modify", boom)
    with pytest.raises(HTTPException) as exc:
        svc.cancel_subscription("a@b.com")
    assert exc.value.status_code == 502


# ─── list_invoices ────────────────────────────────────────────────────────────

def _stripe_invoice(**overrides):
    inv = SimpleNamespace(
        id="in_1",
        number="INV-001",
        amount_paid=14900,
        currency="usd",
        status="paid",
        created=2000000000,
        hosted_invoice_url="https://stripe.com/hosted",
        invoice_pdf="https://stripe.com/pdf",
    )
    for k, v in overrides.items():
        setattr(inv, k, v)
    return inv


def test_list_invoices_maps_and_sorts_desc(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(
        svc.stripe.Invoice,
        "list",
        lambda customer, limit: SimpleNamespace(
            data=[_stripe_invoice(id="in_old", created=1000000000), _stripe_invoice(id="in_new", created=2000000000)]
        ),
    )
    result = svc.list_invoices("a@b.com")
    assert [i["id"] for i in result] == ["in_new", "in_old"]
    assert result[0]["amount"] == 14900
    assert result[0]["hosted_invoice_url"] == "https://stripe.com/hosted"


def test_list_invoices_zero_amount_without_pdf(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: _sub_row())
    monkeypatch.setattr(
        svc.stripe.Invoice,
        "list",
        lambda customer, limit: SimpleNamespace(
            data=[_stripe_invoice(amount_paid=0, invoice_pdf=None, hosted_invoice_url=None, status="open")]
        ),
    )
    result = svc.list_invoices("a@b.com")
    assert result[0]["amount"] == 0
    assert result[0]["invoice_pdf"] is None


def test_list_invoices_no_subscription_404(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "find_by_user_id", lambda uid: None)
    with pytest.raises(HTTPException) as exc:
        svc.list_invoices("a@b.com")
    assert exc.value.status_code == 404


# ─── webhook subscription handlers ────────────────────────────────────────────

def test_handle_subscription_upsert(plans, monkeypatch):
    upserted = {}

    def fake_upsert(uid, values):
        upserted["uid"], upserted["values"] = uid, values

    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: _user())
    monkeypatch.setattr(svc.payment_repo, "upsert", fake_upsert)
    svc._handle_subscription_upsert(_stripe_sub())
    assert upserted["uid"] == 1
    assert upserted["values"]["stripe_subscription_id"] == "sub_123"
    assert upserted["values"]["stripe_customer_id"] == "cus_1"
    assert upserted["values"]["plan_id"] == "professional"


def test_handle_subscription_upsert_no_user_skips(monkeypatch):
    called = {"upsert": False}

    def fake_upsert(uid, values):
        called["upsert"] = True

    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: None)
    monkeypatch.setattr(svc.payment_repo, "upsert", fake_upsert)
    svc._handle_subscription_upsert(_stripe_sub())
    assert called["upsert"] is False


def test_handle_subscription_deleted(monkeypatch):
    updated = {}

    def fake_find(sid):
        return _sub_row()

    def fake_update(sid, values):
        updated["sid"], updated["values"] = sid, values
        return {}

    monkeypatch.setattr(svc.payment_repo, "find_by_subscription_id", fake_find)
    monkeypatch.setattr(svc.payment_repo, "update", fake_update)
    svc._handle_subscription_deleted(_stripe_sub())
    assert updated["sid"] == "sub_123"
    assert updated["values"]["status"] == "canceled"
    assert updated["values"]["cancel_at_period_end"] is True