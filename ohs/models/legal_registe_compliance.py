from odoo import models, fields

class LegalRegister(models.Model):
    _name = 'legal.register.compliance'
    _description = 'Legal Register Compliance Matrix'

    legal_register_line_ids = fields.One2many('legal.register.complaince.line', 'legal_register_compliance_id', string="Legal Register Compliance Lines")

class LegalRegisterCompliance(models.Model):
    _name = 'legal.register.complaince.line'
    _description = 'Legal Register Compliance Matrix Line'

    legal_register_compliance_id = fields.Many2one('legal.register.compliance', string='Legal Register Compliance')
    serial_no = fields.Integer(string='S. No')
    title = fields.Char(string='Title of Rule / Regulation / Requirement')
    description = fields.Text(string='Brief Description of Requirement')
    responsibility = fields.Many2one('res.users', string='Responsibility')
    status = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')