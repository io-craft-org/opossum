# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model.document import Document
from opossum.opossum.hiboutik import HiboutikConnector
from opossum.opossum.model import Item
from six import string_types


class HiboutikSettings(Document):
    def validate(self):
        self.validate_settings()
        self.create_delete_custom_fields()

    def validate_settings(self):
        if self.enable_sync:
            if not self.instance_name:
                frappe.throw(_("Please enter an instance name"))

            if not self.username:
                frappe.throw(_("Please enter a username"))

            if not self.api_key:
                frappe.throw(_("Please enter an API key"))

    def create_delete_custom_fields(self):
        """When the user enables sync, make custom fields in Doctypes"""

        if self.enable_sync:
            custom_fields = {}

            for doctype in ["Item"]:
                fields = [
                    dict(
                        fieldname="hiboutik_id",
                        label="Hiboutik ID",
                        fieldtype="Data",
                        read_only=1,
                        print_hide=1,
                        translatable=0,
                    ),
                    dict(
                        fieldname="sync_with_hiboutik",
                        label="Sync with Hiboutik",
                        fieldtype="Check",
                        insert_after="is_stock_item",
                        print_hide=1,
                    ),
                ]
                for df in fields:
                    create_custom_field(doctype, df)


@frappe.whitelist()
def sync_item(json_doc):
    """Given an Item, request sync to POS"""

    if isinstance(json_doc, string_types):
        item_doc = json.loads(json_doc)
    else:
        return False

    item = Item(code=item_doc["item_code"], name=item_doc["name"], price=10.0, vat=1)

    hiboutik_settings = frappe.get_doc("Hiboutik Settings")

    if not hiboutik_settings.enable_sync:
        return False

    hiboutik = HiboutikConnector(
        account=hiboutik_settings.instance_name,
        user=hiboutik_settings.username,
        api_key=hiboutik_settings.api_key,
    )

    hiboutik.sync(item)

    return True


@frappe.whitelist
def pos_invoice_webhook():
    """Receives a POS Invoice from Hiboutik"""
    # Check if pos-opening-entry exists, create it otherwise
    # XXX: we need a default POS Profile (set that in Hiboutik Settings)

    opening_entry = frappe.get_doc("POS Opening Entry")

    # Insert a POS Invoice with update stock selected


@frappe.whitelist
def pos_closing_webhook():
    pass
