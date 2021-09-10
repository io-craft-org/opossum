# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe

from .models import POSInvoice, POSInvoiceItem


def get_or_create_opening_entry(user):
    """Given a user, make sure we have a POS Opening Entry.
    Create one if necessary."""

    open_entry = frappe.new_doc(
        "POS Opening Entry"
    )  # FIXME: Should populate more fields such as POS Profile
    hb_settings = frappe.get_single("Hiboutik Settings")
    pos_profile = frappe.get_doc("POS Profile", hb_settings.pos_profile)
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

    pos_invoice = POSInvoice(
        posting_date=datetime.now(),
        invoice_items=[
            POSInvoiceItem(qty=10, external_id="balloons"),
            POSInvoiceItem(qty=7, external_id="forks"),
        ]
    )
    opening_entry, created = get_or_create_opening_entry(
        "Administrator"
    )  # FIXME Hardcoded username

    from .doctype.hiboutik_settings.hiboutik_settings import resolve_and_set_item_codes
    resolve_and_set_item_codes(pos_invoice)

    hb_settings = frappe.get_single("Hiboutik Settings")

    # customer = hb_settings.customer
    customer = frappe.get_doc("Customer", "Usagers Coroutine")

    make_pos_invoice(
        pos_invoice=pos_invoice,
        company=opening_entry.company,
        pos_profile=opening_entry.pos_profile,
        customer="Usagers Coroutine"
    )


def _get_item_taxes(item_codes, company):
    """Takes a list of item codes.
    Returns a map of tax account name : tax account doc.
    """

    from erpnext.stock.get_item_details import get_item_tax_template, get_item_tax_map

    rv = {}
    item_taxes = {}
    item_tax_templates = {}
    for item_code in item_codes:
        if item_code in item_taxes:
            continue
        item_taxes[item_code] = {}
        item_tax_templates[item_code] = {}
        item_doc = frappe.get_cached_doc("Item", item_code)
        args = {"company": company}
        get_item_tax_template(args, item_doc, item_tax_templates[item_code])
        item_taxes[item_code]["item_tax_rate"] = get_item_tax_map(company, item_tax_templates[item_code].get("item_tax_template"), as_json=False)
        for itax in item_taxes.values():
            for tax_account_name in itax["item_tax_rate"].keys():
                if not tax_account_name in rv:
                    rv[tax_account_name] = frappe.get_doc("Account", tax_account_name)
    return rv


def get_item_price_on(item_code: str, transaction_date: str):
    # Assumes there is one and only one selling price list
    default_price_list_doc = frappe.get_list("Price List", {"selling": 1})[0]
    from erpnext.stock.get_item_details import get_item_price
    results = get_item_price(
        args={
            "price_list": default_price_list_doc.name,
            "uom": "",
            "batch_no": "",
            # "transaction_date": transaction_date
        },
        item_code=item_code
    )
    # Pick the first and most recent price
    _, price_list_rate, _ = results[0]
    return price_list_rate


def make_pos_invoice(pos_invoice: POSInvoice, company, pos_profile, customer, default_income_account):
    """Create a POS Invoice in the ERP from the external POS data"""

    pos_inv_doc = frappe.new_doc("POS Invoice")

    for item in pos_invoice.invoice_items:
        pos_inv_doc.append(
            "items",
            {
                "item_code": item.code,
                "qty": item.qty,
                "income_account": default_income_account,
                "rate": get_item_price_on(item.code, pos_invoice.posting_date)
            }
        )

    item_taxes_map = _get_item_taxes({ii.code for ii in pos_invoice.invoice_items}, company)
    for tax_account_name, tax_account_doc in item_taxes_map.items():
        pos_inv_doc.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": tax_account_name,
                "description": tax_account_doc.account_name,
                "rate": "0"  # hackish: mandatory so the taxes are correctly spread across items
            }
        )

    pos_inv_doc.customer = customer
    pos_inv_doc.pos_profile = pos_profile
    pos_inv_doc.company = company
    pos_inv_doc.update_stock = 1
    pos_inv_doc.is_pos = 1
    pos_inv_doc.set_posting_time = 1
    # pos_inv_doc.posting_date = args.posting_date or frappe.utils.nowdate()
    # pos_inv_doc.customer = args.customer or "_Test Customer" # XXX
    # pos_inv_doc.debit_to = args.debit_to or "Debtors - _TC"
    # pos_inv_doc.currency = args.currency or "EUR"
    #  pos_inv_doc.conversion_rate = args.conversion_rate or 1
    #  pos_inv_doc.account_for_change_amount = args.account_for_change_amount or "Cash - _TC"

    pos_inv_doc.set_missing_values()
    # pos_inv_doc.set_taxes()
    # pos_inv_doc.insert(ignore_permissions=True)
    pos_inv_doc.insert()
    pos_inv_doc.calculate_taxes_and_totals()
    # pos_inv_doc.submit()
    frappe.db.commit()

    return pos_inv_doc
