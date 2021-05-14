import datetime
from dataclasses import dataclass


@dataclass
class Item:
    """A proxy Item to hide ERPNext internals"""

    code: str
    name: str
    price: str
    vat: int
    external_id: str = ""


@dataclass
class POSInvoice:
    """An invoice received from an external POS"""

    posting_date: datetime.datetime
