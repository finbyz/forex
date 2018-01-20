from frappe import _

def get_data():
	return {
		'fieldname': 'forward_booking',
		'non_standard_fieldnames': {
			'Sales Order': 'forward_contract',
			'Purchase Order': 'forward_contract',
			'Payment Entry': 'forward_contract',
		},		
		'transactions': [
			{
				'label': _('UNDERLYING'),
				'items': ['Sales Order', 'Purchase Order']
			},
			{
				'label': _('UTILIZATION'),
				'items': ['Payment Entry']
			}
		]
	}