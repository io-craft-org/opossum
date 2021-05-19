from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from opossum.opossum.doctype.hiboutik_settings.utils import (
    convert_payload_to_POS_invoice,
)
from opossum.opossum.hiboutik import (
    HiboutikConnector,
    Product,
    ProductAttribute,
)
from opossum.opossum.models import Item


@pytest.fixture
def api():
    return Mock(name="mocked_api")


@pytest.fixture
def connector(api):
    return HiboutikConnector(api)


@pytest.fixture
def item():
    return Item(code="large-spoon", name="Spoon (large)", price="10.00", vat=1)


@pytest.fixture
def synced_item(item):
    si = Item(**item.__dict__)
    si.external_id = "27"
    return si


@pytest.fixture
def matching_outdated_product(synced_item):
    return Product(
        product_model=synced_item.name + " outdated",
        product_price=str(Decimal(synced_item.price) + Decimal(1.24)),
        product_vat=synced_item.vat,
        product_id=synced_item.external_id,
    )


def test_sync_item_create_product(item, connector, api):
    new_product_id = 35
    api.post_product.return_value = new_product_id
    # TODO: prepare erpnext accessor mock

    connector.sync(item)

    assert api.post_product.called is True
    # TODO: assert eprnext accessor is called with external_id new_product_id


def test_sync_item_update_product(
    matching_outdated_product, synced_item, connector, api
):
    api.get_product.return_value = matching_outdated_product

    connector.sync(synced_item)

    api.get_product.assert_called_with(synced_item.external_id)
    api.update_product.assert_called_with(
        synced_item.external_id,
        [
            ProductAttribute("product_model", synced_item.name),
            ProductAttribute("product_price", synced_item.price),
        ],
    )


def test_pos_utils_convert_sale_to_invoice():
    payload = {
        "completed_at": "2021-04-26 15:06:34",
        "line_items[0][product_id]": "3",
        "line_items[0][quantity]": "2",
        "line_items[1][product_id]": "37",
        "line_items[1][quantity]": "1",
    }

    pos_invoice = convert_payload_to_POS_invoice(payload)

    assert pos_invoice.posting_date == datetime(2021, 4, 26, 15, 6, 34)
    assert len(pos_invoice.invoice_items) == 2
    item1 = pos_invoice.invoice_items[0]
    assert item1.external_id == "3"
    assert item1.qty == 2
    item2 = pos_invoice.invoice_items[1]
    assert item2.external_id == "37"
    assert item2.qty == 1
