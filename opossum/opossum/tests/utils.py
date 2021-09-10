import datetime

import frappe


def get_or_create_default_warehouse():
    company = get_or_create_company()
    wh_doc, created = get_or_create(
        "Warehouse",
        {
            "company": company.name,
            "warehouse_name": "_opossum test warehouse"
        },
        {
            "doctype": "Warehouse",
            "company": company.name,
            "warehouse_name": "_opossum test warehouse"
        }
    )
    if created:
        wh_doc.insert()
        frappe.db.commit()
        print(f"Warehouse {wh_doc.name} created")

    return wh_doc


def get_or_create_default_cost_center():
    company = get_or_create_company()
    cost_center_list = frappe.db.get_list(
        "Cost Center",
        {
            "company": company.name,
            "is_group": 0
        }
    )
    if cost_center_list:
        return frappe.get_doc("Cost Center", cost_center_list[0]["name"])
    parent_cost_center_name = frappe.db.get_list(
        "Cost Center",
        {
            "company": company.name
        }
    )[0]["name"]
    cc_doc = frappe.get_doc(
        {
            "doctype": "Cost Center",
            "is_group": 0,
            "cost_center_name": "_opossum test cost center",
            "parent_cost_center": parent_cost_center_name
        }
    ).insert()
    print(f"Cost Center {cc_doc.name} created")
    return cc_doc


def get_or_create_pos_profile():
    company = get_or_create_company()
    wh_doc = get_or_create_default_warehouse()
    cc_doc = get_or_create_default_cost_center()

    try:
        pos_profile_doc = frappe.get_doc(
            "POS Profile",
            "_Opossum Test POS Profile"
        )
    except frappe.DoesNotExistError:
        pos_profile_doc = frappe.get_doc(
            {
                "doctype": "POS Profile",
                "name": "_Opossum Test POS Profile",
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
                "company": company.name,
                "currency": "EUR",
                "write_off_cost_center": cc_doc.name,
                "write_off_account": "Sales - OTC",
                "warehouse": wh_doc.name,
            }
        ).insert()

    return pos_profile_doc


COMPANY_NAME = "Opossum Tests Company"
TVA_5_5_NAME = "TVA 5,5%"
PREFIX = "_Opossum Test"  # Useful to delete all test documents


def _pre(s):
    return f"{PREFIX} {s}"


def get_or_create(doctype, name_or_filters, default_dict):
    created = False
    if isinstance(name_or_filters, dict):
        filters = name_or_filters
        results = frappe.db.get_list(doctype, filters)
        if len(results) > 0:
            name = results[0]["name"]
            return frappe.get_doc(doctype, name), created
    else:
        name = name_or_filters
        try:
            return frappe.get_doc(doctype, name), created
        except frappe.DoesNotExistError:
            pass

    created = True
    return frappe.get_doc(default_dict), created


def get_or_create_company():
    company_doc, created = get_or_create(
        "Company",
        COMPANY_NAME,
        {
            "doctype": "Company",
            "company_name": COMPANY_NAME,
            "default_currency": "EUR"
        }
    )
    if created:
        company_doc.insert()
        print(f"Company {company_doc.name} created")

    return company_doc


def get_or_create_cash_default_account():
    company = get_or_create_company()
    cash = frappe.get_doc("Mode of Payment", "Cash")
    for account in cash.accounts:
        if account.company == company.name:
            return
    cash_accounts = frappe.db.get_list(
        "Account",
        {
            "company": company.name,
            "account_type": "Cash",
            "is_group": 0
        }
    )
    first_cash_account_name = cash_accounts[0]["name"]
    cash.append(
        "accounts",
        {
            "company": company.name,
            "default_account": first_cash_account_name
        }
    )
    cash.save()


