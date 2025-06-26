from odoo import models, fields, api

class HealthCheckup(models.Model):
    _name = 'health.checkup'
    _description = 'Health Checkup'

    type = fields.Selection([
        ('plan', 'Plan'),
        ('actual', ' Actual')
    ], string='Type', required=True)

    shift = fields.Selection([('day_shift', 'Day Shift'), ('night_shift', 'Night Shift')], string='Shift', required=True)
    date = fields.Date(string='Date', required=True)
    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True

    )
    jan = fields.Date(string='Jan')
    feb = fields.Date(string='Feb')
    mar = fields.Date(string='Mar')
    apr = fields.Date(string='Apr')
    may = fields.Date(string='May')
    jun = fields.Date(string='Jun')
    july = fields.Date(string='Jul')
    aug = fields.Date(string='Aug')
    sep = fields.Date(string='Sep')
    oct = fields.Date(string='Oct')
    nov = fields.Date(string='Nov')
    dec = fields.Date(string='Dec')


    @api.model
    def _get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(i), str(i)) for i in range(current_year, current_year + 11)] 