from datetime import datetime
import re

from opossum.opossum.models import POSInvoice, POSInvoiceItem


def convert_payload_to_POS_invoice(data: dict) -> POSInvoice:
    invoice_items = []
    line_index = 0

    invoice_item = _make_POS_invoice_item(data, line_index)
    invoice_items.append(invoice_item)
    while invoice_item:
        line_index += 1
        invoice_item = _make_POS_invoice_item(data, line_index)
        if invoice_item:
            invoice_items.append(invoice_item)

    return POSInvoice(
        # FIXME: check timezone
        posting_date=datetime.fromisoformat(data["completed_at"]),
        invoice_items=invoice_items,
    )


def _fetch_props(data, line_index):
    rv = {}
    pattern = re.compile(f"line_items\[{str(line_index)}\]\[(.*)\]")
    for k, v in data.items():
        if k.startswith(f"line_items[{str(line_index)}]"):
            match = pattern.match(k)
            rv[match.groups()[0]] = v
    return rv


def _make_POS_invoice_item(data: dict, line_index: int) -> POSInvoiceItem or None:
    item_data = _fetch_props(data, line_index)
    if not item_data:
        return None

    return POSInvoiceItem(
        qty=int(item_data["quantity"]), external_id=item_data["product_id"]
    )
