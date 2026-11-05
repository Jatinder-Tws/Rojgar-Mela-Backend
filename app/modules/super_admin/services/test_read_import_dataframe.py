"""Regression: bulk import must accept Excel-locale CSV (;) and recover from tokenize traps."""

from app.modules.super_admin.services.super_admin_bulk_import import read_import_dataframe


def test_read_comma_csv():
    raw = (
        b"first_name,last_name,email,phone\n"
        b"John,Doe,john@example.com,9876543210\n"
    )
    df = read_import_dataframe(raw, filename="seekers.csv")
    assert list(df.columns) == ["first_name", "last_name", "email", "phone"]
    assert len(df) == 1


def test_read_semicolon_csv_with_comma_inside_field():
    # Classic Excel (EU/IN locale) export: ; separator, commas inside cells.
    # Default pandas comma parser → "Expected 1 fields in line N, saw 2".
    raw = (
        "first_name;last_name;email;phone;address\n"
        "Asha;Sharma;asha@example.com;9876543210;Delhi\n"
        "Ravi;Kumar;ravi@example.com;9876543211;Mumbai\n"
        "Neha;Singh;neha@example.com;9876543212;Pune, Maharashtra\n"
    ).encode("utf-8")
    df = read_import_dataframe(raw, filename="seekers.csv")
    assert len(df.columns) >= 4
    assert len(df) == 3
    assert "address" in list(df.columns) or df.shape[1] == 5


def test_read_rejects_single_column_blob():
    raw = b"notes\nline one\nline two\nline three\n"
    try:
        read_import_dataframe(raw, filename="notes.csv")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        msg = str(exc).lower()
        assert "multi-column" in msg or "could not read" in msg
