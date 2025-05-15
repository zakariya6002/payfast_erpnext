frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
            frm.add_custom_button(__('Pay with PayFast'), function() {
                frappe.call({
                    method: "payfast_integration.payment_gateway.payfast.create_payfast_payment_link",
                    args: {
                        invoice_name: frm.doc.name,
                        amount: frm.doc.outstanding_amount,
                        item_name: frm.doc.items[0].item_name
                    },
                    callback: function(r) {
                        if (r.message) {
                            window.open(r.message, '_blank');
                        }
                    }
                });
            });
        }
    }
});
