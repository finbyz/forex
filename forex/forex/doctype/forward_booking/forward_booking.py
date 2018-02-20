# -*- coding: utf-8 -*-
# Copyright (c) 2015, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class ForwardBooking(Document):
	def on_submit(self):
		if self.hedge == "Export":
			for row in self.sales_orders:
				sales_order = frappe.get_doc("Sales Order", row.sales_order)
				amount_hedged = flt(sales_order.amount_covered) + flt(row.amount_covered)
				amount_unhedged = flt(sales_order.grand_total) - flt(amount_hedged) - flt(sales_order.advance_paid) - flt(sales_order.natural_hedge)
				sales_order.amount_covered = flt(amount_hedged)
				sales_order.amount_unhedged = flt(amount_unhedged)
				sales_order.save()
				frappe.db.commit()
				
		else:
			for row in self.purchase_orders:
				purchase_order = frappe.get_doc("Purchase Order", row.purchase_order)
				amount_hedged = flt(purchase_order.amount_covered) + flt(row.amount_covered)
				amount_unhedged = flt(purchase_order.grand_total) - flt(amount_hedged) - flt(purchase_order.advance_paid) - flt(purchase_order.natural_hedge)
				purchase_order.amount_covered = flt(amount_hedged)
				purchase_order.amount_unhedged = flt(amount_unhedged)
				purchase_order.save()
				frappe.db.commit()
				
	def on_cancel(self):
		if self.hedge == "Export":
			for row in self.sales_orders:
				sales_order = frappe.get_doc("Sales Order", row.sales_order)
				amount_hedged = flt(sales_order.amount_covered) - flt(row.amount_covered)
				amount_unhedged = flt(sales_order.grand_total) - flt(amount_hedged) - flt(sales_order.advance_paid) - flt(sales_order.natural_hedge)
				sales_order.amount_covered = flt(amount_hedged)
				sales_order.amount_unhedged = flt(amount_unhedged)
				sales_order.save()
				frappe.db.commit()
				
		else:
			for row in self.purchase_orders:
				purchase_order = frappe.get_doc("Purchase Order", row.purchase_order)
				amount_hedged = flt(purchase_order.amount_covered) - flt(row.amount_covered)
				amount_unhedged = flt(purchase_order.grand_total) - flt(amount_hedged) - flt(purchase_order.advance_paid) - flt(purchase_order.natural_hedge)
				purchase_order.amount_covered = flt(amount_hedged)
				purchase_order.amount_unhedged = flt(amount_unhedged)
				purchase_order.save()
				frappe.db.commit()
