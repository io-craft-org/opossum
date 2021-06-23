// Copyright (c) 2021, ioCraft and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hiboutik Settings', {
	refresh: function(frm) {
      cur_frm.add_custom_button(__("Sync all items"), function() {
				  frappe.call({
						  type:"POST",
						  method:"opossum.opossum.doctype.hiboutik_settings.hiboutik_settings.sync_all_items",
              args: {
					        json_doc: frm.doc
				      },
				  }).done(() => {
						  frappe.show_alert({
							    indicator: "green",
							    message: __("All items synched to Hiboutik")
						  });
				  }).fail(() => {
						  frappe.show_alert({
							    indicator: "red",
							    message: __("Items failed to synchronize to Hiboutik")
						  });
				  });
      });
	 }
});
