from odoo import models, fields, api,_
class ESGMetricDefinition(models.Model):
    _name = 'esg.metric'
    _description = 'ESG Metric Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    goal_id = fields.Many2one('esg.goal')
    type = fields.Selection([
        ('manual', 'Manual'),
        ('automated', 'Automated'),
        ('calculated', 'Calculated')
    ], required=True)
    frequency = fields.Selection([
        ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')])
    data_owner_id = fields.Many2one('res.users')
    method = fields.Text()
    calculation_formula = fields.Text()
    framework_id = fields.Many2one('esg.framework')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)