import frappe
import hashlib
import urllib.parse
from frappe import _

@frappe.whitelist(allow_guest=True)  # ✅ This is REQUIRED to allow API access
def create_payfast_payment_link(invoice_name, amount, item_name):
    return create_payment_url(invoice_name, float(amount), item_name)

def get_gateway_url():
    settings = frappe.get_single("Payfast Settings")
    return "https://sandbox.payfast.co.za/eng/process" if settings.test_mode else "https://www.payfast.co.za/eng/process"

def generate_signature(data: dict, passphrase=""):
    sorted_data = sorted(data.items())
    query_string = urllib.parse.urlencode(sorted_data)
    if passphrase:
        query_string += f"&passphrase={passphrase}"
    return hashlib.md5(query_string.encode()).hexdigest()

def create_payment_url(reference, amount, item_name):
    settings = frappe.get_single("Payfast Settings")

    data = {
        "merchant_id": settings.merchant_id,
        "merchant_key": settings.merchant_key,
        "return_url": frappe.utils.get_url("/payment-success"),
        "cancel_url": frappe.utils.get_url("/payment-cancel"),
        "notify_url": frappe.utils.get_url("/api/method/payfast_integration.payment_gateway.payfast.verify_payment"),
        "amount": "{:.2f}".format(amount),
        "item_name": item_name,
        "m_payment_id": reference
    }

    signature = generate_signature(data, settings.passphrase)
    data["signature"] = signature

    return get_gateway_url() + "?" + urllib.parse.urlencode(data)

@frappe.whitelist(allow_guest=True)
def verify_payment():
    raw_data = frappe.local.form_dict
    settings = frappe.get_single("Payfast Settings")

    # Clean input for signature calculation
    data = {k: v for k, v in raw_data.items() if v and k not in ["signature", "cmd"]}

    received_signature = raw_data.get("signature")
    calculated_signature = generate_signature(data, settings.passphrase)

    if received_signature != calculated_signature:
        frappe.throw(_("Invalid signature"))

    if raw_data.get("payment_status") == "COMPLETE":
        ref = raw_data.get("m_payment_id")
        if frappe.db.exists("Sales Invoice", ref):
            doc = frappe.get_doc("Sales Invoice", ref)
            if doc.docstatus == 1 and doc.outstanding_amount > 0:
                # ✅ Elevate permissions to Administrator
                original_user = frappe.session.user
                frappe.set_user("Administrator")

                try:
                    pe = frappe.new_doc("Payment Entry")
                    pe.payment_type = "Receive"
                    pe.party_type = "Customer"
                    pe.party = doc.customer
                    pe.posting_date = frappe.utils.nowdate()
                    pe.paid_amount = float(raw_data.get("amount_gross"))
                    pe.received_amount = float(raw_data.get("amount_gross"))
                    pe.reference_no = raw_data.get("pf_payment_id", frappe.generate_hash(length=10))
                    pe.reference_date = frappe.utils.nowdate()
                    pe.mode_of_payment = "PayFast"
                    pe.company = doc.company
                    pe.target_exchange_rate = 1.0  # ✅ This fixes the error
                    pe.paid_to = "Bank Account - G"  # 🔁 use your actual bank account name
                    pe.paid_to_account_currency = "ZAR"
                    pe.append("references", {
                        "reference_doctype": "Sales Invoice",
                        "reference_name": ref,
                        "allocated_amount": float(raw_data.get("amount_gross"))
                    })
                    pe.insert()
                    pe.submit()
                finally:
                    frappe.set_user(original_user)  # 🔁 Reset user context

    return {"status": "Payment processed"}