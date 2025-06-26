from odoo import models, fields, api,_
from odoo.exceptions import ValidationError

class Governance(models.Model):
    _name = 'esg.governance'
    _description = 'Governance Metrics'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Metric Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', required=True, copy=False,
                      readonly=True, default=lambda self: _('New'))
    area = fields.Selection([
        ('policy_compliance', 'Policy Compliance'),
        ('audit_score', 'Audit Score'),
        ('ethics_report', 'Ethics Report'),
        ('risk_assessment', 'Risk Assessment'),
        ('board_oversight', 'Board Oversight'),
    ], string='Area', required=True, tracking=True)
    status = fields.Selection([
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('pending', 'Pending Review'),
    ], string='Status', required=True, tracking=True)
    responsible = fields.Many2one('res.users', string='Responsible', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True, tracking=True)
    reporting_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Reporting Period', required=True, default='yearly')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Risk Level')
    compliance_score = fields.Float(string='Compliance Score (%)', digits=(5, 2))
    comments = fields.Text(string='Comments')
    related_environmental_ids = fields.Many2many(
        'esg.environmental',
        relation='esg_environmental_governance_rel',  # Same as environmental
        column1='governance_id',                     # Foreign key to esg.governance
        column2='environmental_id',                  # Foreign key to esg.environmental
        string='Related Environmental Metrics'
    )
    related_social_ids = fields.Many2many(
        'esg.social',
        relation='esg_social_governance_rel',  # Same as social
        column1='governance_id',               # Foreign key to esg.governance
        column2='social_id',                   # Foreign key to esg.social
        string='Related Social Metrics'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('esg.governance') or _('New')
        return super().create(vals_list)

    @api.constrains('compliance_score')
    def _check_compliance_score(self):
        for record in self:
            if record.compliance_score and (record.compliance_score < 0 or record.compliance_score > 100):
                raise ValidationError("Compliance score must be between 0 and 100.")

