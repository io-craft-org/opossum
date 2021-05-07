from dataclasses import dataclass


@dataclass
class Item:
    code: int
    name: str
    price: int
    vat: int
