import frappe
from frappe import _, db
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact

@frappe.whitelist()
def payment_on_submit(self, method):
	fwd_uti(self)
	total_uti(self)

@frappe.whitelist()
def payment_on_cancel(self, method):
	fwd_uti_cancel(self)
	total_uti(self)

@frappe.whitelist()
def forward_update(self, method):
	cover_so(self)
	cover_po(self)

@frappe.whitelist()	
def si_on_submit(self, method):
	create_drawback_jv(self)
	create_igst_jv(self)

@frappe.whitelist()	
def si_on_cancel(self, method):
	cancel_jvs(self)

def create_drawback_jv(self):
	if self.currency != "INR" and self.total_duty_drawback:
		drawback_receivable_account = db.get_value("Company", { "company_name": self.company}, "duty_drawback_receivable_account")
		drawback_income_account = db.get_value("Company", { "company_name": self.company}, "duty_drawback_income_account")
		drawback_cost_center = db.get_value("Company", { "company_name": self.company}, "duty_drawback_cost_center")
		if not drawback_receivable_account:
			frappe.throw(_("Set Duty Drawback Receivable Account in Company"))
		elif not drawback_income_account:
			frappe.throw(_("Set Duty Drawback Income Account in Company"))
		elif not drawback_cost_center:
			frappe.throw(_("Set Duty Drawback Cost Center in Company"))
		else:
			jv = frappe.new_doc("Journal Entry")
			jv.voucher_type = "Duty Drawback Entry"
			jv.posting_date = self.posting_date
			jv.company = self.company
			jv.cheque_no = self.name
			jv.cheque_date = self.posting_date
			jv.user_remark = "Duty draw back against" + self.name + " for " + self.customer
			jv.append("accounts", {
				"account": drawback_receivable_account,
				"cost_center": drawback_cost_center,
				"debit_in_account_currency": self.total_duty_drawback
			})
			jv.append("accounts", {
				"account": drawback_income_account,
				"cost_center": drawback_cost_center,
				"credit_in_account_currency": self.total_duty_drawback
			})
			jv.save(ignore_permissions=True)
			self.db_set('duty_drawback_jv', jv.name)
			jv.submit()
			db.commit()

def create_igst_jv(self):
	if self.export_type == "With Payment of Tax" and self.currency != "INR" and self.total_igst_amount and self.shipping_bill_date:
		refund_receivable_account = db.get_value("Company", { "company_name": self.company}, "refund_receivable_on_export_account")
		igst_payable_account = db.get_value("Company", { "company_name": self.company}, "igst_payable_account")
		cost_center = db.get_value("Company", { "company_name": self.company}, "cost_center")
		if not refund_receivable_account:
			frappe.throw(_("Set Refund Receivable on Export Account in Company"))
		elif not igst_payable_account:
			frappe.throw(_("Set IGST Payable Account in Company"))
		elif not cost_center:
			frappe.throw(_("Set Default Cost Center in Company"))
		else:
			jv = frappe.new_doc("Journal Entry")
			jv.voucher_type = "GST Payable Entry"
			jv.posting_date = self.shipping_bill_date
			jv.company = self.company
			jv.cheque_no = self.name
			jv.cheque_date = self.shipping_bill_date
			jv.user_remark = "IGST Payable against" + self.name + " for " + self.customer
			jv.append("accounts", {
				"account": refund_receivable_account,
				"cost_center": cost_center,
				"debit_in_account_currency": self.total_igst_amount
			})
			jv.append("accounts", {
				"account": igst_payable_account,
				"cost_center": cost_center,
				"credit_in_account_currency": self.total_igst_amount
			})
			jv.save(ignore_permissions=True)
			self.db_set('gst_jv', jv.name)
			jv.submit()
			db.commit()

def cancel_jvs(self):
	if self.duty_drawback_jv:
		jv = frappe.get_doc("Journal Entry", self.duty_drawback_jv)
		jv.cancel()
		self.db_set('duty_drawback_jv', '')
	if self.gst_jv:
		jv = frappe.get_doc("Journal Entry", self.gst_jv)
		jv.cancel()
		self.db_set('gst_jv', '')
	db.commit()

#On Submit Payment
def fwd_uti(self):
	if self.forward_contract:
		target_doc = frappe.get_doc("Forward Booking", self.forward_contract)
		existing_row_id = db.get_value("Forward Booking Utilization", filters={"parent": self.forward_contract, "payment_entry": self.name}, fieldname="name")

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
		db.commit()

#Calculate Total
def total_uti(self):
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
		db.commit()


#CANCEL Payment
def fwd_uti_cancel(self):
	if self.forward_contract:
		existing_row_id = db.get_value("Forward Booking Utilization", filters={"parent": self.forward_contract, "payment_entry": self.name}, fieldname="name")
		frappe.delete_doc("Forward Booking Utilization", existing_row_id)
		db.commit()

# On Save event of Forward Bookin Underlying
def cover_so(self):
	for row in self.sales_orders: 
		so = frappe.get_doc("Sales Order", row.sales_order)
		so.forward_contract = self.name
		so.amount_covered = row.amount_covered
		so.amount_unhedged = so.grand_total - row.amount_covered
		so.save(ignore_permissions=True)
		db.commit()

def cover_po(self):
	for row in self.purchase_orders: 
		po = frappe.get_doc("Purchase Order", row.purchase_order)
		po.forward_contract = self.name
		po.amount_covered = row.amount_covered
		po.amount_unhedged = so.grand_total - row.amount_covered
		po.save(ignore_permissions=True)
		db.commit()

@frappe.whitelist()
def get_party_details(party=None, party_type="Customer", ignore_permissions=False):

	if not party:
		return {}

	if not db.exists(party_type, party):
		frappe.throw(_("{0}: {1} does not exists").format(party_type, party))

	return _get_party_details(party, party_type, ignore_permissions)

def _get_party_details(party=None, party_type="Customer", ignore_permissions=False):

	out = frappe._dict({
		party_type.lower(): party
	})

	party = out[party_type.lower()]

	if not ignore_permissions and not frappe.has_permission(party_type, "read", party):
		frappe.throw(_("Not permitted for {0}").format(party), frappe.PermissionError)

	party = frappe.get_doc(party_type, party)
	
	set_address_details(out, party, party_type)
	set_contact_details(out, party, party_type)
	set_other_values(out, party, party_type)

	return out

def set_address_details(out, party, party_type):
	billing_address_field = "customer_address" if party_type == "Lead" \
		else party_type.lower() + "_address"
	out[billing_address_field] = get_default_address(party_type, party.name)
	
	# address display
	out.address_display = get_address_display(out[billing_address_field])

def set_contact_details(out, party, party_type):
	out.contact_person = get_default_contact(party_type, party.name)

	if not out.contact_person:
		out.update({
			"contact_person": None,
			"contact_display": None,
			"contact_email": None,
			"contact_mobile": None,
			"contact_phone": None,
			"contact_designation": None,
			"contact_department": None
		})
	else:
		out.update(get_contact_details(out.contact_person))

def set_other_values(out, party, party_type):
	# copy
	if party_type=="Customer":
		to_copy = ["customer_name", "customer_group", "territory", "language"]
	else:
		to_copy = ["supplier_name", "supplier_type", "language"]
	for f in to_copy:
		out[f] = party.get(f)

@frappe.whitelist()
def get_quality_parameter(item_group):

	return db.get_list("Quality Parameter", filters={'item_group': item_group}, fields='name')

@frappe.whitelist()
def get_packing_parameter(item_group):
	return db.get_list("Packing Parameter", filters={'item_group': item_group}, fields='name')