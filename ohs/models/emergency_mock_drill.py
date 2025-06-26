from odoo import models, fields, api

class EmergencyMockDrill(models.Model):
    _name = 'emergency.mock.drill'
    _description = 'Emergency Mock Drill Plan'

    emergency_type = fields.Selection([
        ('fire', 'Fire & Evacuation'),
        ('shock', 'Electrical Shock'),
        ('fall', 'Fall from work at height'),
        ('oil', 'Oil Spillage'),
        ('utility', 'Utility Failure'),
        ('natural', 'Natural Disaster – Floods, Tornadoes, Earthquakes etc')

    ], string='Type of Emergency', required=True)
    shift = fields.Selection([('A', 'A'), ('B', 'B')], string='Shift', required=True)

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
