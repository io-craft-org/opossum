from dataclasses import dataclass


@dataclass
class Item:
    code: str
    name: str
    price: str
    vat: int
    external_id: str = ""
