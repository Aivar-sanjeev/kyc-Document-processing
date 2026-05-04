from datetime import date, timedelta

from app.pipeline.validate import validate_dl_expiry, validate_pan


def test_validate_pan_ok():
    ok, w = validate_pan("ABCDE1234F")
    assert ok and not w


def test_validate_pan_bad():
    ok, w = validate_pan("ABCD1234F")
    assert not ok


def test_validate_dl_expiry_future():
    future = (date.today() + timedelta(days=400)).isoformat()
    ok, w = validate_dl_expiry({"validity_to": future})
    assert ok
    assert "dl_expired" not in "".join(w)


def test_validate_dl_expiry_past():
    past = (date.today() - timedelta(days=10)).isoformat()
    ok, w = validate_dl_expiry({"validity_to": past})
    assert not ok
