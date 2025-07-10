from odoo import fields, models, api,_
class ESGTarget(models.Model):
    _name = 'esg.target'
    _description = 'ESG Targets'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    goal_id = fields.Many2one('esg.goal', required=True)
    start_date = fields.Date()
    end_date = fields.Date()
    base_value = fields.Float()
    target_value = fields.Float()
    actual_value = fields.Float()
    unit = fields.Char(default="%")
    owner_id = fields.Many2one('res.users')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)