def get_or_create_company_bank_account():
    company = get_or_create_company()
    bank_accounts = frappe.db.get_list(
        "Account",
        {
            "company": company.name,
            "account_type": "Bank",
            "is_group": 0
        }
    )
    if bank_accounts:
        return frappe.get_doc("Account", bank_accounts[0]["name"])
    bank_accounts_group_name = frappe.db.get_list(
        "Account",
        {
            "company": company.name,
            "account_type": "Bank",
            "is_group": 1
        }
    )[0]["name"]
    bank_account_doc = frappe.get_doc(
        {
            "doctype": "Account",
            "company": company.name,
            "account_name": "The Bank Account",
            "account_type": "Bank",
            "is_group": 0,
            "parent_account": bank_accounts_group_name
        }
    ).insert()
    print(f"Bank Account {bank_account_doc.name} created")
    return bank_account_doc


def get_or_create_credit_card_default_account():
    company = get_or_create_company()
    cc = frappe.get_doc("Mode of Payment", "Credit Card")
    for account in cc.accounts:
        if account.company == company.name:
            return
    bank_account = get_or_create_company_bank_account()
    cc.append(
        "accounts",
        {
            "company": company.name,
            "default_account": bank_account.name
        }
    )
    cc.save()


def get_or_create_default_income_account():
    company = get_or_create_company()
    income_account_list = frappe.db.get_list(
        "Account",
        {
            "company": company.name,
            "root_type": "Income",
            "is_group": 0
        }
    )
    if income_account_list:
        return frappe.get_doc("Account", income_account_list[0]["name"])
    income_account_group_name = frappe.db.get_list(
        "Account",
        {
            "company": company.name,
            "root_type": "Income",
            "is_group": 1
        }
    )[0]["name"]
    default_income_account_doc = frappe.get_doc(
        {
            "doctype": "Account",
            "is_group": 0,
            "account_name": "Default Income Account",
            "parent_account": income_account_group_name
        }
    ).insert()
    print(f"Income Account {default_income_account_doc} created")
    return default_income_account_doc


def get_or_create_tax_account_tva_5_5():
    company = get_or_create_company()
    default_tax_account_name = frappe.db.get_list(
        "Account",
        {
            "company": company.name,
            "account_type": "Tax",
            "is_group": 1
        }
    )[0]["name"]
    tax_account_doc, created = get_or_create(
        "Account",
        {
            "account_name": TVA_5_5_NAME,
            "company": company.name
        },
        {
            "doctype": "Account",
            "account_name": TVA_5_5_NAME,
            "company": company.name,
            "account_type": "Tax",
            "parent_account": default_tax_account_name
        }
    )
    if created:
        tax_account_doc.insert()
        print(f"Tax Account {tax_account_doc.name} created")

    return tax_account_doc


def get_or_create_tax_template_tva_5_5():
    company = get_or_create_company()
    tva_5_5_account = get_or_create_tax_account_tva_5_5()
    template_doc, created = get_or_create(
        doctype="Item Tax Template",
        name_or_filters={
            "title": "Modèle TVA 5,5%",
            "company": company.name
        },
        default_dict={
            "doctype": "Item Tax Template",
            "title": "Modèle TVA 5,5%",
            "company": company.name
        }
    )
    if created:
        template_doc.append(
            "taxes",
            {
                "tax_type": tva_5_5_account.name,
                "tax_rate": 5.5
            }
        )
        template_doc.insert()
        print(f"Item Tax Template {template_doc.name} created")
        return template_doc
    else:
        return template_doc


def get_or_create_item_price(item_code):
    price = 2.5
    price_list_doc = get_default_selling_price_list()
    item_price_doc, created = get_or_create(
        doctype="Item Price",
        name_or_filters={"item_code": item_code},
        default_dict={
                "doctype": "Item Price",
                "item_code": item_code,
                "price_list": price_list_doc.name,
                "buying": 0,
                "selling": 1,
                # "currency": "EUR",
                "price_list_rate": price,
                "valid_from": datetime.date(2020, 7, 29)  # FIXME
        }
    )
    if created:
        item_price_doc.insert()
        frappe.db.commit()
        print(f"Item Price {item_price_doc.name} created")

    return item_price_doc


