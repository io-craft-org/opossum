frappe.ui.form.on("Item", "refresh", function(frm) {
    frm.add_custom_button(__('Sync to Hiboutik'), () => {
				frappe.call({
						type:"POST",
						method:"opossum.opossum.doctype.hiboutik_settings.hiboutik_settings.sync_item",
            args: {
					      json_doc: frm.doc
				    },
				}).done(() => {
						frappe.show_alert({
							  indicator: "green",
							  message: __("Item synched to Hiboutik")
						});
				}).fail(() => {
						frappe.show_alert({
							  indicator: "red",
							  message: __("Item failed to synchronize to Hiboutik")
						});
				});
    }, __("POS"));
});
