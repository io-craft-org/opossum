# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe.model.document import Document
from opossum.opossum.hiboutik import HiboutikConnector
from opossum.opossum.model import Item
from six import string_types


class HiboutikSettings(Document):
    def validate(self):
        self.validate_settings()

    def validate_settings(self):
        if self.is_enabled:
            if not self.instance_name:
                frappe.throw(_("Please enter an instance name"))

            if not self.username:
                frappe.throw(_("Please enter a username"))

            if not self.api_key:
                frappe.throw(_("Please enter an API key"))


@frappe.whitelist()
def sync_item(json_doc):
    if isinstance(json_doc, string_types):
        item_doc = json.loads(json_doc)
    else:
        return False

    item = Item(code=item_doc["item_code"], name=item_doc["name"], price=10.0, vat=1)

    hiboutik_settings = frappe.get_doc("Hiboutik Settings")

    if not hiboutik_settings.is_enabled:
        return False

    hiboutik = HiboutikConnector(
        account=hiboutik_settings.instance_name,
        user=hiboutik_settings.username,
        api_key=hiboutik_settings.api_key,
    )

    hiboutik.sync(item)

    return True
