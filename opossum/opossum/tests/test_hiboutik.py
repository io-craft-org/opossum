from decimal import Decimal
from unittest.mock import Mock

import pytest
from opossum.opossum.hiboutik import (HiboutikConnector, Product,
                                      ProductAttribute)
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