def get_or_create_item_1():
    company = get_or_create_company()
    warehouse = get_or_create_default_warehouse()
    tva_5_5_template = get_or_create_tax_template_tva_5_5()
    item_doc, created = get_or_create(
        doctype="Item",
        name_or_filters="_Opossum Test Item 1",
        default_dict={
            "doctype": "Item",
            "item_code": "_Opossum Test Item 1",
            "hiboutik_id": "_opossum-test-item-1",
            "item_group": "Products"
        }
    )
    if created:
        item_doc.append(
            "item_defaults",
            {
                "company": company.name
            }
        )
        item_doc.append(
            "taxes",
            {
                "item_tax_template": tva_5_5_template.name
            }
        )
        item_doc.insert()
        print(f"Item {item_doc.name} created")
        frappe.db.commit()

    get_or_create_item_price(item_doc.item_code)

    # if no stock create a stock entry
    stock_entry_doc = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "posting_date": "2021-09-07",  # Must be in the past.
            "company": "Opossum Tests Company",
            "stock_entry_type": "Material Receipt",
            "to_warehouse": warehouse.name,
            "items": [
                {
                    "item_code": item_doc.item_code,
                    "qty": 1000.0,
                    "allow_zero_valuation_rate": 1
                }
            ]
        }
    )
    stock_entry_doc.save()
    stock_entry_doc.submit()

    return item_doc


def get_or_create_price_list():
    price_list_doc, created = get_or_create(
        doctype="Price List",
        name_or_filters="_Opossum Test Price List",
        default_dict={
            "doctype": "Price List",
            "price_list_name": "_Opossum Test Price List",
            "currency": "EUR",
            "selling": 1
        }
    )
    if created:
        price_list_doc.insert()
        print(f"Price List {price_list_doc.name} created")
    return price_list_doc


def get_default_selling_price_list():
    price_list_name = frappe.get_list("Price List", {"selling": 1})[0]
    return frappe.get_doc("Price List", price_list_name)


def delete_pos_invoice(pos_inv_name):  # Not used yet
    doc = frappe.get_doc("POS Invoice", pos_inv_name)
    for item in doc.items:
        ret = frappe.db.delete("POS Invoice Item", {"name": item.name})
        print(f"delete POS Invoice Item {item.name}: {str(ret)}")
    for tax in doc.taxes:
        ret = frappe.db.delete("Sales Taxes and Charges", {"name": tax.name})
        print(f"delete Sales Taxes and Charges {tax.name}: {str(ret)}")
    for payment in doc.payments:
        ret = frappe.db.delete("Sales Invoice Payment", {"name": payment.name})
        print(f"delete Sales Taxes and Charges {payment.name}: {str(ret)}")
    ret = frappe.db.delete("POS Invoice", pos_inv_name)
    print(f"delete POS Invoice {pos_inv_name}: {str(ret)}")


def delete_all_pos_invoice():  # Not used yet
    pos_inv_list = frappe.db.get_list("POS Invoice")
    for pos_inv_name in pos_inv_list:
        delete_pos_invoice(pos_inv_name)


def delete_all_test_documents():  # Not used yet
    delete_all_pos_invoice()
    frappe.db.delete("POS Invoice", {"owner": "Administrator"})
    frappe.db.delete("POS Closing Entry", {"owner": "test@example.com"})
    frappe.db.delete("POS Opening Entry", {"owner": "test@example.com"})


def create_test_documents():
    get_or_create_company()
    get_or_create_default_warehouse()
    get_or_create_default_cost_center()
    get_or_create_pos_profile()
    get_or_create_cash_default_account()
    get_or_create_credit_card_default_account()
    get_or_create_default_income_account()
    get_or_create_tax_account_tva_5_5()
    get_or_create_tax_template_tva_5_5()
    get_or_create_price_list()
