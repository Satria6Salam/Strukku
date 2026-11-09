from datetime import datetime

import pytest

from app.integrations.parser.regex_parser import RegexReceiptParser, parse_money


@pytest.mark.parametrize(
    "text,expected",
    [
        ("22.500", 22500), ("22,500", 22500), ("1.250.000", 1250000), ("22.500,00", 22500),
        ("22,500.00", 22500), ("Rp15.000", 15000), ("15000", 15000), ("abc", None),
    ],
)
def test_parse_money(text, expected):
    assert parse_money(text) == expected


def test_two_line_items_and_text_date():
    text = """ALFAMART
Tgl. 03 Nov 2026 19:05
VITAMIN C 10 TABLET
  2 x 15.000   30.000
AQUA 600ML      4.000
SUBTOTAL       34.000
DISKON         -2.000
TOTAL BELANJA  32.000
"""
    parsed = RegexReceiptParser().parse(text)
    assert parsed.merchant_name == "ALFAMART"
    assert parsed.transaction_date == datetime(2026, 11, 3, 19, 5)
    assert parsed.total_amount == 32000
    assert [(i.name, i.quantity, i.price) for i in parsed.items] == [
        ("VITAMIN C 10 TABLET", 2, 30000),
        ("AQUA 600ML", 1, 4000),
    ]


def test_ignores_payment_lines():
    parsed = RegexReceiptParser().parse("TOKO A\nGULA 1KG 15.000\nTOTAL 15.000\nTUNAI 20.000\nKEMBALI 5.000\n")
    assert len(parsed.items) == 1 and parsed.total_amount == 15000
