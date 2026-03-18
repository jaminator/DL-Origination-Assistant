"""Tests for BizAPI match method selection logic."""

import pytest

from app.miner.enrichment.bizapi.rest_client import BizAPIRESTClient


@pytest.fixture
def client():
    return BizAPIRESTClient(
        base_url="https://test.bizapi.com/v1",
        username="testuser",
        password="testpass",
    )


def test_duns_is_highest_priority(client):
    methods = client._select_match_method(
        "Acme", duns="123", website="https://acme.com", state="TX",
    )
    assert methods[0][0] == "duns"
    assert methods[0][1] == {"DUNS": "123"}


def test_url_before_standard(client):
    methods = client._select_match_method("Acme", website="https://acme.com", state="TX")
    names = [m[0] for m in methods]
    assert names.index("url") < names.index("standard")


def test_standard_before_name(client):
    methods = client._select_match_method("Acme", state="TX")
    names = [m[0] for m in methods]
    assert names.index("standard") < names.index("name")


def test_name_always_included(client):
    methods = client._select_match_method("Acme")
    names = [m[0] for m in methods]
    assert "name" in names


def test_loose_is_last(client):
    methods = client._select_match_method("Acme", duns="123", website="x", state="TX", phone="555")
    assert methods[-1][0] == "loose"


def test_phone_included_when_provided(client):
    methods = client._select_match_method("Acme", phone="555-1234")
    names = [m[0] for m in methods]
    assert "phone" in names


def test_standard_body_includes_name_and_state(client):
    methods = client._select_match_method("Acme Corp", state="CA")
    standard = next(m for m in methods if m[0] == "standard")
    assert standard[1] == {"CompanyName": "Acme Corp", "State": "CA"}
