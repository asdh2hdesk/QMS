from odoo import models, fields, api,_
class ESGGoal(models.Model):
    _name = 'esg.goal'
    _description = 'ESG Goals'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    material_topic_id = fields.Many2one('esg.material.topic', tracking=True)
    owner_id = fields.Many2one('res.users', tracking=True)
    start_date = fields.Date(tracking=True)
    end_date = fields.Date(tracking=True)
    description = fields.Text(tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)