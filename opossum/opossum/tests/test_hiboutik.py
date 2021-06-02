from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import Mock

import pytest

from opossum.opossum.doctype.hiboutik_settings.utils import (
    convert_payload_to_POS_invoice,
)
from opossum.opossum.hiboutik import (
    HiboutikConnector,
    Product,
    ProductAttribute,
    Webhook,
    Sale,
    SaleLineItem,
    ClosedSale,
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
    return Item(
        code="large-spoon",
        name="Spoon (large)",
        price="10.00",
        vat=1,
        deactivated=False,
    )


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
        product_vat=synced_item.vat + 1,
        product_arch=int(synced_item.deactivated),
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

    call_args, call_kwargs = api.update_product.call_args
    product_id_arg = (
        call_args[0] if len(call_args) >= 1 else call_kwargs["product_id"]
    )
    update_arg = call_args[1] if len(call_args) >= 2 else call_kwargs["update"]
    assert product_id_arg == synced_item.external_id
    for pa in [
        ProductAttribute("product_model", synced_item.name),
        ProductAttribute("product_price", synced_item.price),
        ProductAttribute("product_vat", str(synced_item.vat)),
    ]:
        assert pa in update_arg


class SyncItemTestCase(TestCase):
    def setUp(self) -> None:
        self.api = Mock(name="mocked_api")
        self.connector = HiboutikConnector(self.api)
        self.item = Item(
            code="large-spoon",
            name="Spoon (large)",
            price="10.00",
            vat=1,
            deactivated=False,
            external_id="42",
        )
        self.product = Product.create(self.item)

    def test_sync_item_propagate_activated(self):
        self.api.get_product.return_value = self.product
        self.item.deactivated = False
        self.product.product_arch = 1

        self.connector.sync(self.item)

        self.api.update_product.assert_called_once_with(
            self.item.external_id,
            [
                ProductAttribute("product_arch", "0"),
            ],
        )

    def test_sync_item_propagate_deactivated(self):
        self.api.get_product.return_value = self.product
        self.item.deactivated = True
        self.product.product_arch = 0

        self.connector.sync(self.item)

        self.api.update_product.assert_called_once_with(
            self.item.external_id,
            [
                ProductAttribute("product_arch", "1"),
            ],
        )


class SetSaleWebhookTestCase(TestCase):
    def setUp(self) -> None:
        self.api = Mock(name="mocked_api")
        self.connector = HiboutikConnector(self.api)
        self.callback_url = "http://doesnot.exi.st/callback"
        self.updated_callback_url = "http://stillnot.exi.st/webhook"
        self.connector_webhook = Webhook.create_connector_webhook(
            self.callback_url
        )
        self.updated_connector_webhook = Webhook.create_connector_webhook(
            self.updated_callback_url
        )
        self.some_webhooks = [
            Webhook(
                "Some Webhook 1",
                "http://doesnot.matt.er/callback1",
                "sale",
                "TEST1",
                webhook_id=11,
            ),
            Webhook(
                "Some Webhook 2",
                "http://doesnot.matt.er/callback2",
                "sale",
                "TEST2",
                webhook_id=12,
            ),
            Webhook(
                "Some Webhook 3",
                "http://doesnot.matt.er/callback3",
                "sale",
                "TEST3",
                webhook_id=13,
            ),
        ]
        self.webhooks_with_ours = self.some_webhooks.copy()
        self.webhooks_with_ours.insert(2, self.connector_webhook)

    def test_set_sale_webhook_creation(self):
        connector_webhook_id = 42
        self.api.get_webhooks.return_value = self.some_webhooks
        self.api.post_webhook.return_value = connector_webhook_id

        self.connector.set_sale_webhook(self.connector_webhook)

        self.assertTrue(self.api.post_webhook.called)
        self.api.post_webhook.assert_called_with(self.connector_webhook.data)

    def test_set_sale_webhook_creation_empty_webhook_list(self):
        connector_webhook_id = 42
        self.api.get_webhooks.return_value = []
        self.api.post_webhook.return_value = connector_webhook_id

        self.connector.set_sale_webhook(self.connector_webhook)

        self.assertTrue(self.api.post_webhook.called)
        self.api.post_webhook.assert_called_with(self.connector_webhook.data)

    def test_set_sale_webhook_update(self):
        connector_webhook_id = 42
        self.connector_webhook.webhook_id = connector_webhook_id
        self.api.get_webhooks.return_value = self.webhooks_with_ours

        self.connector.set_sale_webhook(self.updated_connector_webhook)

        self.api.delete_webhook.assert_called_once_with(connector_webhook_id)
        self.api.post_webhook.assert_called_once_with(
            self.updated_connector_webhook.data
        )

    def test_set_sale_webhook_no_change(self):
        connector_webhook_id = 42
        self.connector_webhook.webhook_id = connector_webhook_id
        self.api.get_webhooks.return_value = self.webhooks_with_ours

        self.connector.set_sale_webhook(self.connector_webhook)

        self.assertFalse(self.api.post_webhook.called)
        self.assertFalse(self.api.delete_webhook.called)


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


class SaleDataClassTestCase(TestCase):
    def test_sale_object_creation(self):
        data = {
            "sale_id": 44,
            "created_at": "2021-06-02 11:53:55",
            "completed_at": "2021-06-02 11:54:14",
            "store_id": 1,
            "vendor_id": 1,
            "unique_sale_id": "2021-06-1-2",
            "customer_id": 0,
            "currency": "EUR",
            "total": "763.50",
            "billing_address": 0,
            "shipping_address": 0,
            "payment": "CHE",
            "without_taxes": 0,
            "prices_without_taxes": 0,
            "ressource_id": 0,
            "points": 0,
            "sale_ext_ref": "",
            "service_charge": "0.00",
            "guests_number": 0,
            "takeaway": 0,
            "shipping_ref": "",
            "customs_duty": "0.00",
            "vat_number": "",
            "date_z": 20210602,
            "pickup_date": "0000-00-00 00:00:00",
            "cash_tendered": "0.00",
            "completed_at_date": "2021-06-02",
            "created_at_date": "2021-06-02",
            "created_at_date_yyyy": "2021",
            "created_at_date_mm": "06",
            "created_at_date_dd": "02",
            "completed_at_date_yyyy": "2021",
            "completed_at_date_mm": "06",
            "completed_at_date_dd": "02",
            "date_z_yyyy": "2021",
            "date_z_mm": "06",
            "date_z_dd": "02",
            "pickup_date_yyyy": "0000",
            "pickup_date_mm": "00",
            "pickup_date_dd": "00",
            "pickup_date_hh": "00",
            "pickup_date_min": "00",
            "pickup_date_ss": "00",
            "line_items": [
                {
                    "product_id": 23,
                    "product_size": 0,
                    "quantity": 1,
                    "product_price": "750.00",
                    "product_currency": "EUR",
                    "vat": "0.200",
                    "package": 0,
                    "points": 0,
                    "discount": "0.00",
                    "stock_withdrawal": 1,
                    "credit_note": 0,
                    "credit_note_id": 0,
                    "product_comments": "",
                    "serial_number": "",
                    "line_item_id_return": 0,
                    "date_return": 0,
                    "kitchen_pos": 1,
                    "product_supply_price": "0.00",
                    "line_item_id": 58,
                    "detail_commande_id": 58,
                    "item_unit_net_wo_discount": "625.00",
                    "item_unit_gross_wo_discount": "750.00",
                    "item_unit_discount_net": "0.00",
                    "item_unit_discount_gross": "0.00",
                    "item_unit_net": "625.00",
                    "item_unit_tax": "125.00",
                    "item_unit_gross": "750.00",
                    "item_discount_net": "0.00",
                    "item_discount_tax": "0.00",
                    "item_discount_gross": "0.00",
                    "item_discount_percentage": "0.00",
                    "item_total_net": "625.00",
                    "item_total_gross": "750.00",
                    "item_total_tax": "125.00",
                    "tax_label": "Taux normal 20%",
                    "tax_value": 20,
                    "product_model": "Une belle tirelire",
                    "product_barcode": "2430000000232",
                    "product_brand": 0,
                    "product_supplier": 0,
                    "product_category": 0,
                    "product_size_type": 0,
                    "product_package": 0,
                    "product_stock_management": 0,
                    "product_supplier_reference": "",
                    "product_desc": "",
                    "storage_location": "",
                    "product_arch": 0,
                    "products_ref_ext": "tirelire-1",
                    "multiple": 1,
                    "tags": [],
                    "modifiers": [],
                    "modifiers_conc": "",
                    "multiple_quantity": 1,
                    "multiple_product_price": 750,
                    "item_discount_percentage_round_0": "0",
                },
                {
                    "product_id": 24,
                    "product_size": 0,
                    "quantity": 3,
                    "product_price": "13.50",
                    "product_currency": "EUR",
                    "vat": "0.200",
                    "package": 0,
                    "points": 0,
                    "discount": "0.00",
                    "stock_withdrawal": 1,
                    "credit_note": 0,
                    "credit_note_id": 0,
                    "product_comments": "",
                    "serial_number": "",
                    "line_item_id_return": 0,
                    "date_return": 0,
                    "kitchen_pos": 1,
                    "product_supply_price": "0.00",
                    "line_item_id": 62,
                    "detail_commande_id": 62,
                    "item_unit_net_wo_discount": "11.25",
                    "item_unit_gross_wo_discount": "13.50",
                    "item_unit_discount_net": "0.00",
                    "item_unit_discount_gross": "0.00",
                    "item_unit_net": "11.25",
                    "item_unit_tax": "2.25",
                    "item_unit_gross": "13.50",
                    "item_discount_net": "0.00",
                    "item_discount_tax": "0.00",
                    "item_discount_gross": "0.00",
                    "item_discount_percentage": "0.00",
                    "item_total_net": "33.75",
                    "item_total_gross": "40.50",
                    "item_total_tax": "6.75",
                    "tax_label": "Taux normal 20%",
                    "tax_value": 20,
                    "product_model": "Une très belle tirelire!",
                    "product_barcode": "2430000000249",
                    "product_brand": 0,
                    "product_supplier": 0,
                    "product_category": 0,
                    "product_size_type": 0,
                    "product_package": 0,
                    "product_stock_management": 0,
                    "product_supplier_reference": "",
                    "product_desc": "",
                    "storage_location": "",
                    "product_arch": 0,
                    "products_ref_ext": "tirelire-1",
                    "multiple": 1,
                    "tags": [],
                    "modifiers": [],
                    "modifiers_conc": "",
                    "multiple_quantity": 3,
                    "multiple_product_price": 13.5,
                    "item_discount_percentage_round_0": "0",
                },
            ],
            "sale_total_net": "636.25",
            "sale_total_tax": "127.25",
            "sale_total_gross": "763.50",
            "sale_total_quantity": 2,
            "taxes": [
                {
                    "tax_value": "0.200",
                    "tax_value_p": "20%",
                    "tax_label": "Taux normal 20%",
                    "tax_accounting_account": "",
                    "total_net": "636.25",
                    "total_vat": "127.25",
                    "total_gross": "763.50",
                }
            ],
            "sale_tags": [],
            "closed_day": 0,
            "payment_accounting_account": "",
            "vendor_last_name": "Dupre",
            "vendor_first_name": "Marc-Antoine",
            "warehouse_id": 1,
        }

        sale = Sale.create_from_data(data)

        expected = Sale(
            sale_id=44,
            created_at=datetime(2021, 6, 2, 11, 53, 55),
            completed_at=datetime(2021, 6, 2, 11, 54, 14),
            unique_sale_id="2021-06-1-2",
            line_items=[
                SaleLineItem(product_id=23, quantity=1),
                SaleLineItem(product_id=24, quantity=3),
            ],
        )
        self.assertEquals(sale, expected)


class ClosedSaleDataClassTestCase(TestCase):
    def test_closed_sale_object_creation(self):
        data = {
            "sale_id": 42,
            "created_at": "2021-06-02 11:20:14",
            "completed_at": "2021-06-02 11:20:32",
            "store_id": 1,
            "vendor_id": 1,
            "unique_sale_id": "2021-06-1-1",
            "customer_id": 0,
            "currency": "EUR",
            "payment": "CB",
            "billing_address": 0,
            "shipping_address": 0,
            "resource_id": 0,
            "guests_number": 0,
            "total": "39.00",
        }

        closed_sale = ClosedSale.create_from_data(data)

        expected = ClosedSale(
            sale_id=42,
            created_at=datetime(2021, 6, 2, 11, 20, 14),
            completed_at=datetime(2021, 6, 2, 11, 20, 32),
            unique_sale_id="2021-06-1-1",
        )
        self.assertEquals(closed_sale, expected)
