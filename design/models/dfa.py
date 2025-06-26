from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import uuid

_logger = logging.getLogger(__name__)

class DFARecord(models.Model):
    _name = 'dfa.record'
    _description = 'Dependent Failure Analysis (DFA) Record - IATF 16949'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'iatf.sign.off.members']
    _order = 'name desc'

    name = fields.Char(string='DFA ID', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    dfmea_item_id = fields.Many2one('dfmea.item', string='Linked DFMEA Item', required=True, tracking=True)
    analysis_scope = fields.Selection([
        ('dependent_failures', 'Dependent Failures'),
        ('cascading_effects', 'Cascading Effects'),
        ('interaction_failures', 'Interaction Failures'),
        ('common_cause', 'Common Cause Failures')
    ], string='Analysis Scope', required=True, default='dependent_failures', tracking=True)
    analysis_trigger = fields.Selection([
        ('high_rpn_critical_failures', 'High RPN/Critical Failures'),
        ('customer_requirement', 'Customer Requirement'),
        ('regulatory_requirement', 'Regulatory Requirement'),
        ('design_review', 'Design Review Finding')
    ], string='Analysis Trigger', required=True, tracking=True)
    revision = fields.Char(string='Revision', tracking=True)
    team_ids = fields.Many2many('res.users', 'dfa_team_rel', 'dfa_id', 'user_id',
                               string='Analysis Team', required=True)
    team_leader_id = fields.Many2one('res.users', string='Team Leader', required=True, tracking=True)
    responsible_id = fields.Many2one('res.users', string='Responsible Engineer', required=True, tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', tracking=True)
    date = fields.Date(string='DFA Date', default=fields.Date.today, required=True)
    target_completion_date = fields.Date(string='Target Completion', tracking=True)
    date_completed = fields.Date(string='Completion Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('analysis', 'Analysis in Progress'),
        ('mitigation_strategy', 'Mitigation Strategy Development'),
        ('verification', 'Verification'),
        ('approved', 'Approved')
    ], string='Status', default='draft', tracking=True, required=True)
    dfa_line_ids = fields.One2many('dfa.item', 'dfa_record_id', string='Dependent Failure Analysis')
    total_dependent_failures = fields.Integer(string='Total Dependent Failures',
                                             compute='_compute_analysis_metrics', store=True)
    critical_dependencies = fields.Integer(string='Critical Dependencies',
                                          compute='_compute_analysis_metrics', store=True)
    mitigation_strategies_count = fields.Integer(string='Mitigation Strategies',
                                                compute='_compute_analysis_metrics', store=True)
    analysis_summary = fields.Text(string='Analysis Summary')
    key_findings = fields.Text(string='Key Findings')
    recommendations = fields.Text(string='Recommendations')
    dfmea_updated = fields.Boolean(string='DFMEA Updated', default=False, tracking=True)

    @api.depends('dfa_line_ids')
    def _compute_analysis_metrics(self):
        for record in self:
            record.total_dependent_failures = len(record.dfa_line_ids)
            record.critical_dependencies = len(record.dfa_line_ids.filtered(lambda l: l.severity >= 8))
            record.mitigation_strategies_count = len(record.dfa_line_ids.filtered(lambda l: l.mitigation_strategy))

    def _send_email(self, template_xmlid, recipients, ctx=None):
        """Helper method to send email using the specified template."""
        try:
            template = self.env.ref(template_xmlid)
            ctx = ctx or {}
            ctx.update({
                'email_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })
            for recipient in recipients:
                ctx['recipient_name'] = recipient.name
                template.with_context(**ctx).send_mail(
                    self.id,
                    force_send=True,
                    email_values={'recipient_ids': [(6, 0, [recipient.partner_id.id])]}
                )
        except Exception as e:
            _logger.error(f"Failed to send email {template_xmlid}: {str(e)}")

    def action_start_analysis(self):
        if not self.dfa_line_ids:
            raise UserError(_('Please add dependent failure items before starting analysis.'))
        self.state = 'analysis'
        self.message_post(body=_('DFA analysis started.'))
        # Send DFA Analysis Created email
        recipients = self.team_ids | self.team_leader_id | self.responsible_id
        self._send_email('design.email_template_dfa_analysis_created', recipients, {
            'total_dependent_failures': self.total_dependent_failures,
            'critical_dependencies': self.critical_dependencies
        })

    def action_develop_mitigation_strategy(self):
        unanalyzed_items = self.dfa_line_ids.filtered(lambda l: not l.mitigation_strategy)
        if unanalyzed_items:
            raise UserError(_('Mitigation strategies must be defined for all dependent failures.'))
        self.state = 'mitigation_strategy'
        self.message_post(body=_('Mitigation strategies developed.'))

    def action_verify_implementation(self):
        pending_actions = self.dfa_line_ids.filtered(lambda l: not l.action_implemented)
        if pending_actions:
            raise UserError(_('All mitigation actions must be implemented before verification.'))
        self.state = 'verification'
        self.message_post(body=_('Implementation verification in progress.'))

    def action_approve(self):
        if not self.approved_by_id:
            raise UserError(_('Approval authority must be assigned.'))
        if not self.key_findings or not self.recommendations:
            raise UserError(_('Key findings and recommendations must be completed before approval.'))
        for dfa_item in self.dfa_line_ids:
            if dfa_item.action_implemented and dfa_item.dependent_item:
                related_dfmea_line = self.dfmea_item_id.dfmea_line_ids.filtered(
                    lambda l: dfa_item.dependent_item in l.failure_mode
                )
                if related_dfmea_line:
                    related_dfmea_line.write({
                        'severity_post': dfa_item.severity_post_action or dfa_item.severity,
                        'occurrence_post': dfa_item.occurrence_post_action or dfa_item.occurrence,
                        'detection_post': dfa_item.detection_post_action or dfa_item.detection,
                        'recommended_action': (related_dfmea_line.recommended_action or '') + f"\nDFA Finding: {dfa_item.mitigation_strategy}"
                    })
        self.dfmea_updated = True
        self.state = 'approved'
        self.date_completed = fields.Date.today()
        if self.dfmea_item_id and self.dfmea_item_id.state == 'dfa_required':
            self.dfmea_item_id.state = 'dfa_completed'
        self.message_post(body=_('DFA analysis approved and results transferred to DFMEA.'))
        # Send Approval Request and DFA Approved emails
        recipients = self.team_ids | self.team_leader_id | self.responsible_id | self.approved_by_id
        self._send_email('design.email_template_approval_request', [self.approved_by_id])
        self._send_email('design.email_template_dfmea_approved', recipients, {
            'approval_date': self.date_completed,
            'approved_by': self.approved_by_id
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('dfa.record') or _('New')
        records = super().create(vals_list)
        # DFA Analysis Created email is sent from action_start_analysis
        return records

class DFAItem(models.Model):
    _name = 'dfa.item'
    _description = 'DFA Line Item - Dependent Failure Analysis'
    _order = 'severity desc, rpn desc'

    dfa_record_id = fields.Many2one('dfa.record', string='DFA Reference', required=True, ondelete='cascade')
    dependent_item = fields.Char(string='Dependent Item/Component', required=True)
    failure_effect = fields.Text(string='Effect of Dependent Failure', required=True)
    severity = fields.Integer(string='Severity', required=True, help="1-10 scale")
    occurrence = fields.Integer(string='Occurrence', required=True, help="1-10 scale")
    detection = fields.Integer(string='Detection', required=True, help="1-10 scale")
    rpn = fields.Integer(string='RPN', compute='_compute_rpn', store=True)
    mitigation_strategy = fields.Text(string='Mitigation Strategy', required=True)
    recommended_action = fields.Text(string='Recommended Action')
    owner_id = fields.Many2one('res.users', string='Action Owner', required=True)
    due_date = fields.Date(string='Target Completion Date', required=True)
    action_priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Priority', compute='_compute_priority', store=True)
    action_implemented = fields.Boolean(string='Action Implemented', default=False)
    date_action_completed = fields.Date(string='Implementation Date')
    verification_evidence = fields.Binary(string='Verification Evidence Attachment')
    severity_post_action = fields.Integer(string='Severity (Post-Implementation)')
    occurrence_post_action = fields.Integer(string='Occurrence (Post-Implementation)')
    detection_post_action = fields.Integer(string='Detection (Post-Implementation)')
    rpn_post_action = fields.Integer(string='RPN (Post-Implementation)', compute='_compute_rpn_post', store=True)
    risk_reduction = fields.Float(string='Risk Reduction %', compute='_compute_risk_reduction', store=True)

    @api.depends('severity', 'occurrence', 'detection')
    def _compute_rpn(self):
        for rec in self:
            rec.rpn = (rec.severity or 0) * (rec.occurrence or 0) * (rec.detection or 0)

    @api.depends('severity_post_action', 'occurrence_post_action', 'detection_post_action')
    def _compute_rpn_post(self):
        for rec in self:
            rec.rpn_post_action = (rec.severity_post_action or 0) * (rec.occurrence_post_action or 0) * (
                        rec.detection_post_action or 0)

    @api.depends('rpn', 'severity')
    def _compute_priority(self):
        for rec in self:
            if rec.severity >= 9 or rec.rpn >= 200:
                rec.action_priority = 'critical'
            elif rec.rpn >= 100:
                rec.action_priority = 'high'
            elif rec.rpn >= 50:
                rec.action_priority = 'medium'
            else:
                rec.action_priority = 'low'

    @api.depends('rpn', 'rpn_post_action')
    def _compute_risk_reduction(self):
        for rec in self:
            if rec.rpn and rec.rpn_post_action and rec.rpn > 0:
                rec.risk_reduction = ((rec.rpn - rec.rpn_post_action) / rec.rpn) * 100
            else:
                rec.risk_reduction = 0.0

    def action_implement_mitigation(self):
        if not self.mitigation_strategy:
            raise UserError(_('Mitigation strategy must be defined before implementation.'))
        self.action_implemented = True
        self.date_action_completed = fields.Date.today()
        self.dfa_record_id.message_post(
            body=_('Mitigation implemented for dependent item: %s') % self.dependent_item
        )

    def action_verify_effectiveness(self):
        if not self.action_implemented:
            raise UserError(_('Action must be implemented before verification.'))
        self.dfa_record_id.message_post(
            body=_('Effectiveness verification completed for: %s') % self.dependent_item
        )

    @api.constrains('severity', 'occurrence', 'detection', 'severity_post_action', 'occurrence_post_action',
                    'detection_post_action')
    def _check_rating_values(self):
        for record in self:
            fields_to_check = [
                ('severity', record.severity),
                ('occurrence', record.occurrence),
                ('detection', record.detection),
                ('severity_post_action', record.severity_post_action),
                ('occurrence_post_action', record.occurrence_post_action),
                ('detection_post_action', record.detection_post_action)
            ]
            for field_name, value in fields_to_check:
                if value and (value < 1 or value > 10):
                    field_label = record._fields[field_name].string
                    raise ValidationError(_('%s must be between 1 and 10.') % field_label)