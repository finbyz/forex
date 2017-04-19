import frappe
from frappe import _

@frappe.whitelist()
def payment_on_submit(self, method):
	fwd_uti(self, method)
	total_uti(self,method)

@frappe.whitelist()
def payment_on_cancel(self, method):
	fwd_uti_cancel(self, method)
	total_uti(self,method)
	

#On Submit Payment
def fwd_uti(self, method):
	if self.forward_contract:
		target_doc = frappe.get_doc("Forward Booking", self.forward_contract)
		existing_row_id = frappe.db.get_value("Forward Booking Utilization", filters={"parent": self.forward_contract, "payment_entry": self.name}, fieldname="name")

		if not existing_row_id:
			target_doc.append("payment_entries", {
				"date": self.posting_date,
				"party_type": self.party_type,
				"party": self.party,
				"paid_amount" : self.paid_amount,
				"received_amount" : self.received_amount,
				"payment_entry" : self.name
			})
		target_doc.save()
		frappe.db.commit()

#Calculate Total
def total_uti(self,method):
	if self.forward_contract:
		target_doc = frappe.get_doc("Forward Booking", self.forward_contract)
		total = 0
		if target_doc.hedge == "Export":
			for row in target_doc.payment_entries:
				total += row.paid_amount
			target_doc.total_utilization = total
		else:
			for row in target_doc.payment_entries:
				total += row.received_amount
			target_doc.total_utilization = total
		target_doc.amount_outstanding = target_doc.amount - target_doc.total_utilization - target_doc.total_cancelled
		target_doc.save()
		frappe.db.commit()


#CANCEL Payment
def fwd_uti_cancel(self, method):
	if self.forward_contract:
		existing_row_id = frappe.db.get_value("Forward Booking Utilization", filters={"parent": self.forward_contract, "payment_entry": self.name}, fieldname="name")
		frappe.delete_doc("Forward Booking Utilization", existing_row_id)
		frappe.db.commit()
	

# On Save event of Forward Bookin Underlying
@frappe.whitelist()
def cover_so(self, method):
	for row in self.sales_orders: 
		
		# set_value by-passes permissions matrix  
		# frappe.db.set_value("CS DocType C", i.ac, "field_c", i.field_ax1);
		# frappe.db.commit()	

		so = frappe.get_doc("Sales Order", row.sales_order)
		so.forward_contract = self.name,
		so.amount_covered = row.amount_covered
		so.amount_unhedged = so.grand_total - row.amount_covered
		so.update()
		frappe.db.commit()
