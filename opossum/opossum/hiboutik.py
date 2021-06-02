from dataclasses import dataclass
from datetime import datetime, date
from logging import getLogger
from typing import List

import requests
from requests.auth import HTTPBasicAuth

from opossum.opossum.models import Item, POSInvoice, POSInvoiceItem

LOGGER = getLogger(__name__)

#: Identifies uniquely the sale webhook for Hiboutik.
#: Allows to update with DELETE+POST if it already exists.
SALE_WEBHOOK_APP_ID = "DOKOS"


class HiboutikStoreError(BaseException):
    pass


class HiboutikAPIError(BaseException):
    pass


class HiboutikAPIInsufficientRightsError(BaseException):
    pass


@dataclass
class Product:

    product_model: str
    product_price: str
    product_vat: int
    product_arch: int  # Is the product archived, 0 for no, 1 for yes.
    product_id: int or None = None

    @classmethod
    def create(cls, item: Item):
        return Product(
            product_model=item.name,
            product_price=str(item.price),
            product_vat=item.vat,
            product_arch=int(item.deactivated),
            product_id=int(item.external_id) if item.external_id else None,
        )

    @classmethod
    def create_from_data(cls, data: dict):
        return Product(
            product_id=data["product_id"],
            product_model=data["product_model"],
            product_price=data["product_price"],
            product_vat=data["product_vat"],
            product_arch=data["product_arch"],
        )

    @property
    def data(self) -> dict:
        rv = self.__dict__.copy()
        try:
            del rv["product_id"]
        except KeyError:
            pass
        return rv


@dataclass
class ProductAttribute:
    product_attribute: str
    new_value: str


@dataclass
class Webhook:
    webhook_label: str
    webhook_url: str
    webhook_action: str
    webhook_app_id_int: str
    webhook_id: int = None

    @classmethod
    def create_connector_webhook(cls, url: str):
        return Webhook(
            webhook_label="Synchronisation des ventes avec Dokos",
            webhook_url=url,
            webhook_action="sale",
            webhook_app_id_int=SALE_WEBHOOK_APP_ID,
        )

    @classmethod
    def create_from_data(cls, data: dict):
        return Webhook(
            webhook_id=data["webhook_id"],
            webhook_label=data["webhook_label"],
            webhook_url=data["webhook_url"],
            webhook_action=data["webhook_action"],
            webhook_app_id_int=data["webhook_app_id_int"],
        )

    @property
    def data(self) -> dict:
        rv = self.__dict__.copy()
        try:
            del rv["webhook_id"]
        except KeyError:
            pass
        return rv


@dataclass
class SaleLineItem:
    product_id: int
    # "product_size": 0,
    quantity: int
    # "product_price": "3.00",
    # "product_currency": "EUR",
    # "vat": "0.200",
    # "package": 0,
    # "points": 0,
    # "discount": "0.00",
    # "stock_withdrawal": 1,
    # "credit_note": 0,
    # "credit_note_id": 0,
    # "product_comments": "",
    # "serial_number": "",
    # "line_item_id_return": 0,
    # "date_return": 0,
    # "kitchen_pos": 1,
    # "product_supply_price": "0.00",
    # "line_item_id": 57,
    # "detail_commande_id": 57,
    # "item_unit_net_wo_discount": "2.50",
    # "item_unit_gross_wo_discount": "3.00",
    # "item_unit_discount_net": "0.00",
    # "item_unit_discount_gross": "0.00",
    # "item_unit_net": "2.50",
    # "item_unit_tax": "0.50",
    # "item_unit_gross": "3.00",
    # "item_discount_net": "0.00",
    # "item_discount_tax": "0.00",
    # "item_discount_gross": "0.00",
    # "item_discount_percentage": "0.00",
    # "item_total_net": "2.50",
    # "item_total_gross": "3.00",
    # "item_total_tax": "0.50",
    # "tax_label": "Taux normal 20%",
    # "tax_value": 20,
    # "product_model": "Ballons x10",
    # "product_barcode": "2430000000164",
    # "product_brand": 0,
    # "product_supplier": 0,
    # "product_category": 0,
    # "product_size_type": 0,
    # "product_package": 0,
    # "product_stock_management": 0,
    # "product_supplier_reference": "",
    # "product_desc": "",
    # "storage_location": "",
    # "product_arch": 0,
    # "products_ref_ext": "10-ballons",
    # "multiple": 1,
    # "tags": [],
    # "modifiers": [],
    # "modifiers_conc": "",
    # "multiple_quantity": 1,
    # "multiple_product_price": 3,
    # "item_discount_percentage_round_0": "0"

    @classmethod
    def create_from_data(cls, data: dict):
        line_item_fields = SaleLineItem.__dataclass_fields__.items()
        line_item_kwargs = {}
        for field_name, field_type in line_item_fields:
            if field_type.type is datetime:
                line_item_kwargs[field_name] = datetime.fromisoformat(
                    data[field_name]
                )
            else:
                line_item_kwargs[field_name] = data[field_name]
        return SaleLineItem(**line_item_kwargs)


