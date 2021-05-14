# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and Contributors
# See license.txt
from __future__ import unicode_literals

import json
import unittest
from unittest.mock import patch

import frappe
from opossum.opossum.hiboutik import HiboutikConnector
from opossum.opossum.model import Item

from .hiboutik_settings import sync_item

test_records = frappe.get_test_records("Item")


class TestHiboutikSettings(unittest.TestCase):
    def test_sync_one_item_if_disabled(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.is_enabled = False
        settings.save()

        article_json = json.JSONEncoder().encode({"item_code": "article1", "name": "An article"})
        assert sync_item(article_json) == False

    def test_sync_one_item_with_wrong_credentials(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.is_enabled = True
        settings.instance_name = "wrong instance name"
        settings.username = "wrong username"
        settings.api_key = "wrong api key"
        settings.save()

        with patch.object(HiboutikConnector, "sync", return_value=False) as mock_method:
            article_json = json.JSONEncoder().encode({"item_code": "article1", "name": "An article"})
            assert sync_item(article_json) == False
            mock_method.assert_called_once()

    def test_sync_one_item(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.is_enabled = True
        settings.instance_name = "valid instance name"
        settings.username = "valid username"
        settings.api_key = "valid api key"
        settings.save()

        with patch.object(HiboutikConnector, "sync", return_value=True) as mock_method:
            article_json = json.JSONEncoder().encode({"item_code": "article1", "name": "An article"})
            assert sync_item(article_json) == True
            mock_method.assert_called_once()

    def test_model_is_fed_from_item(self):
        doc = frappe.get_doc("Item", "article1")

        item = Item(code=doc.item_code, name=doc.name, price=10.0, vat=1)

        assert item.code == doc.item_code
        assert item.name == doc.name
        assert item.price == 10.0
        assert item.vat == 1
