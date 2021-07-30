# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe

from .models import POSInvoice, POSInvoiceItem


LOGGER = frappe.logger(__name__)


def get_or_create_opening_entry(user):
    """Given a user, make sure we have a POS Opening Entry.
    Create one if necessary."""

    created = False
    # try:
    #     open_entry = frappe.get_last_doc(
    #         "POS Opening Entry",
    #         filters={"user": user, "pos_closing_entry": ["in", ["", None]], "docstatus": 1},
    #     )
    # except frappe.exceptions.DoesNotExistError:

    hb_settings = frappe.get_single("Hiboutik Settings")

    open_entry = frappe.new_doc(
        "POS Opening Entry"
    )  # FIXME: Should populate more fields such as POS Profile
    open_entry.pos_profile = hb_settings.pos_profile
    open_entry.user = "Administrator"
    open_entry.period_start_date = datetime.now()
    open_entry_detail = frappe.new_doc(
        doctype="POS Opening Entry Detail",
        parent_doc=open_entry,
        parentfield='balance_details'
    )
    open_entry_detail.mode_of_payment = "Espèces"
    open_entry_detail.opening_amount = 150
    open_entry.balance_details = [open_entry_detail]
    open_entry.insert()
    open_entry.submit()
    frappe.db.commit()

    created = True
    return open_entry, created


@frappe.whitelist(allow_guest=True)
def test_make_pos_invoice():

    opening_entry, created = get_or_create_opening_entry(
        "Administrator"
    )  # FIXME Hardcoded username

    company = opening_entry.company
    pos_profile = opening_entry.pos_profile
    customer = "Usagers Coroutine"

    pos_inv = frappe.new_doc("POS Invoice")

    # POS Invoice Items
    pos_inv.append("items", {
        "item_code": "25-trombones",
        "qty": 10,
        "income_account": "1-Comptes de Capitaux - MC",
        "item_tax_template": "France VAT 5.5% - MC"
    })
    pos_inv.append("items", {
        "item_code": "10-ballons",
        "qty": 3,
        "income_account": "1-Comptes de Capitaux - MC",
        "item_tax_template": "France VAT 20% - MC"
    })

    # POS Invoice Taxes
    pos_inv.append("taxes", {
        "charge_type": "On Net Total",
        "account_head": "VAT 5.5% - MC",
        "description": "La TVA à 5,5%",
        "rate": "0",  # This attribute value is mandatory for the taxes to be properly computed
    })
    pos_inv.append("taxes", {
        "charge_type": "On Net Total",
        "account_head": "VAT 20% - MC",
        "description": "La TVA à 20%",
        "rate": "0",  # This attribute value is mandatory for the taxes to be properly computed
    })

    pos_inv.customer = customer
    pos_inv.pos_profile = pos_profile
    pos_inv.company = company
    pos_inv.update_stock = 1
    pos_inv.is_pos = 1
    pos_inv.set_posting_time = 1

    # Je ne sais pas si les attributs suivants nous sont utiles.
    # pos_inv.posting_date = args.posting_date or frappe.utils.nowdate()
    # pos_inv.customer = args.customer or "_Test Customer" # XXX
    # pos_inv.debit_to = args.debit_to or "Debtors - _TC"
    # pos_inv.currency = args.currency or "EUR"
    # pos_inv.conversion_rate = args.conversion_rate or 1
    # pos_inv.account_for_change_amount = args.account_for_change_amount or "Cash - _TC"

    pos_inv.set_missing_values()
    pos_inv.insert(ignore_permissions=True)
    pos_inv.calculate_taxes_and_totals()  # Maybe useless
    pos_inv.submit()
    frappe.db.commit()
