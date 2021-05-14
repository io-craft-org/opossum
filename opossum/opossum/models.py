import datetime
from dataclasses import dataclass


@dataclass
class Item:
    """An proxy Item to hide ERPNext internals"""

    code: str
    name: str
    price: str
    vat: int


@dataclass
class POSInvoice:
    """An invoice received from an external POS"""

    posting_date: datetime.datetime
