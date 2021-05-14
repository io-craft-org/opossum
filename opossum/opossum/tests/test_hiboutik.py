from unittest.mock import MagicMock, Mock

import pytest
from opossum.opossum.hiboutik import (HiboutikConnector, HiboutikStoreError,
                                      Product)
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
def matching_product(item):
    return Product(
        product_model="foo",
        products_ref_ext=item.code,
        product_price="6.4",
        product_vat=item.vat,
    )


@pytest.fixture
def another_matching_product(item):
    return Product(
        product_model="bar",
        products_ref_ext=item.code,
        product_price="7.30",
        product_vat=item.vat,
    )


@pytest.fixture
def some_products():
    return [
        Product("Test 1", "1.50", 1, "test-1"),
        Product("Test 2", "2.50", 1, "test-2"),
        Product("Test 3", "3.50", 1, "test-3"),
    ]


@pytest.fixture
def products_with_match(matching_product):
    return [
        Product("Test 1", "1.50", 1, "test-1"),
        Product("Test 2", "2.50", 1, "test-2"),
        matching_product,
        Product("Test 3", "3.50", 1, "test-3"),
    ]


def test_sync_item_create_product(connector, api):
    api.get_products.return_value = []
    api.post_product.return_value = 1

    item = Item(code="large-spoon", name="Spoon (large)", price="10.00", vat=1)
    connector.sync(item)
    assert api.get_products.called is True
    assert api.post_product.called is True


def test_sync_item_update_product(matching_product, item, connector, api):
    connector.find_product = MagicMock()
    connector.find_product.return_value = matching_product
    api.update_product.return_value = None

    connector.sync(item)

    assert connector.find_product.called is True
    assert api.update_product.called is True


def test_find_product(products_with_match, matching_product, item, connector, api):
    api.get_products.return_value = products_with_match

    assert connector.find_product(item) == matching_product
    assert api.get_products.called is True


def test_find_product_empty_store(item, connector, api):
    api.get_products.return_value = []

    assert connector.find_product(item) is None
    assert api.get_products.called is True


def test_find_product_not_found(some_products, item, connector, api):
    api.get_products.return_value = some_products

    assert connector.find_product(item) is None
    assert api.get_products.called is True


def test_find_product_multiple_matches_error(
    matching_product, another_matching_product, item, connector, api
):
    api.get_products.return_value = [matching_product, another_matching_product]

    with pytest.raises(HiboutikStoreError):
        connector.find_product(item)
