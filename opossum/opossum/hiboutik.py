from dataclasses import dataclass
from logging import getLogger

import requests
from requests.auth import HTTPBasicAuth

from opossum.opossum.model import Item


LOGGER = getLogger(__name__)


class HiboutikConnector:

    def __init__(self, account, user, api_key):
        self.api = HiboutikAPI(account, user, api_key)

    def sync(self, item: Item):
        product = Product.create(item)
        self.api.post_product(product)


@dataclass
class Product:

    product_model: str
    product_price: str
    product_vat: int
    products_ref_ext: str

    @classmethod
    def create(cls, item: Item):
        return Product(
            product_model=item.name,
            product_price=str(item.price),
            product_vat=item.vat,
            products_ref_ext=item.code,
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

    def get_products(self):
        response = self.session.get(
            f"{self.api_root}/products", auth=HTTPBasicAuth(self.user, self.api_key)
        )
        LOGGER.debug(f"HIBOUTIK get products>{response.text}")

    def post_product(self, product: Product):
        response = self.session.post(
            f"{self.api_root}/products",
            auth=HTTPBasicAuth(self.user, self.api_key),
            data=product.__dict__,
        )
        LOGGER.debug(f"HIBOUTIK post product>{response.text}")

    def get(self, route):
        response = self.session.get(
            f"{self.api_root}{route}",
            auth=HTTPBasicAuth(self.user, self.api_key)
        )
        LOGGER.debug(f"HIBOUTIK get {self.api_root}{route}>{response.text}")
