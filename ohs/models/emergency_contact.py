from odoo import models, fields, api

class EmergencyContact(models.Model):
    _name = 'emergency.contact'
    _description = 'Emergency Contact'

    department_id = fields.Many2one('hr.employee', string='Department', required=True)
    location_id = fields.Many2one('res.company', string='Location', required=True)
    contact = fields.Integer(string='Contact Number', required=True)