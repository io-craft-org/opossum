import datetime
from dataclasses import dataclass
from typing import List


@dataclass
class Item:
    """A proxy Item to hide ERPNext internals"""

    code: str
    name: str
    price: str
    vat: int
    is_stock_item: bool
    deactivated: bool = False
    external_id: str = ""
    stock_qty: int = 0


@dataclass
class POSInvoiceItem:
    """A sell item on a POS Invoice"""

    qty: int
    external_id: str
    code: str = ""
    # TODO: add price and tax


@dataclass
class POSInvoice:
    """An invoice received from an external POS"""

    posting_date: datetime.datetime
    invoice_items: List[POSInvoiceItem]
