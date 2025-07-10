from odoo import models, fields, api, _
class ESGMaterialTopic(models.Model):
    _name = 'esg.material.topic'
    _description = 'Material ESG Topics'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    description = fields.Text(tracking=True)
    impact_on_stakeholders = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High')
    ], tracking=True)
    impact_on_business = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High')
    ], tracking=True)
    framework_id = fields.Many2one('esg.framework', string="Framework")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)