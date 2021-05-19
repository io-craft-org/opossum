# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and contributors
# For license information, please see license.txt

# Part of the code inspired by
# https://gitlab.com/dokos/dokos/-/blob/develop/erpnext/erpnext_integrations/doctype/woocommerce_settings/woocommerce_settings.py

from __future__ import unicode_literals

import json

import frappe
from erpnext.selling.page import point_of_sale
from erpnext.utilities.product import get_price
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model.document import Document
from frappe.utils import flt
from opossum.opossum.hiboutik import HiboutikAPI, HiboutikConnector
from opossum.opossum.models import Item
from opossum.opossum.pos_utils import (get_or_create_opening_entry,
                                       make_pos_invoice)
from six import string_types
from six.moves.urllib.parse import urlparse


class HiboutikSettings(Document):
    def validate(self):
        self.validate_settings()
        self.create_custom_fields()

    def on_update(self):
        self.make_and_set_webhook_urls()

    def validate_settings(self):
        """ If enabled, force connection info fields to be filled """
        if self.enable_sync:
            if not self.instance_name:
                frappe.throw(_("Please enter an instance name"))

            if not self.username:
                frappe.throw(_("Please enter a username"))

            if not self.api_key:
                frappe.throw(_("Please enter an API key"))

            if not self.pos_profile:
                frappe.throw(_("Please select a POS Profile"))

            if not self.pos_invoice_webhook:
                self.pos_invoice_webhook = self._make_pos_invoice_webhook_url()

    def create_custom_fields(self):
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

    def _make_pos_invoice_webhook_url(self):
        """ Generate the public POS Invoice Webhook URL"""
        endpoint = "/api/method/opossum.opossum.doctype.hiboutik_settings.hiboutik_settings.pos_invoice_webhook"

        try:
            url = frappe.request.url
        except RuntimeError:
            # for CI Test to work
            url = "http://localhost:8000"

        server_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))

        delivery_url = server_url + endpoint

        return delivery_url

    def make_and_set_webhook_urls(self):
        """ Make the Webhook URI and register it to Hiboutik"""
        if self.enable_sync:
            self.pos_invoice_webhook = self._make_pos_invoice_webhook_url()

            hiboutik_api = HiboutikAPI(
                account=self.instance_name,
                user=self.username,
                api_key=self.api_key,
            )

            connector = HiboutikConnector(hiboutik_api)

            # call HiboutikConnector here


@frappe.whitelist()
def sync_item(json_doc):
    """Given an Item, request sync to external POS"""

    hiboutik_settings = frappe.get_doc("Hiboutik Settings")

    if not hiboutik_settings.enable_sync:
        return False

    if isinstance(json_doc, string_types):
        item_json = json.loads(json_doc)
    else:
        return False

    item_doc = frappe.get_doc("Item", item_json["item_code"])

    # Get POS Profile from Hiboutik Settings
    hiboutik_settings = frappe.get_single("Hiboutik Settings")
    pos_profile = frappe.get_doc("POS Profile", hiboutik_settings.pos_profile)

    # Get Price given the Price List configured
    price = get_price(
        item_doc.item_code,
        pos_profile.selling_price_list,
        "",  # Customer_group
        pos_profile.company,
        qty=1,
    )

    item = Item(
        code=item_doc.item_code,
        name=item_doc.name,
        external_id=item_doc.hiboutik_id,
        price=flt(price.get("price_list_rate") if price else 0.0),
        vat=1,
    )  # FIXME Hardcoded VAT

    hiboutik_api = HiboutikAPI(
        account=hiboutik_settings.instance_name,
        user=hiboutik_settings.username,
        api_key=hiboutik_settings.api_key,
    )

    connector = HiboutikConnector(hiboutik_api)

    updated_item = connector.sync(item)

    if item_doc.hiboutik_id != updated_item.external_id:
        item_doc.hiboutik_id = updated_item.external_id
        item_doc.save()
        # FIXME Request page reload

    return True


@frappe.whitelist(allow_guest=True)
def pos_invoice_webhook(*args, **kwargs):
    """Receives a POS Invoice from Hiboutik"""

    try:
        data = frappe.parse_json(frappe.safe_decode(frappe.request.data))
    except json.decoder.JSONDecodeError:
        data = frappe.safe_decode(frappe.request.data)

    # XXX: we need a default POS Profile (set that in Hiboutik Settings)
    opening_entry, created = get_or_create_opening_entry(
        "Administrator"
    )  # FIXME Hardcoded username

    make_pos_invoice(opening_entry.company, opening_entry.pos_profile)

    # Insert a POS Invoice with update stock selected


@frappe.whitelist
def pos_closing_webhook():
    pass
