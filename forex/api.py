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

@frappe.whitelist()
def forward_update(self, method):
	cover_so(self, method)
	cover_po(self,method)

@frappe.whitelist()	
def si_on_submit(self, method):
	create_jv(self, method)
	
@frappe.whitelist()	
def si_on_cancel(self, method):
	cancel_jv(self, method)
	
def create_jv(self, method):
	jv = frappe.new_doc("Journal Entry")
	jv.voucher_type = "Duty Drawback Entry"
	jv.posting_date = self.posting_date
	jv.company = self.company
	jv.cheque_no = self.name
	jv.cheque_date = self.posting_date
	jv.user_remark = "Duty draw back against" + self.name + " for " + self.customer
	jv.append("accounts", {
		"account": frappe.db.get_value("Company", self.company, 'duty_drawback_receivable_account'),
		"cost_center": "Export - BE",
		"debit_in_account_currency": self.total_duty_drawback
	})
	jv.append("accounts", {
		"account": frappe.db.get_value("Company", self.company, 'duty_drawback_income_account'),
		"cost_center": "Export - BE",
		"credit_in_account_currency": self.total_duty_drawback
	})
	jv.save(ignore_permissions=True)
	jv.submit()
	self.duty_drawback_jv = jv.name
	self.save(ignore_permissions=True)
	frappe.db.commit()
	
def cancel_jv(self, method):
	jv = frappe.get_doc("Journal Entry", self.duty_drawback_jv)
	jv.cancel()
	frappe.db.commit()

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
def cover_so(self, method):
	for row in self.sales_orders: 
		so = frappe.get_doc("Sales Order", row.sales_order)
		so.forward_contract = self.name
		so.amount_covered = row.amount_covered
		so.amount_unhedged = so.grand_total - row.amount_covered
		so.save()
		frappe.db.commit()

def cover_po(self, method):
	for row in self.purchase_orders: 
		po = frappe.get_doc("Purchase Order", row.purchase_order)
		po.forward_contract = self.name
		po.amount_covered = row.amount_covered
		po.amount_unhedged = so.grand_total - row.amount_covered
		po.save()
		frappe.db.commit()
