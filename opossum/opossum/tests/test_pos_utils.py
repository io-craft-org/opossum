from datetime import datetime
import json
from unittest import TestCase

import frappe

from opossum.opossum import pos_utils
from opossum.opossum.models import POSInvoice, POSInvoiceItem
from opossum.opossum.tests import utils as test_utils


class MakePosInvoiceTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        test_utils.create_test_documents()
        frappe.db.commit()

    def setUp(self):
        self.company = test_utils.get_or_create_company()
        self.default_income_account = test_utils.get_or_create_default_income_account()
        frappe.db.commit()  # necessary to avoid a Lock timeout after 60 seconds of hanging
        self.pos_profile = test_utils.get_or_create_pos_profile()
        self.customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": "_Opossum Test Customer"
            }
        ).insert()
        self.tva_5_5_account_doc = test_utils.get_or_create_tax_account_tva_5_5()
        self.item1 = test_utils.get_or_create_item_1()
        self.item_price = test_utils.get_or_create_item_price(self.item1.item_code)

    def test_make_simple_invoice(self):

        pos_invoice = POSInvoice(
            posting_date=datetime.now(),
            invoice_items=[
                POSInvoiceItem(qty=10, external_id="_opossum-test-item-1", code="_Opossum Test Item 1"),
            ]
        )

        invoice = pos_utils.make_pos_invoice(
            pos_invoice,
            company=self.company.name,
            pos_profile=self.pos_profile.name,
            customer=self.customer.name,
            default_income_account=self.default_income_account.name
        )

        # Check the invoice items list
        assert len(invoice.items) == 1
        inv_item = invoice.items[0]
        assert inv_item.item_code == "_Opossum Test Item 1"  # FIXME: hardcoded value
        assert inv_item.qty == 10.0

        # Check the tax and total amounts
        qty = pos_invoice.invoice_items[0].qty
        price = self.item_price.price_list_rate
        expected_raw_tax_amount = qty * price * 0.055  # FIXME: hardcoded value 0.055

        def fceil(n, d):
            """ For instance `fceil(1.4587, 2)` returns `1.46`."""
            import math
            f = 10 ** d
            return math.ceil(n * f) / f

        assert len(invoice.taxes) == 1

        inv_tax = invoice.taxes[0]
        assert inv_tax.account_head == self.tva_5_5_account_doc.name

        expected_tax_amount = fceil(expected_raw_tax_amount, 2)
        assert inv_tax.tax_amount == expected_tax_amount

        expected_total = qty * price + expected_tax_amount
        assert inv_tax.total == expected_total

        expected_item1_tax_detail = [5.5, expected_raw_tax_amount]  # FIXME: hardcoded value 5.5
        tax_detail = json.loads(inv_tax.item_wise_tax_detail)
        assert self.item1.name in tax_detail
        assert tax_detail[self.item1.name] == expected_item1_tax_detail

    def test_another(self):
        # This is only to test what happens when setUp is executed twice
        pass
