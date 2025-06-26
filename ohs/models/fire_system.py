
from odoo import models, fields, api

class FireSystem(models.Model):
    _name = 'fire.system'
    _description = 'Fire System'

    particular = fields.Selection([('fire extinguisher', 'Fire Extinguisher'), ('fire hose box', 'Fire Hose Box'), ('fire hose reel', 'Fire Hose Reel'), 
    ('hydrant', 'Hydrant'), ('sprinkler', 'Sprinkler')], string='Particular', required=True)
    Frequency = fields.Selection([('two month', 'Every Two Months'), ('quaterly', 'Quaterly')], string='Frequency', required=True)
    date = fields.Date(string='Date', required=True)
    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True
    )

    @api.model
    def _get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(i), str(i)) for i in range(current_year, current_year + 11)]
    
    jan = fields.Date(string='Jan')
    feb = fields.Date(string='Feb')
    mar = fields.Date(string='Mar')    
    apr = fields.Date(string='Apr')
    may = fields.Date(string='May')
    jun = fields.Date(string='Jun')    
    jul = fields.Date(string='Jul')
    aug = fields.Date(string='Aug')
    sep = fields.Date(string='Sep')
    oct = fields.Date(string='Oct')
    nov = fields.Date(string='Nov')
    dec = fields.Date(string='Dec')