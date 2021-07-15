# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and contributors
# For license information, please see license.txt

# Part of the code inspired by
# https://gitlab.com/dokos/dokos/-/blob/develop/erpnext/erpnext_integrations/doctype/woocommerce_settings/woocommerce_settings.py

from __future__ import unicode_literals

import json

from six import string_types
from six.moves.urllib.parse import urlparse

import frappe
from erpnext.utilities.product import get_price
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model.document import Document
from frappe.utils import flt
from opossum.opossum.hiboutik import HiboutikAPI, HiboutikConnector, HiboutikAPIError
from opossum.opossum import hiboutik
from opossum.opossum.models import Item, POSInvoice
from opossum.opossum.pos_utils import (
    get_or_create_opening_entry,
    make_pos_invoice,
)


class HiboutikSettings(Document):
    def validate(self):
        self.validate_settings()
        self.create_custom_fields()

    def on_update(self):
        self.make_and_set_webhook_urls()

    def validate_settings(self):
        """If enabled, force connection info fields to be filled"""
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
        """Generate the public POS Invoice Webhook URL"""
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
        """Make the Webhook URI and register it to Hiboutik"""
        if self.enable_sync:
            self.pos_invoice_webhook = self._make_pos_invoice_webhook_url()

            hiboutik_api = HiboutikAPI(
                account=self.instance_name,
                user=self.username,
                api_key=self.api_key,
            )

            connector = HiboutikConnector(hiboutik_api)

            webhook = hiboutik.Webhook.create_connector_webhook(
                self.pos_invoice_webhook
            )
            try:
                connector.set_sale_webhook(webhook)
            except HiboutikAPIError as e:
                frappe.msgprint(
                    msg="Erreur de mise en place du Webhook. Vérifiez que vous avez les droits dans l'interface Hiboutik.",
                    title="Erreur Hiboutik",
                    raise_exception=HiboutikAPIError,
                )


@frappe.whitelist()
def sync_all_items():
    """Synchronize all items where 'hiboutik_sync' checkbox is ticked"""

    hiboutik_settings = frappe.get_doc("Hiboutik Settings")

    if not hiboutik_settings.enable_sync:
        return False

    items = frappe.db.get_list(
        "Item",
        filters={"sync_with_hiboutik": "true", "disabled": "false"},
        fields=["item_code"],
    )

    for item in items:
        res = _sync_item_to_hiboutik(item["item_code"])
        if not res:
            frappe.msgprint(
                msg=f"Erreur de synchronization de l'item {item.code}." % item,
                title="Erreur Hiboutik",
                raise_exception=HiboutikAPIError,
            )


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

    return _sync_item_to_hiboutik(item_json["item_code"])


def _sync_item_to_hiboutik(item_code: str):
    item_doc = frappe.get_doc("Item", item_code)

    # Get POS Profile from Hiboutik Settings
    hiboutik_settings = frappe.get_single("Hiboutik Settings")
    pos_profile = frappe.get_doc("POS Profile", hiboutik_settings.pos_profile)

    hb_tax_id = get_hiboutik_tax_id(item_doc, hiboutik_settings)

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
        vat=hb_tax_id,
        is_stock_item=False,
    )

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
        # item_doc.reload() # XXX Can't figure out how to do it

    return True


@frappe.whitelist(allow_guest=True)
def pos_invoice_webhook(*args, **kwargs):
    """Receives a POS Invoice from Hiboutik"""

    try:
        data = frappe.parse_json(frappe.safe_decode(frappe.request.data))
    except json.decoder.JSONDecodeError:
        data = frappe.safe_decode(frappe.request.data)

    pos_invoice = convert_payload_to_POS_invoice(data)

    opening_entry, created = get_or_create_opening_entry(
        "Administrator"
    )  # FIXME Hardcoded username

    resolve_and_set_item_codes(pos_invoice)

    make_pos_invoice(pos_invoice, opening_entry.company, opening_entry.pos_profile)

    # Insert a POS Invoice with update stock selected


@frappe.whitelist
def pos_closing_webhook():
    pass


def resolve_and_set_item_codes(pos_invoice: POSInvoice):
    """Set Item Code from External id field"""
    for item in pos_invoice.invoice_items:
        item.code = get_item_code_from_external_id(item.external_id)


def get_item_code_from_external_id(external_id: str):
    """Given the Hiboutik stored external ID, retrieve the ERPNext Item code"""
    return frappe.db.get_value("Item", dict(hiboutik_id=external_id))


def get_hiboutik_tax_id(item: Document, hb_settings: Document) -> int:
    """Returns the Hiboutik's tax ID corresponding to the tax set for the Item."""
    HIBOUTIK_20_TAX_ID = 1
    HIBOUTIK_10_TAX_ID = 2
    HIBOUTIK_5_5_TAX_ID = 3
    HIBOUTIK_2_1_TAX_ID = 4
    HIBOUTIK_NO_TAX_ID = 5

    itt_name = get_item_tax_template_name(item)

    if hb_settings.tva_20 == itt_name:
        return HIBOUTIK_20_TAX_ID

    if hb_settings.tva_10 == itt_name:
        return HIBOUTIK_10_TAX_ID

    if hb_settings.tva_5_5 == itt_name:
        return HIBOUTIK_5_5_TAX_ID

    if hb_settings.tva_2_1 == itt_name:
        return HIBOUTIK_2_1_TAX_ID

    return HIBOUTIK_NO_TAX_ID


# FIXME: maybe there is an erpnext function doing a better job.
def get_item_tax_template_name(item: Document) -> str:
    """Given an Item returns the first Tax Template found either at the Item level
    or at the Item Group level. Returns an empty string if no tax template has been set for this item."""

    def get_item_tax():
        try:
            return item.taxes[0].item_tax_template
        except IndexError:
            return None

    def get_item_group_tax():
        group = frappe.get_doc("Item Group", item.item_group)
        try:
            return group.taxes[0].item_tax_template
        except IndexError:
            return None

    for getter in [get_item_tax, get_item_group_tax]:
        itt_name = getter()
        if itt_name:
            return itt_name

    return ""
