from odoo import models, fields, api

class EmergencyContact(models.Model):
    _name = 'emergency.contact'
    _description = 'Emergency Contact'

    department_id = fields.Many2one('custom.employee', string='Department', required=True)
    location_id = fields.Many2one('custom.company', string='Location', required=True)
    contact = fields.Integer(string='Contact Number', required=True)


class CustomEmployee(models.Model):
    _name = 'custom.employee'
    _description = 'Custom Employee'

    name = fields.Char(string='Name', required=True)

class CustomCompany(models.Model):
    _name = 'custom.company'
    _description = 'Custom Company'

    name = fields.Char(string='Company Name', required=True)