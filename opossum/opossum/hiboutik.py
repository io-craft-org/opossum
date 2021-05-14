from dataclasses import dataclass
from logging import getLogger
from typing import List

import requests
from requests.auth import HTTPBasicAuth

from opossum.opossum.models import Item

LOGGER = getLogger(__name__)


class HiboutikStoreError(BaseException):
    pass


class HiboutikAPIError(BaseException):
    pass


class HiboutikConnector:
    def __init__(self, api):
        self.api = api

    def sync(self, item: Item):
        product = self.find_product(item)
        if product:
            self.api.update_product(product.product_id, Product.create(item))
        else:
            self.api.post_product(Product.create(item))

    def find_product(self, item: Item):
        all_products = self.api.get_products()
        matching_products = list(
            filter(lambda x: x.products_ref_ext == item.code, all_products)
        )
        if len(matching_products) == 1:
            return matching_products[0]
        elif len(matching_products) > 1:
            raise HiboutikStoreError(
                "Multiple products have the same external reference '%s'", item.code
            )
        return None


@dataclass
class Product:

    product_model: str
    product_price: str
    product_vat: int
    products_ref_ext: str
    product_id: int = None

    @classmethod
    def create(cls, item: Item):
        return Product(
            product_model=item.name,
            product_price=str(item.price),
            product_vat=item.vat,
            products_ref_ext=item.code,
        )

    @classmethod
    def create_from_data(cls, data: dict):
        return Product(
            product_id=data["product_id"],
            product_model=data["product_model"],
            product_price=data["product_price"],
            product_vat=data["product_vat"],
            products_ref_ext=data["products_ref_ext"],
        )

    @property
    def data(self) -> dict:
        rv = self.__dict__.copy()
        try:
            del rv["product_id"]
        except KeyError:
            pass
        return rv


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
            f"{self.api_root}/products", auth=HTTPBasicAuth(self.user, self.api_key)
        )
        LOGGER.debug(f"HIBOUTIK get products>{response.text}")
        if response.status_code != 200:
            raise HiboutikAPIError(response.json())
        return list(map(lambda p: Product.create_from_data(p), response.json()))

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
        LOGGER.debug(f"HIBOUTIK put product {product_id} {data}>{response.text}")
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

    def update_product(self, product_id: int, product: Product):
        current_data = self.get_product(product_id).data
        for k, v in product.data.items():
            if current_data[k] != v:
                self._put_product(product_id, {"product_attribute": k, "new_value": v})
