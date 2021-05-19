# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and Contributors
# See license.txt
from __future__ import unicode_literals

import json
import unittest
from unittest.mock import patch

import frappe
from opossum.opossum.hiboutik import HiboutikAPIError, HiboutikConnector
from opossum.opossum.models import Item

from .hiboutik_settings import pos_invoice_webhook, sync_item

test_records = frappe.get_test_records("Item")


class TestHiboutikSettings(unittest.TestCase):
    def test_sync_one_item_if_disabled(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.enable_sync = False
        settings.save()

        article_json = json.JSONEncoder().encode(
            {"item_code": "article1", "name": "An article", "hiboutik_id": "T_Item1"}
        )
        assert sync_item(article_json) == False

    def test_sync_one_item_with_wrong_credentials(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.enable_sync = True
        settings.instance_name = "wrong instance name"
        settings.username = "wrong username"
        settings.api_key = "wrong api key"
        settings.save()

        with patch.object(HiboutikConnector, "sync") as mock_method:
            mock_method.side_effect = HiboutikAPIError()
            article_json = json.JSONEncoder().encode(
                {
                    "item_code": "article1",
                    "name": "An article",
                    "hiboutik_id": "T_Item1",
                }
            )

            with self.assertRaises(HiboutikAPIError) as context:
                sync_item(article_json)

    def test_sync_one_item(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.enable_sync = True
        settings.instance_name = "valid instance name"
        settings.username = "valid username"
        settings.api_key = "valid api key"
        settings.save()

        item = Item(code="article1", name="An Article", price="10", vat=1)

        with patch.object(HiboutikConnector, "sync", return_value=item) as mock_method:
            article_json = json.JSONEncoder().encode(
                {"item_code": item.code, "name": item.name, "hiboutik_id": "T_Item1"}
            )
            assert sync_item(article_json) == True
            mock_method.assert_called_once()

    def test_model_is_fed_from_item(self):
        doc = frappe.get_doc("Item", "article1")

        item = Item(code=doc.item_code, name=doc.name, price=10.0, vat=1)

        assert item.code == doc.item_code
        assert item.name == doc.name
        assert item.price == 10.0
        assert item.vat == 1

    def test_enabling_hiboutik_create_custom_item_fields(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.enable_sync = True
        settings.instance_name = "random instance name"
        settings.username = "random username"
        settings.api_key = "random api key"
        settings.save()

        item_dt = frappe.get_meta("Item")

        assert item_dt.has_field("hiboutik_id") is True


class TestHiboutikWebhooks(unittest.TestCase):
    def test_pos_invoice_received(self):
        assert pos_invoice_webhook("") is True
