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


def create_pos_profile():
    if frappe.flags.test_pos_profile_created:
        return

    frappe.set_user("Administrator")

    hs = frappe.get_doc("Hiboutik Settings")
    hs.enable_sync = False
    hs.pos_profile = None
    hs.save()

    frappe.delete_doc("POS Profile", "_Opossum Hiboutik")
    frappe.delete_doc("Item", "_opossum_item1")

    doc = frappe.get_doc(
        {
            "doctype": "Item",
            "name": "_Opossum Item1",
            "company": "_Test Company",
            "item_code": "_opossum_item1",
            "stock_uom": "Meter",
            "item_group": "Services",
        }
    ).insert()

    doc = frappe.get_doc(
        {
            "doctype": "POS Profile",
            "name": "_Opossum Hiboutik",
            "payments": [
                {
                    "doctype": "POS Payment Method",
                    "name": "new-pos-payment-method-2",
                    "default": 1,
                    "allow_in_returns": 0,
                    "idx": 1,
                    "mode_of_payment": "Cash",
                }
            ],
            "company": "_Test Company",
            "currency": "EUR",
            "write_off_cost_center": "Main - _TC",
            "write_off_account": "Sales - _TC",
            "warehouse": "_Test Warehouse - _TC",
        }
    ).insert()

    account_doc = frappe.get_doc("Account", "_Test Income Account - _TC")
    if not account_doc:
        frappe.get_doc(
            {
                "doctype": "Account",
                "account_name": "_Test Income Account",
                "root_type": "Income",
                "parent_account": frappe.get_list(
                    "Account",
                    filters={"company": "_Test Company", "root_type": "Income", "is_group": 1},
                    pluck="name")[0],
                "company": "_Test Company"
            }
        ).insert()

    frappe.flags.test_pos_profile_created = True


class TestHiboutikSettings(unittest.TestCase):
    def setUp(self):
        create_pos_profile()

    def test_sync_one_item_if_disabled(self):
        settings = frappe.get_doc("Hiboutik Settings")
        settings.enable_sync = False
        settings.save()

        article_json = json.JSONEncoder().encode(
            {
                "item_code": "_opossum_item1",
                "name": "An article",
                "hiboutik_id": "T_Item1",
            }
        )
        assert sync_item(article_json) == False

    def test_sync_one_item_with_wrong_credentials(self):
        with patch.object(HiboutikConnector, "set_sale_webhook"):
            settings = frappe.get_doc("Hiboutik Settings")
            settings.enable_sync = True
            settings.instance_name = "wrong_instance_name"
            settings.username = "wrong username"
            settings.api_key = "wrong api key"
            settings.pos_profile = "_Opossum Hiboutik"
            settings.customer = "_Test Customer"
            settings.income_account = "_Test Income Account - _TC"
            settings.save()

            with patch.object(HiboutikConnector, "sync") as mock_method:
                mock_method.side_effect = HiboutikAPIError()
                article_json = json.JSONEncoder().encode(
                    {
                        "item_code": "_opossum_item1",
                        "name": "An article",
                        "hiboutik_id": "T_Item1",
                    }
                )

                with self.assertRaises(HiboutikAPIError) as context:
                    sync_item(article_json)

    def test_sync_one_item(self):
        with patch.object(HiboutikConnector, "set_sale_webhook"):
            settings = frappe.get_doc("Hiboutik Settings")
            settings.enable_sync = True
            settings.instance_name = "valid_instance_name"
            settings.username = "valid username"
            settings.api_key = "valid api key"
            settings.pos_profile = "_Opossum Hiboutik"
            settings.customer = "_Test Customer"
            settings.income_account = "_Test Income Account - _TC"
            settings.save()

            item = frappe.get_doc("Item", "_opossum_item1")
            item.is_stock_item = False
            item.save()

            item = Item(
                code="_opossum_item1",
                name="An Article",
                price="10",
                vat=1,
                is_stock_item=False,
                external_id="T_Item1",
            )

            with patch.object(HiboutikConnector, "sync", return_value=item) as mock_method:
                article_json = json.JSONEncoder().encode(
                    {
                        "item_code": item.code,
                        "name": item.name,
                        "hiboutik_id": item.external_id,
                    }
                )
                assert sync_item(article_json) == True
                doc = frappe.get_doc("Item", item.code)
                assert doc.hiboutik_id == item.external_id
                mock_method.assert_called_once()

    def test_model_is_fed_from_item(self):
        doc = frappe.get_doc("Item", "_opossum_item1")

        item = Item(code=doc.item_code, name=doc.name, price=10.0, vat=1, is_stock_item=False)

        assert item.code == doc.item_code
        assert item.name == doc.name
        assert item.price == 10.0
        assert item.vat == 1

    def test_enabling_hiboutik_create_custom_item_fields(self):
        with patch.object(HiboutikConnector, "set_sale_webhook"):
            settings = frappe.get_doc("Hiboutik Settings")
            settings.enable_sync = True
            settings.instance_name = "random_instance_name"
            settings.username = "random username"
            settings.api_key = "random api key"
            settings.pos_profile = "_Opossum Hiboutik"
            settings.customer = "_Test Customer"
            settings.income_account = "_Test Income Account - _TC"
            settings.save()

            item_dt = frappe.get_meta("Item")

            assert item_dt.has_field("hiboutik_id") is True


class TestHiboutikWebhooks(unittest.TestCase):
    def test_pos_invoice_received(self):
        pass  # assert pos_invoice_webhook() is True