@dataclass
class Sale:
    sale_id: int
    created_at: datetime
    completed_at: datetime
    # "store_id": 1,
    # "vendor_id": 1,
    unique_sale_id: str
    # "customer_id": 0,
    # "currency": "EUR",
    # "total": "3.00",
    # "billing_address": 0,
    # "shipping_address": 0,
    # "payment": "CB",
    # "without_taxes": 0,
    # "prices_without_taxes": 0,
    # "ressource_id": 0,
    # "points": 0,
    ## "sale_ext_ref": "",
    # "service_charge": "0.00",
    # "guests_number": 0,
    # "takeaway": 0,
    # "shipping_ref": "",
    # "customs_duty": "0.00",
    # "vat_number": "",
    # "date_z": 0,
    # "pickup_date": "0000-00-00 00:00:00",
    # "cash_tendered": "0.00",
    # "completed_at_date": "0000-00-00",
    # "created_at_date": "2021-06-02",
    # "created_at_date_yyyy": "2021",
    # "created_at_date_mm": "06",
    # "created_at_date_dd": "02",
    # "completed_at_date_yyyy": "0000",
    # "completed_at_date_mm": "00",
    # "completed_at_date_dd": "00",
    # "date_z_yyyy": "0",
    # "date_z_mm": false,
    # "date_z_dd": false,
    # "pickup_date_yyyy": "0000",
    # "pickup_date_mm": "00",
    # "pickup_date_dd": "00",
    # "pickup_date_hh": "00",
    # "pickup_date_min": "00",
    # "pickup_date_ss": "00",
    line_items: List[SaleLineItem]
    # "sale_total_net": "2.50",
    # "sale_total_tax": "0.50",
    # "sale_total_gross": "3.00",
    # "sale_total_quantity": 1,
    # "taxes": [
    #     {
    #         "tax_value": "0.200",
    #         "tax_value_p": "20%",
    #         "tax_label": "Taux normal 20%",
    #         "tax_accounting_account": "",
    #         "total_net": "2.50",
    #         "total_vat": "0.50",
    #         "total_gross": "3.00"
    #     }
    # ],
    # "sale_tags": [],
    # "closed_day": 0,
    # "payment_accounting_account": "",
    # "vendor_last_name": "Dupre",
    # "vendor_first_name": "Marc-Antoine",
    # "warehouse_id": 1

    @classmethod
    def create_from_data(cls, data: dict):
        sale_fields = Sale.__dataclass_fields__.items()
        sale_kwargs = {}
        for field_name, field_type in sale_fields:
            if field_type.type is datetime:
                sale_kwargs[field_name] = datetime.fromisoformat(
                    data[field_name]
                )
            else:
                sale_kwargs[field_name] = data[field_name]

        sale_kwargs["line_items"] = [
            SaleLineItem.create_from_data(i) for i in sale_kwargs["line_items"]
        ]

        return Sale(**sale_kwargs)


class HiboutikConnector:
    def __init__(self, api):
        self.api = api

    def sync(self, item: Item):
        if item.external_id:
            # FIXME: handle partial update due to some failures (some calls succeed, some don't).
            existing_product = self.api.get_product(item.external_id)
            update = []
            existing_data = existing_product.data
            for k, v in Product.create(item).data.items():
                if existing_data[k] != v:
                    update.append(ProductAttribute(k, str(v)))
            self.api.update_product(item.external_id, update)
        else:
            item.external_id = str(self.api.post_product(Product.create(item)))

        return item

    def set_sale_webhook(self, webhook: Webhook):
        webhooks = self.api.get_webhooks()
        matches = list(
            filter(
                lambda wh: wh.webhook_app_id_int == SALE_WEBHOOK_APP_ID
                and wh.webhook_action == "sale",
                webhooks,
            )
        )
        if len(matches) > 1:
            # TODO: delete all? raise exception ?
            LOGGER.warning(
                "There are more than one sale webhook defined on the Hiboutik store"
            )
        if matches:
            match = matches[0]
            if match.webhook_url != webhook.webhook_url:
                self.api.delete_webhook(match.webhook_id)
                self.api.post_webhook(webhook.data)
        else:
            self.api.post_webhook(webhook.data)

    def sync_sales_on_day(self, day: date, synced_sales: POSInvoice):
        """would fetch sales from Hiboutik store, compare with the given list,
        then returns the not synced yet sales."""
        pass

    def get_sales_on_day(self, day: date) -> List[POSInvoice]:
        pass

    def get_pos_invoices_on_day(self, day: date) -> List[POSInvoice]:
        pass


