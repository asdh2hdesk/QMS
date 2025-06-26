from odoo import models, fields, api,_
from odoo.exceptions import ValidationError

class Social(models.Model):
    _name = 'esg.social'
    _description = 'Social Metrics'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Metric Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', required=True, copy=False,
                      readonly=True, default=lambda self: _('New'))
    metric_type = fields.Selection([
        ('safety_incidents', 'Safety Incidents'),
        ('training_hours', 'Training Hours'),
        ('diversity_ratio', 'Diversity Ratio'),
        ('community_impact', 'Community Impact'),
        ('employee_satisfaction', 'Employee Satisfaction'),
    ], string='Metric Type', required=True, tracking=True)
    value = fields.Float(string='Value', digits=(12, 2), tracking=True)
    unit = fields.Selection([
        ('incidents', 'Incidents'),
        ('hours', 'Hours'),
        ('percent', 'Percentage'),
        ('score', 'Score'),
    ], string='Unit', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True, tracking=True)
    reporting_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Reporting Period', required=True, default='yearly')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    employee_group = fields.Selection([
        ('all', 'All Employees'),
        ('gender', 'By Gender'),
        ('age', 'By Age Group'),
        ('department', 'By Department'),
    ], string='Employee Group')
    community_investment = fields.Float(string='Community Investment ($)', digits=(12, 2))
    verification_status = fields.Selection([
        ('draft', 'Draft'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], string='Verification Status', default='draft', tracking=True)
    remarks = fields.Text(string='Remarks')
    related_environmental_ids = fields.Many2many(
        'esg.environmental',
        relation='esg_environmental_social_rel',  # Same table as above, bidirectional
        column1='social_id',                     # Foreign key to esg.social
        column2='environmental_id',              # Foreign key to esg.environmental
        string='Related Environmental Metrics'
    )
    related_governance_ids = fields.Many2many(
        'esg.governance',
        relation='esg_social_governance_rel',  # Unique relation table
        column1='social_id',                   # Foreign key to esg.social
        column2='governance_id',               # Foreign key to esg.governance
        string='Related Governance Metrics'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('esg.social') or _('New')
        return super().create(vals_list)

    @api.constrains('value')
    def _check_value(self):
        for record in self:
            if record.value < 0:
                raise ValidationError("Value cannot be negative.")

