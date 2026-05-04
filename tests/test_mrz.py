from app.pipeline.mrz import build_td3_second_line, mrz_matches_extracted, parse_td3_second_line


def test_parse_td3_second_line_roundtrip():
    line = build_td3_second_line(
        doc9="Z1234567",
        nationality="IND",
        dob_yymmdd="900412",
        sex="F",
        expiry_yymmdd="350401",
    )
    assert len(line) == 44
    parsed = parse_td3_second_line(line)
    assert parsed is not None
    assert parsed.document_number.replace("<", "") == "Z1234567".replace("<", "")
    assert parsed.nationality == "IND"


def test_mrz_matches_extracted_ok():
    line = build_td3_second_line(
        doc9="Z1234567",
        nationality="IND",
        dob_yymmdd="900412",
        sex="F",
        expiry_yymmdd="350401",
    )
    ok, w = mrz_matches_extracted(
        line,
        passport_number="Z1234567",
        dob_iso="1990-04-12",
        expiry_iso="2035-04-01",
        nationality="IND",
    )
    assert ok is True
    assert w == []
