from dataclasses import dataclass
from logging import getLogger
from typing import List

import requests
from requests.auth import HTTPBasicAuth

from opossum.opossum.models import Item

LOGGER = getLogger(__name__)

#: Identifies uniquely the sale webhook for Hiboutik.
#: Allows to update with DELETE+POST if it already exists.
SALE_WEBHOOK_APP_ID = "DOKOS"

HIBOUTIK_DEFAULT_STOCK_ID = 1
HIBOUTIK_DEFAULT_PRODUCT_SIZE = 0


class HiboutikStoreError(BaseException):
    pass


class HiboutikAPIError(BaseException):
    pass


class HiboutikAPIInsufficientRightsError(BaseException):
    pass


@dataclass
class ProductData:

    product_model: str
    product_price: str
    product_vat: int
    product_arch: int  # Is the product archived, 0 for no, 1 for yes.
    product_stock_management: int  # Is the product stock-managed, 0 for no, 1 for yes.

    @classmethod
    def create(cls, item: Item):
        return ProductData(
            product_model=item.name,
            product_price=str(item.price),
            product_vat=item.vat,
            product_arch=int(item.deactivated),
            product_stock_management=int(item.is_stock_item),
        )

    @property
    def data(self) -> dict:
        return self.__dict__.copy()


@dataclass
class ProductStock:

    stock_available: int

    @classmethod
    def create_from_data(cls, data: dict):
        return ProductStock(stock_available=data["stock_available"])


@dataclass
class Product(ProductData):

    product_id: int
    stock_available: List[ProductStock]

    @classmethod
    def create_from_data(cls, data: dict):
        return Product(
            product_id=data["product_id"],
            product_model=data["product_model"],
            product_price=data["product_price"],
            product_vat=data["product_vat"],
            product_arch=data["product_arch"],
            product_stock_management=data["product_stock_management"],
            stock_available=[
                ProductStock.create_from_data(st)
                for st in data["stock_available"]
            ],
        )

    @property
    def data(self) -> dict:
        rv = self.__dict__.copy()
        del rv["stock_available"]
        del rv["product_id"]
        return rv


@dataclass
class ProductAttribute:
    product_attribute: str
    new_value: str


@dataclass
class SyncedItem(Item):

    product: Product or None = None

    def __init__(self, item: Item, product_id: int, product: Product = None):
        item_data = item.__dict__.copy()
        del item_data["external_id"]
        Item.__init__(self, external_id=int(product_id), **item_data)
        self.product = product


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
class InventoryInputData:

    stock_id: int


@dataclass
class InventoryInputDetailData:

    quantity: int
    product_id: int
    product_size: int


class HiboutikConnector:
    def __init__(self, api):
        self.api = api

    def sync(self, item: Item):
        if item.external_id:
            # FIXME: handle partial update due to some failures (some calls succeed, some don't).
            existing_product = self.api.get_product(item.external_id)
            update = []
            existing_data = existing_product.data
            for k, v in ProductData.create(item).data.items():
                if existing_data[k] != v:
                    update.append(ProductAttribute(k, str(v)))
            self.api.update_product(item.external_id, update)
            synced_item = SyncedItem(
                item, existing_product.product_id, existing_product
            )
        else:
            item.external_id = str(self.api.post_product(Product.create(item)))
            synced_item = SyncedItem(item, int(item.external_id))

        if item.is_stock_item:
            StockSyncer(self.api).sync(synced_item)

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


class StockSyncer:
    def __init__(self, api):
        self.api = api

    def sync(self, item: SyncedItem):
        if not item.is_stock_item:
            return

        pos_stock = (
            item.product.stock_available[0].stock_available
            if item.product
            else 0
        )

        diff = item.stock_qty - pos_stock
        if diff != 0:
            self.api.post_inventory_input_for_product(
                product_id=item.external_id, quantity=diff
            )


class HiboutikAPI:
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

    def post_inventory_input_for_product(self, product_id: int, quantity: int):
        inv_input_id = self.post_inventory_input(
            InventoryInputData(HIBOUTIK_DEFAULT_STOCK_ID)
        )
        self.post_inventory_input_details(
            inv_input_id,
            InventoryInputDetailData(
                quantity, product_id, HIBOUTIK_DEFAULT_PRODUCT_SIZE
            ),
        )
        self.validate_inventory_input(inv_input_id)

    def post_inventory_input(self, inv_input: InventoryInputData) -> int:
        data = inv_input.__dict__.copy()
        response = self.session.post(
            f"{self.api_root}/inventory_inputs",
            auth=HTTPBasicAuth(self.user, self.api_key),
            data=data,
        )
        LOGGER.debug(
            f"HIBOUTIK post inventory input\n{data}\n>\n{response.text}"
        )
        if response.status_code == 201:
            return response.json()["inventory_input_id"]
        else:
            raise HiboutikAPIError(response.json())

    def post_inventory_input_details(
        self, inv_input_id: int, inv_input_detail: InventoryInputDetailData
    ) -> int:
        data = inv_input_detail.__dict__.copy()
        response = self.session.post(
            f"{self.api_root}/inventory_input_details/{inv_input_id}",
            auth=HTTPBasicAuth(self.user, self.api_key),
            data=data,
        )
        LOGGER.debug(
            f"HIBOUTIK post inventory input detail\n{data}\n>\n{response.text}"
        )
        if response.status_code == 201:
            return response.json()["inventory_input_detail_id"]
        else:
            raise HiboutikAPIError(response.json())

    def validate_inventory_input(self, inventory_input_id: int):
        data = {"inventory_input_id": inventory_input_id}
        response = self.session.post(
            f"{self.api_root}/inventory_input_validate",
            auth=HTTPBasicAuth(self.user, self.api_key),
            data=data,
        )
        LOGGER.debug(
            f"HIBOUTIK post inventory input validate\n{data}\n>\n{response.text}"
        )
        if response.status_code != 200:
            raise HiboutikAPIError(response.json())