class HiboutikAPI:

    default_store_id: int = 1

    def __init__(self, account, user, api_key):
        self.account = account
        self.host = f"{account}.hiboutik.com"
        self.user = user
        self.api_key = api_key

        self.headers = {"Accept": "application/json"}

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self.api_root = "https://{0}/api".format(self.host)

    def get_products(self) -> List[Product]:
        response = self.session.get(
            f"{self.api_root}/products",
            auth=HTTPBasicAuth(self.user, self.api_key),
        )
        LOGGER.debug(f"HIBOUTIK get products>{response.text}")
        if response.status_code != 200:
            raise HiboutikAPIError(response.json())
        return list(
            map(lambda p: Product.create_from_data(p), response.json())
        )

    def post_product(self, product: Product) -> int:
        response = self.session.post(
            f"{self.api_root}/products",
            auth=HTTPBasicAuth(self.user, self.api_key),
            data=product.data,
        )
        LOGGER.debug(f"HIBOUTIK post product>{response.text}")
        if response.status_code != 201:
            raise HiboutikAPIError(response.json())
        return response.json()["product_id"]

    def _put_product(self, product_id: int, data):
        response = self.session.put(
            f"{self.api_root}/product/{product_id}",
            auth=HTTPBasicAuth(self.user, self.api_key),
            data=data,
        )
        LOGGER.debug(
            f"HIBOUTIK put product {product_id} {data}>{response.text}"
        )
        if response.status_code != 200:
            raise HiboutikAPIError(response.json())

    def get_product(self, product_id: int):
        response = self.session.get(
            f"{self.api_root}/products/{product_id}",
            auth=HTTPBasicAuth(self.user, self.api_key),
        )
        LOGGER.debug(f"HIBOUTIK get product {product_id}>{response.text}")
        if response.status_code == 200:
            return Product.create_from_data(response.json()[0])
        else:
            raise HiboutikAPIError(response.json())

    def update_product(self, product_id: int, update: List[ProductAttribute]):
        for pa in update:
            self._put_product(product_id, pa.__dict__)

    def get_webhooks(self) -> List[Webhook]:
        response = self.session.get(
            f"{self.api_root}/webhooks",
            auth=HTTPBasicAuth(self.user, self.api_key),
        )
        LOGGER.debug(f"HIBOUTIK get webhooks > {response.text}")
        if response.status_code != 200:
            raise HiboutikAPIError(response.json())
        return list(
            map(lambda i: Webhook.create_from_data(i), response.json())
        )

    def post_webhook(self, data: dict) -> int:
        response = self.session.post(
            f"{self.api_root}/webhooks",
            auth=HTTPBasicAuth(self.user, self.api_key),
            data=data,
        )
        LOGGER.debug(f"HIBOUTIK post webhook\n{data}\n>\n{response.text}")
        if response.status_code == 200:
            return response.json()["webhook_id"]
        elif response.status_code == 403:
            raise HiboutikAPIInsufficientRightsError(response.json())
        else:
            raise HiboutikAPIError(response.json())

    def delete_webhook(self, webhook_id: int):
        response = self.session.delete(
            f"{self.api_root}/webhooks/{webhook_id}",
            auth=HTTPBasicAuth(self.user, self.api_key),
        )
        LOGGER.debug(
            f"HIBOUTIK delete webhook {webhook_id} >\n{response.text}"
        )
        if response.status_code == 403:
            raise HiboutikAPIInsufficientRightsError(response.json())
        elif response.status_code != 200:
            raise HiboutikAPIError(response.json())

    def get_closed_sales_on_day(self, day: date) -> List[Sale]:
        response = self.session.get(
            f"{self.api_root}/closed_sales/{self.default_store_id}/{day.year}/{day.month}/{day.day}",
            auth=HTTPBasicAuth(self.user, self.api_key),
        )
        LOGGER.debug(f"HIBOUTIK get closed sales on day > {response.text}")
        if response.status_code != 200:
            raise HiboutikAPIError(response.json())
        return list(map(lambda i: Sale.create_from_data(i), response.json()))
