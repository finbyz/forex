import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact

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

@frappe.whitelist()
def get_party_details(party=None, party_type="Customer", ignore_permissions=False):

	if not party:
		return {}

	if not frappe.db.exists(party_type, party):
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