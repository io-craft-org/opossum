# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from opossum.opossum.model import Item

from .hiboutik_settings import sync_item

test_records = frappe.get_test_records("Item")


class TestHiboutikSettings(unittest.TestCase):
    def test_sync_one_item(self):
        assert sync_item("article1") == True

    def test_model_is_fed_from_item(self):
        doc = frappe.get_doc("Item", "article1")

        item = Item(code=doc.item_code, name=doc.name, price=10.0, vat=1)

        assert item.code == doc.item_code
        assert item.name == doc.name
        assert item.price == 10.0
        assert item.vat == 1
