
from odoo import models, fields, api
class ESGFramework(models.Model):
    _name = 'esg.framework'
    _description = 'ESG Reporting Framework'

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()