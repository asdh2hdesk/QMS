from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import uuid

_logger = logging.getLogger(__name__)


class DFMEAItem(models.Model):
    _name = 'dfmea.item'
    _description = 'DFMEA Item - IATF 16949 Compliant'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'iatf.sign.off.members']
    _order = 'name desc'

    name = fields.Char(string='DFMEA ID', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    model_year = fields.Char(string='Model Year', tracking=True)
    customer = fields.Many2one('res.users', string='Customer', tracking=True)
    supplier = fields.Many2one('res.users', string='Supplier', tracking=True)
    rev_date = fields.Date("Revision Date", default=fields.Date.today, tracking=True)
    rev_no = fields.Char("Revision Number", default="1", required=True, tracking=True)
    original_dfmea_date = fields.Date("Original DFMEA Date", tracking=True)
    team_ids = fields.Many2many('res.users', 'dfmea_team_rel', 'dfmea_id', 'user_id',
                                string='Cross-functional Team', required=True)
    team_leader_id = fields.Many2one('res.users', string='Team Leader', required=True, tracking=True)
    responsible_id = fields.Many2one('res.users', string='Responsible Engineer', required=True, tracking=True)
    design_responsible_id = fields.Many2one('res.users', string='Design Responsible', tracking=True)
    date = fields.Date(string='DFMEA Date', default=fields.Date.today, required=True)
    target_completion_date = fields.Date(string='Target Completion Date', tracking=True)
    date_completed = fields.Date(string='Actual Completion Date', tracking=True)
    reviewed_by_id = fields.Many2one('res.users', string='Reviewed By', tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', tracking=True)
    rejected_by_id = fields.Many2one('res.users', string='Rejected By', tracking=True)
    rejection_date = fields.Date(string='Rejection Date', tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    customer_approval_required = fields.Boolean(string='Customer Approval Required', default=False)
    customer_approved_by = fields.Char(string='Customer Approved By')
    customer_approval_date = fields.Date(string='Customer Approval Date')
    system_function = fields.Text(string='System/Component Function', required=True)
    design_intent = fields.Text(string='Design Intent')
    attachments = fields.Many2many(
        'ir.attachment',
        'dfmea_item_attachment_rel',
        'dfmea_item_id',
        'attachment_id',
        string='Attachments'
    )
    system_requirements = fields.Text(string='System Requirements')
    interface_requirements = fields.Text(string='Interface Requirements')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('design_review', 'Design Review'),
        ('dfmea_analysis', 'DFMEA Analysis'),
        ('dfa_required', 'DFA Required'),
        ('dfa_completed', 'DFA Completed'),
        ('verification', 'Verification'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved'),
        ('implemented', 'Implemented')
    ], string='Status', default='draft', tracking=True, required=True)
    dfmea_line_ids = fields.One2many('dfmea.line.item', 'dfmea_item_id', string='Failure Mode Analysis')
    dfa_created = fields.Boolean(string="DFA Created", default=False, tracking=True)
    highest_rpn = fields.Integer(string='Highest RPN', compute='_compute_risk_metrics', store=True)
    high_risk_count = fields.Integer(string='High Risk Items', compute='_compute_risk_metrics', store=True)
    critical_risk_count = fields.Integer(string='Critical Risk Items', compute='_compute_risk_metrics', store=True)
    design_controls_implemented = fields.Boolean(string='Design Controls Implemented', default=False)
    document_control_number = fields.Char(string='Document Control Number')

    @api.depends('dfmea_line_ids.rpn')
    def _compute_risk_metrics(self):
        for record in self:
            if record.dfmea_line_ids:
                rpn_values = record.dfmea_line_ids.mapped('rpn')
                record.highest_rpn = max(rpn_values) if rpn_values else 0
                record.high_risk_count = len([rpn for rpn in rpn_values if 100 <= rpn < 200])
                record.critical_risk_count = len([rpn for rpn in rpn_values if rpn >= 200])
            else:
                record.highest_rpn = 0
                record.high_risk_count = 0
                record.critical_risk_count = 0

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

    def action_start_design_review(self):
        required_fields = {
            'model_year': 'Model Year',
            'customer': 'Customer',
            'supplier': 'Supplier',
            'team_ids': 'Cross-functional Team',
            'team_leader_id': 'Team Leader',
            'responsible_id': 'Responsible Engineer',
            'design_responsible_id': 'Design Responsible',
            'date': 'DFMEA Date',
            'target_completion_date': 'Target Completion Date',
        }
        missing_fields = [label for field, label in required_fields.items() if not getattr(self, field)]
        if missing_fields:
            raise UserError(_('Please complete the following required fields: %s') % ', '.join(missing_fields))
        if not self.system_function:
            raise UserError(_('System/Component Function must be defined.'))
        self.state = 'design_review'
        self.message_post(body=_('Design review phase started.'))
        # Send Design Review Phase Started email
        recipients = self.team_ids | self.team_leader_id | self.responsible_id | self.design_responsible_id
        self._send_email('design.email_template_design_review', recipients)

    def action_define_system_functions(self):
        required_fields = {
            'system_function': 'System/Component Function',
            'design_intent': 'Design Intent',
            'system_requirements': 'System Requirements',
            'interface_requirements': 'Interface Requirements'
        }
        missing_fields = [label for field, label in required_fields.items() if not getattr(self, field)]
        if missing_fields:
            raise UserError(_('Please complete all system requirements: %s') % ', '.join(missing_fields))
        self.state = 'dfmea_analysis'
        self.message_post(body=_('System functions defined. Ready for DFMEA analysis.'))

    def action_perform_dfmea(self):
        if not self.dfmea_line_ids:
            raise UserError(_('Please add at least one failure mode analysis.'))
        for line in self.dfmea_line_ids:
            missing_fields = []
            for field in ['function', 'failure_mode', 'failure_effect', 'failure_cause', 'current_design_controls',
                          'current_detection_controls']:
                if not getattr(line, field):
                    missing_fields.append(line._fields[field].string)
            if missing_fields:
                raise UserError(
                    _('Incomplete analysis for failure mode. Please complete: %s') % ', '.join(missing_fields))
        high_rpn_lines = self.dfmea_line_ids.filtered(lambda line: line.rpn >= 100)
        critical_lines = self.dfmea_line_ids.filtered(lambda line: line.severity >= 9 or line.rpn >= 200)
        if high_rpn_lines or critical_lines:
            self.state = 'dfa_required'
            self.message_post(body=_('High RPN or critical failures detected. DFA analysis required.'))
            # Send DFA Analysis Required email
            recipients = self.team_ids | self.team_leader_id | self.responsible_id
            self._send_email('design.email_template_dfa_required', recipients, {
                'high_risk_count': self.high_risk_count,
                'critical_risk_count': self.critical_risk_count,
                'highest_rpn': self.highest_rpn
            })
        else:
            self.state = 'verification'
            self.message_post(body=_('DFMEA analysis completed. Proceeding to verification.'))

    def action_conduct_dfa(self):
        existing_dfa = self.env['dfa.record'].search([
            ('dfmea_item_id', '=', self.id),
            ('state', '!=', 'archived')
        ])
        if existing_dfa:
            raise UserError(
                _('A DFA record already exists for this DFMEA. Please review or archive the existing DFA before creating a new one.'))
        high_rpn_lines = self.dfmea_line_ids.filtered(lambda line: line.rpn >= 100)
        critical_lines = self.dfmea_line_ids.filtered(lambda line: line.severity >= 9 or line.rpn >= 200)
        if not high_rpn_lines and not critical_lines:
            raise UserError(_('No high RPN or critical items found. DFA is not required.'))
        dfa_model = self.env['dfa.record']
        dfa = dfa_model.create({
            'dfmea_item_id': self.id,
            'name': f"DFA-{self.name}",
            'part_id': self.part_id.id,
            'revision': self.rev_no,
            'team_ids': [(6, 0, self.team_ids.ids)],
            'team_leader_id': self.team_leader_id.id,
            'responsible_id': self.responsible_id.id,
            'approved_by_id': self.approved_by_id.id,
            'analysis_scope': 'dependent_failures',
            'analysis_trigger': 'high_rpn_critical_failures'
        })
        lines_to_analyze = (high_rpn_lines | critical_lines).sudo()
        for line in lines_to_analyze:
            self.env['dfa.item'].create({
                'dfa_record_id': dfa.id,
                'dependent_item': line.failure_mode,
                'failure_effect': line.failure_effect,
                'severity': line.severity,
                'occurrence': line.occurrence,
                'detection': line.detection,
                'mitigation_strategy': 'To be defined:',
                'owner_id': line.action_owner_id.id if line.action_owner_id else self.responsible_id.id,
                'due_date': line.action_due_date or fields.Date.today() + timedelta(days=30)
            })
        self.dfa_created = True
        self.message_post(body=_('DFA analysis initiated for high-risk items.'))
        # Send DFA Analysis Created email (triggered from DFA model)
        return {
            'type': 'ir.actions.act_window',
            'name': _('DFA Record'),
            'res_model': 'dfa.record',
            'view_mode': 'form',
            'res_id': dfa.id,
            'target': 'current'
        }

    def action_design_verification(self):
        if self.state == 'dfa_required' and not self.dfa_created:
            raise UserError(_('DFA must be created before proceeding to verification.'))
        if self.state == 'dfa_required':
            dfa_record = self.env['dfa.record'].search([('dfmea_item_id', '=', self.id), ('state', '!=', 'approved')])
            if dfa_record:
                raise UserError(_('Linked DFA analysis must be approved before proceeding to verification.'))
        pending_actions = self.dfmea_line_ids.filtered(lambda l: l.rpn >= 100 and l.action_status != 'completed')
        if pending_actions:
            raise UserError(_('All high-priority corrective actions must be completed.'))
        if not self.design_controls_implemented:
            raise UserError(_('Design controls must be implemented before verification.'))
        if not self.reviewed_by_id:
            raise UserError(_('Design review must be completed and documented.'))
        self.state = 'verification'
        self.message_post(body=_('Design verification phase initiated.'))

    def action_approve(self):
        if not self.design_controls_implemented:
            raise UserError(_('Design controls must be implemented before approval.'))
        if not self.reviewed_by_id or not self.approved_by_id:
            raise UserError(_('Cross-functional team review and approval required.'))
        if self.customer_approval_required and not self.customer_approved_by:
            raise UserError(_('Customer approval is required but not obtained.'))

        # Clear rejection fields when approving
        self.rejected_by_id = False
        self.rejection_date = False
        self.rejection_reason = False

        self.state = 'approved'
        self.date_completed = fields.Date.today()
        self.message_post(body=_('DFMEA approved by %s.') % self.approved_by_id.name)

        # Send Approval Request and DFMEA Approved emails
        recipients = self.team_ids | self.team_leader_id | self.responsible_id | self.approved_by_id
        self._send_email('design.email_template_approval_request', [self.approved_by_id])
        self._send_email('design.email_template_dfmea_approved', recipients, {
            'approval_date': self.date_completed,
            'approved_by': self.approved_by_id
        })

    def action_reject(self):
        """Reject the DFMEA and require rejection reason"""
        if not self.rejection_reason:
            raise UserError(_('Please provide a rejection reason before rejecting the DFMEA.'))

        if not self.rejected_by_id:
            self.rejected_by_id = self.env.user

        self.rejection_date = fields.Date.today()
        self.state = 'rejected'

        # Clear approval fields when rejecting
        self.approved_by_id = False
        self.date_completed = False

        self.message_post(
            body=_('DFMEA rejected by %s. Reason: %s') % (self.rejected_by_id.name, self.rejection_reason)
        )

        # Send rejection notification to team
        recipients = self.team_ids | self.team_leader_id | self.responsible_id | self.design_responsible_id
        self._send_email('design.email_template_dfmea_rejected', recipients, {
            'rejection_date': self.rejection_date,
            'rejected_by': self.rejected_by_id.name,
            'rejection_reason': self.rejection_reason
        })

        # Create activity for responsible engineer to address rejection
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get_id('dfmea.item'),
            'res_id': self.id,
            'user_id': self.responsible_id.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': _('DFMEA Rejected - Action Required'),
            'note': _(
                'DFMEA has been rejected. Please address the following issues and resubmit:\n%s') % self.rejection_reason,
            'date_deadline': fields.Date.today() + timedelta(days=7),
        })

    def action_resubmit_after_rejection(self):
        """Resubmit DFMEA after addressing rejection issues"""
        if self.state != 'rejected':
            raise UserError(_('This action is only available for rejected DFMEAs.'))

        # Validation before resubmission
        if not self.design_controls_implemented:
            raise UserError(_('Design controls must be implemented before resubmission.'))
        if not self.reviewed_by_id:
            raise UserError(_('Design review must be completed and documented.'))

        # Move back to verification state for re-approval
        self.state = 'verification'
        self.message_post(
            body=_('DFMEA resubmitted for approval after addressing rejection issues.')
        )

        # Notify approver about resubmission
        if self.approved_by_id:
            self._send_email('design.email_template_dfmea_resubmitted', [self.approved_by_id], {
                'resubmission_date': fields.Date.today(),
                'previous_rejection_reason': self.rejection_reason
            })

    def action_qms_integration(self):
        if self.state != 'approved':
            raise UserError(_('DFMEA must be approved before QMS integration.'))
        if not self.document_control_number:
            self.document_control_number = f"DFMEA-{self.name}-{self.rev_no}"
        self.state = 'implemented'
        self.message_post(body=_('DFMEA integrated into QMS. Implementation complete.'))
        # Send DFMEA Approved email again if needed for implementation notification
        recipients = self.team_ids | self.team_leader_id | self.responsible_id
        self._send_email('design.email_template_dfmea_approved', recipients, {
            'implementation_date': self.date_completed
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('dfmea.item') or _('New')
            if not vals.get('original_dfmea_date'):
                vals['original_dfmea_date'] = fields.Date.today()
        records = super().create(vals_list)
        # Send DFMEA Created email
        for record in records:
            recipients = record.team_ids | record.team_leader_id | record.responsible_id
            record._send_email('design.email_template_dfmea_created', recipients)
        return records

    @api.constrains('team_ids')
    def _check_team_composition(self):
        for record in self:
            if len(record.team_ids) < 3:
                raise ValidationError(_('Cross-functional team must have at least 3 members per IATF 16949.'))


class DFMEALineItem(models.Model):
    _name = 'dfmea.line.item'
    _description = 'DFMEA Line Item - Failure Mode Analysis'
    _order = 'rpn desc, severity desc'

    dfmea_item_id = fields.Many2one('dfmea.item', string='DFMEA Reference', required=True, ondelete='cascade')
    function = fields.Text(string='Function', required=True)
    failure_mode = fields.Text(string='Potential Failure Mode', required=True)
    failure_effect = fields.Text(string='Potential Effect(s) of Failure', required=True)
    failure_cause = fields.Text(string='Potential Cause(s) of Failure', required=True)
    severity = fields.Integer(string='Severity (S)', required=True, help="1-10 scale")
    occurrence = fields.Integer(string='Occurrence (O)', required=True, help="1-10 scale")
    detection = fields.Integer(string='Detection (D)', required=True, help="1-10 scale")
    rpn = fields.Integer(string='RPN', compute='_compute_rpn', store=True, help="Risk Priority Number (S × O × D)")
    current_design_controls = fields.Text(string='Preventive Controls')
    current_detection_controls = fields.Text(string='Detection Controls')
    recommended_action = fields.Text(string='Recommended Action(s)')
    action_priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Action Priority', compute='_compute_action_priority', store=True)
    action_owner_id = fields.Many2one('res.users', string='Responsibility (Action Owner)')
    action_due_date = fields.Date(string='Action Due Date')
    action_taken = fields.Text(string='Actions Taken')
    action_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Action Status', default='pending')
    action_completion_date = fields.Date(string='Action Completion Date', compute='_compute_action_completion_date',
                                         store=True)
    severity_post = fields.Integer(string='Severity (Post-Action)')
    occurrence_post = fields.Integer(string='Occurrence (Post-Action)')
    detection_post = fields.Integer(string='Detection (Post-Action)')
    rpn_post = fields.Integer(string='RPN (Post-Action)', compute='_compute_rpn_post', store=True)

    @api.depends('action_status')
    def _compute_action_completion_date(self):
        for rec in self:
            if rec.action_status == 'completed' and not rec.action_completion_date:
                rec.action_completion_date = fields.Date.today()
            elif rec.action_status != 'completed':
                rec.action_completion_date = False

    @api.depends('severity', 'occurrence', 'detection')
    def _compute_rpn(self):
        for rec in self:
            rec.rpn = (rec.severity or 0) * (rec.occurrence or 0) * (rec.detection or 0)

    @api.depends('severity_post', 'occurrence_post', 'detection_post')
    def _compute_rpn_post(self):
        for rec in self:
            rec.rpn_post = (rec.severity_post or 0) * (rec.occurrence_post or 0) * (rec.detection_post or 0)

    @api.depends('rpn', 'severity')
    def _compute_action_priority(self):
        for rec in self:
            if rec.severity >= 9 or rec.rpn >= 200:
                rec.action_priority = 'critical'
            elif rec.rpn >= 100:
                rec.action_priority = 'high'
            elif rec.rpn >= 50:
                rec.action_priority = 'medium'
            else:
                rec.action_priority = 'low'

    @api.constrains('severity', 'occurrence', 'detection', 'severity_post', 'occurrence_post', 'detection_post')
    def _check_rating_values(self):
        for record in self:
            fields_to_check = [
                ('severity', record.severity),
                ('occurrence', record.occurrence),
                ('detection', record.detection),
                ('severity_post', record.severity_post),
                ('occurrence_post', record.occurrence_post),
                ('detection_post', record.detection_post)
            ]
            for field_name, value in fields_to_check:
                if value and (value < 1 or value > 10):
                    field_label = record._fields[field_name].string
                    raise ValidationError(_('%s must be between 1 and 10.') % field_label)

    def escalate_overdue_actions(self):
        today = fields.Date.today()
        overdue_lines = self.search([
            ('action_due_date', '<', today),
            ('action_status', '!=', 'completed')
        ])
        for line in overdue_lines:
            manager = line.dfmea_item_id.team_leader_id or line.dfmea_item_id.responsible_id
            if manager:
                line.dfmea_item_id.message_post(
                    body=_('Escalation: Action for "%s" is overdue!') % (line.function or line.failure_mode),
                    partner_ids=[manager.partner_id.id]
                )
                # Send Overdue Actions Reminder email
                line._send_email('design.email_template_overdue_actions', [manager], {
                    'overdue_count': 1,
                    'overdue_items': [{
                        'failure_mode': line.failure_mode,
                        'action_due_date': line.action_due_date,
                        'action_priority': line.action_priority
                    }]
                })

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

    def schedule_action_reminder(self):
        for line in self:
            if line.action_owner_id and line.action_due_date and line.action_status != 'completed':
                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get_id('dfmea.line.item'),
                    'res_id': line.id,
                    'user_id': line.action_owner_id.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('DFMEA Action Due'),
                    'note': _('Action is due for: %s' % (line.function or line.failure_mode)),
                    'date_deadline': line.action_due_date,
                })

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record.schedule_action_reminder()
        return record

    def write(self, vals):
        res = super().write(vals)
        self.schedule_action_reminder()
        return res

    @api.model
    def _cron_weekly_dfmea_report(self):
        """Cron job to send weekly DFMEA status report."""
        today = fields.Date.today()
        report_date = today.strftime('%Y-%m-%d')
        dfmeas = self.env['dfmea.item'].search([])
        new_dfmeas = dfmeas.filtered(lambda d: d.create_date.date() >= today - timedelta(days=7))
        completed_dfmeas = dfmeas.filtered(lambda d: d.state == 'implemented')
        overdue_actions = self.search([
            ('action_due_date', '<', today),
            ('action_status', '!=', 'completed')
        ])
        pending_approvals = dfmeas.filtered(lambda d: d.state == 'verification')
        high_rpn_lines = self.search([('rpn', '>=', 100)])
        upcoming_deadlines = self.search([
            ('action_due_date', '>=', today),
            ('action_due_date', '<=', today + timedelta(days=7)),
            ('action_status', '!=', 'completed')
        ])
        missing_assignments = self.search([('action_owner_id', '=', False)])
        recipients = self.env['res.users'].search([('groups_id.name', 'in', ['DFMEA Manager'])])
        ctx = {
            'report_date': report_date,
            'new_dfmeas': len(new_dfmeas),
            'completed_dfmeas': len(completed_dfmeas),
            'overdue_actions': len(overdue_actions),
            'pending_approvals': len(pending_approvals),
            'high_risk_items': len(high_rpn_lines),
            'upcoming_deadlines': len(upcoming_deadlines),
            'missing_assignments': len(missing_assignments)
        }
        for record in dfmeas:
            record._send_email('design.email_template_weekly_dfmea_report', recipients, ctx)