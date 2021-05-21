# -*- coding: utf-8 -*-
# Copyright (c) 2021, ioCraft and contributors
# For license information, please see license.txt

import frappe

from .models import POSInvoice


def get_or_create_opening_entry(user):
    """Given a user, make sure we have a POS Opening Entry.
    Create one if necessary."""

    created = False
    open_entry = frappe.get_last_doc(
        "POS Opening Entry",
        filters={"user": user, "pos_closing_entry": ["in", ["", None]], "docstatus": 1},
    )

    if not open_entry:
        open_entry = frappe.new_doc(
            "POS Opening Entry", {"user": user}
        )  # FIXME: Should populate more fields such as POS Profile
        open_entry.insert()
        created = True

    return open_entry, created


def make_pos_invoice(pos_invoice: POSInvoice, company, pos_profile):
    """Create a POS Invoice in the ERP from the external POS data"""

    return True

    pos_inv = frappe.new_doc("POS Invoice")
    # pos_inv.update(args)
    pos_inv.update_stock = 1
    pos_inv.is_pos = 1
    pos_inv.pos_profile = pos_profile

    pos_inv.set_posting_time = 1
    # pos_inv.posting_date = args.posting_date or frappe.utils.nowdate()

    pos_inv.company = company
    # pos_inv.customer = args.customer or "_Test Customer" # XXX
    # pos_inv.debit_to = args.debit_to or "Debtors - _TC"

    # pos_inv.currency = args.currency or "EUR"
    #  pos_inv.conversion_rate = args.conversion_rate or 1
    #  pos_inv.account_for_change_amount = args.account_for_change_amount or "Cash - _TC"

    pos_inv.set_missing_values()

    return

    pos_inv.append(
        "items",
        {
            "item_code": args.item or args.item_code or "_Test Item",
            "warehouse": args.warehouse or "_Test Warehouse - _TC",
            "qty": args.qty or 1,
            "rate": args.rate if args.get("rate") is not None else 100,
            "income_account": args.income_account or "Sales - _TC",
            "expense_account": args.expense_account or "Cost of Goods Sold - _TC",
            "cost_center": args.cost_center or "_Test Cost Center - _TC",
            "serial_no": args.serial_no,
        },
    )

    if not args.do_not_save:
        pos_inv.insert()
        if not args.do_not_submit:
            pos_inv.submit()
        else:
            pos_inv.payment_schedule = []
    else:
        pos_inv.payment_schedule = []

    return pos_inv
