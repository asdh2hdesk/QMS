from odoo import models, fields, api

class EnvironmentPlan(models.Model):
    _name = 'environment.plan'
    _description = 'Environment Plan'

    particular = fields.Char(string='Particular', required=True)
    frequency = fields.Selection([
        ('quaterly', 'Quaterly'),
        ('half yearly', 'Half Yearly'),
    ], string='Frequency', required=True)
    quantity_quarter= fields.Integer(string='Quantity / Quarter', required=True)
    quartity_year = fields.Integer(string='Quantity / year', required=True)
    done_on_1 = fields.Date(string='Done On', required=True)
    done_on_2 = fields.Date(string='Done On', required=True)
    done_on_3 = fields.Date(string='Done On', required=True)
    done_on_4 = fields.Date(string='Done On', required=True)
    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True
    )
    date = fields.Date(string='Date', required=True)

    jan = fields.Date(string='Jan')
    feb = fields.Date(string='Feb')
    mar = fields.Date(string='Mar')
    apr = fields.Date(string='Apr')
    may = fields.Date(string='May')
    jun = fields.Date(string='Jun')
    july = fields.Date(string='July')
    aug = fields.Date(string='Aug')
    sep = fields.Date(string='Sep')
    oct = fields.Date(string='Oct')
    nov = fields.Date(string='Nov')
    dec = fields.Date(string='Dec')

    @api.model
    def _get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(i), str(i)) for i in range(current_year, current_year + 11)]

