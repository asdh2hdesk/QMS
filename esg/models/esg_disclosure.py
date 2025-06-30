from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ESGDisclosure(models.Model):
    _name = 'esg.disclosure'
    _description = 'ESG Disclosure'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    disclosure_type = fields.Selection([
        ('annual', 'Annual'), ('quarterly', 'Quarterly'), ('monthly', 'Monthly')
    ])
    reporting_year = fields.Char()
    metric_ids = fields.Many2many('esg.metric')
    is_approved = fields.Boolean(default=False)
    approved_by = fields.Many2one('res.users')
    approval_date = fields.Date()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)