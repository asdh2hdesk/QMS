from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Environmental(models.Model):
    _name = 'esg.environmental'
    _description = 'Environmental Metrics'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Metric Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', required=True, copy=False,
                      readonly=True, default=lambda self: _('New'))
    category = fields.Selection([
        ('emission_scope1', 'Emission - Scope 1'),
        ('emission_scope2', 'Emission - Scope 2'),
        ('emission_scope3', 'Emission - Scope 3'),
        ('waste', 'Waste Management'),
        ('energy', 'Energy Usage'),
        ('water', 'Water Usage'),
    ], string='Category', required=True, tracking=True)
    value = fields.Float(string='Value', digits=(12, 2), tracking=True)
    unit = fields.Selection([
        ('kg_co2e', 'kg CO2e'),
        ('tonnes', 'Tonnes'),
        ('kwh', 'kWh'),
        ('liters', 'Liters'),
        ('percent', 'Percentage'),
    ], string='Unit', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True, tracking=True)
    reporting_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Reporting Period', required=True, default='yearly')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    reduction_target = fields.Float(string='Reduction Target (%)', digits=(5, 2))
    carbon_offset = fields.Float(string='Carbon Offset (kg CO2e)', digits=(12, 2))
    verification_status = fields.Selection([
        ('draft', 'Draft'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], string='Verification Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')
    related_social_ids = fields.Many2many(
        'esg.social',
        relation='esg_environmental_social_rel',  # Unique relation table
        column1='environmental_id',              # Foreign key to esg.environmental
        column2='social_id',                     # Foreign key to esg.social
        string='Related Social Metrics'
    )
    related_governance_ids = fields.Many2many(
        'esg.governance',
        relation='esg_environmental_governance_rel',  # Unique relation table
        column1='environmental_id',                  # Foreign key to esg.environmental
        column2='governance_id',                     # Foreign key to esg.governance
        string='Related Governance Metrics'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('esg.environmental') or _('New')
        return super().create(vals_list)
    @api.constrains('value')
    def _check_value(self):
        for record in self:
            if record.value < 0:
                raise ValidationError("Value cannot be negative.")

