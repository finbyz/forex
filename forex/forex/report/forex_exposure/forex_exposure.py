# Copyright (c) 2013, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	return columns, data, None, chart

def get_columns():
	columns = [_("Sales Order") + ":Link/Sales Order:100",  
				_("Order Date") + ":Date:80",
				_("Payment Date") + ":Date:80",				
				_("Customer") + ":Link/Customer:180",
				dict(fieldname = "ccy",
					label = _("CCY"),
					fieldtype = "Link",
					options = "Currency",
					width = 40),
				dict(label = _("Total Amount"), 
					fieldtype = "Currency", 
					options = "ccy", 
					width = 100),
				_("Rate") + ":Float:80",
				_("INR Amount") + ":Currency:100",
				_("Forward") + ":Link/Forward Booking:70",
				dict(label = _("Hedged Amt"), 
					fieldtype = "Currency", 
					options = "ccy", 
					width = 100),
				dict(label = _("Unhedged Amt"), 
					fieldtype = "Currency", 
					options = "ccy", 
					width = 100),
				dict(label = _("Advance Recd"), 
					fieldtype = "Currency", 
					options = "ccy", 
					width = 100),
				dict(label = _("Natural Hedge"), 
					fieldtype = "Currency", 
					options = "ccy", 
					width = 100),
				_("Status") + "::150",
	]
	return columns
	
def get_data(filters):

	where_clause = ''
	where_clause += filters.currency and " and so.currency = '%s'" % \
		filters.currency.replace("'","\'") or " and so.currency != 'INR'"
	
	data = frappe.db.sql("""
		select 
			so.name as "Sales Order",
			so.transaction_date as "Order Date",
			so.delivery_date as "Payment Date",			
			so.customer as "Customer",
			so.currency as "ccy",
			so.grand_total as "Total Amount",
			so.conversion_rate as "Rate",
			so.base_grand_total as "INR Amount",
			so.forward_contract as "Forward",
			so.amount_covered as "Hedged Amt",
			(so.amount_unhedged-so.advance_paid) as "Unhedged Amt",			
			so.advance_paid as "Advance Recd",		
			so.natural_hedge as "Natural Hedge",
			so.status as "Status"
		from	
			`tabSales Order` so
		where
			so.docstatus = 1
			and so.status != 'Closed'
			and so.status != 'Completed'
			and so.amount_covered < so.grand_total
			%s
		order by so.delivery_date asc"""%where_clause)
		
	#d = list(data)
	return data
		
def get_chart_data(data):
	
	total_amount, total_hedged, total_unhedged = [], [], []
	labels = []
	dates = []
	
	for row in data:
		date = getdate(row[2])
		if str(date.strftime("%b-%Y")) not in dates:
			dates.append(str(date.strftime("%b-%Y")))
	
	sorted(dates, key=lambda x: datetime.datetime.strptime(x, '%b-%Y'))
	
	for month in dates:
		amt = 0
		hedged = 0
		unhedged = 0
		for row in data:
			d = getdate(row[2])
			period = str(d.strftime("%b-%Y"))
			if period == month:
				amt += row[5]
				hedged += row[9]
				unhedged += row[10]
				
		total_amount.append(amt)
		total_hedged.append(hedged)
		total_unhedged.append(unhedged)
		labels.append(month)
		
	datasets = []
	
	if total_amount:
		datasets.append({
			'title': "Total Amount",
			'values': total_amount
		})
	
	if total_hedged:
		datasets.append({
			'title': "Total Hedged",
			'values': total_hedged
		})
	
	if total_unhedged:
		datasets.append({
			'title': "Total Unhedged",
			'values': total_unhedged
		})
	
	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}
	chart["type"] = "bar"
	return chart