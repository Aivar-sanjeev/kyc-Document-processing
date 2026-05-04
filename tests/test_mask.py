from app.pipeline.mask import finalize_aadhaar_output_fields, mask_aadhaar_number, normalize_aadhaar_digits


def test_normalize_aadhaar_digits():
    assert normalize_aadhaar_digits("1234 5678 9012") == "123456789012"
    assert normalize_aadhaar_digits("123") is None


def test_mask_aadhaar_number():
    assert mask_aadhaar_number("1234 5678 9012") == "XXXX XXXX 9012"


def test_finalize_accepts_already_masked_display():
    fields = {"name": "Test", "aadhaar_number": "XXXX XXXX 9012"}
    out, masked = finalize_aadhaar_output_fields(fields)
    assert masked is True
    assert out["aadhaar_number"] == "XXXX XXXX 9012"


def test_finalize_masks_and_scrubs_address():
    fields = {
        "name": "Test",
        "aadhaar_number": "1234 5678 9012",
        "address": "A-1, pin 1234 5678 9012 near gate",
    }
    out, masked = finalize_aadhaar_output_fields(fields)
    assert masked is True
    assert out["aadhaar_number"] == "XXXX XXXX 9012"
    assert "9012" in out["address"]
    assert "123456789012" not in str(out)
