from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class QMSRejectionHandling(models.Model):
    _name = 'qms.rejection.handling'
    _description = 'QMS Rejection Handling'
    _inherit = ['mail.thread', 'mail.activity.mixin', "translation.mixin"]
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'),translate=True)

    # Source Document Information
    source_document = fields.Selection([
        ('grn', 'GRN'),
        ('calibration', 'Calibration'),
        ('msa', 'MSA'),
        ('complaint', 'Customer Complaint'),
        ('ncr', 'Non-Conformance Report'),
    ], string='Source Document', required=True, tracking=True)

    source_document_id = fields.Reference([
        ('grn.management', 'GRN'),
        ('calibration.sheet', 'Calibration'),
        ('msa.sheet', 'MSA'),
        ('customer.complaint.handling', 'Customer Complaint'),
        ('non.conformance', 'Non-Conformance Report'),
    ], string='Source Document Reference', required=True)

    # Basic Information
    rejection_date = fields.Datetime(string='Rejection Date', required=True,
                                     default=fields.Datetime.now, tracking=True)
    rejected_by = fields.Many2one('res.users', string='Rejected By',
                                  default=lambda self: self.env.user, tracking=True)

    # Rejection Details
    rejection_reason = fields.Text(string='Rejection Reason', required=True, tracking=True,translate=True)
    defect_source = fields.Char(string='Defect Source', tracking=True,translate=True)
    defective_qty = fields.Float(string='Defective Quantity', tracking=True)
    suspected_qty = fields.Float(string='Suspected Quantity', tracking=True)
    defect_description = fields.Text(string='Defect Description', tracking=True,translate=True)
    defect_snapshot = fields.Binary(string='Defect Snapshot')

    # Impact Assessment
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity Level', required=True, tracking=True)

    customer_impact = fields.Boolean(string='Customer Impact', tracking=True)
    financial_impact = fields.Monetary(string='Financial Impact', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Disposition
    disposition = fields.Selection([
        ('quarantine', 'Move to Quarantine'),
        ('scrap', 'Move to Scrap'),
        ('rework', 'Rework'),
        ('repair', 'Repair'),
        ('return_to_supplier', 'Return to Supplier'),
        ('use_as_is', 'Use As-Is'),
        ('concession', 'Concession'),
        ('other', 'Other')
    ], string='Disposition Decision', tracking=True)

    quarantine_location = fields.Char(string='Quarantine Location', tracking=True,translate=True)
    scrap_reason = fields.Text(string='Scrap Reason', tracking=True,translate=True)
    rework_instructions = fields.Text(string='Rework Instructions', tracking=True,translate=True)
    return_supplier_details = fields.Text(string='Return to Supplier Details', tracking=True,translate=True)

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('action_required', 'Action Required'),
        ('in_progress', 'In Progress'),
        ('quarantined', 'Quarantined'),
        ('scrapped', 'Scrapped'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True)

    # Assignment
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    department_id = fields.Many2one('hr.department', string='Responsible Department', tracking=True)

    # Action Plan
    action_plan = fields.Text(string='Action Plan', tracking=True,translate=True)

    # Resolution
    resolution_date = fields.Date(string='Resolution Date', tracking=True)
    verification_date = fields.Date(string='Verification Date', tracking=True)
    verified_by = fields.Many2one('res.users', string='Verified By', tracking=True)

    # Additional Information
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    notes = fields.Text(string='Notes',translate=True)

    # Computed fields
    days_to_resolution = fields.Integer(string='Days to Resolution', compute='_compute_days_to_resolution')
    is_overdue = fields.Boolean(string='Is Overdue', compute='_compute_is_overdue', search='_search_is_overdue',
                                store=True)

    @api.constrains('state')
    def _check_editable_state(self):
        for record in self:
            if record.state in ['resolved', 'closed'] and self._origin.state not in ['resolved', 'closed']:
                raise ValidationError(_("You cannot modify a record once it's resolved or closed."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('qms.rejection.handling') or _('New')
        return super().create(vals_list)

    @api.depends('rejection_date', 'resolution_date')
    def _compute_days_to_resolution(self):
        for record in self:
            if record.rejection_date and record.resolution_date:
                delta = record.resolution_date - record.rejection_date.date()
                record.days_to_resolution = delta.days
            else:
                record.days_to_resolution = 0

    @api.depends('state', 'rejection_date')
    def _compute_is_overdue(self):
        for record in self:
            if record.state not in ['resolved', 'closed', 'scrapped']:
                delta = fields.Date.today() - record.rejection_date.date()
                record.is_overdue = delta.days > 30
            else:
                record.is_overdue = False

    def _search_is_overdue(self, operator, value):
        today = fields.Date.today()
        thirty_days_ago = today - timedelta(days=30)
        domain = [
            ('state', 'not in', ['resolved', 'closed', 'scrapped']),
            ('rejection_date', '<=', thirty_days_ago)
        ]
        if operator == '=' and value:
            return domain
        elif operator == '=' and not value:
            return ['|', ('state', 'in', ['resolved', 'closed', 'scrapped']),
                   ('rejection_date', '>', thirty_days_ago)]
        return []

    def action_under_review(self):
        self.write({'state': 'under_review'})

    def action_require_action(self):
        self.write({'state': 'action_required'})

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_move_to_quarantine(self):
        if not self.quarantine_location:
            raise UserError(_("Please specify the quarantine location before moving to quarantine."))
        self.write({
            'state': 'quarantined',
            'disposition': 'quarantine'
        })

    def action_move_to_scrap(self):
        if not self.scrap_reason:
            raise UserError(_("Please specify the scrap reason before moving to scrap."))
        self.write({
            'state': 'scrapped',
            'disposition': 'scrap'
        })

    def action_resolve(self):
        self.write({
            'state': 'resolved',
            'resolution_date': fields.Date.today()
        })

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.onchange('source_document', 'source_document_id')
    def _onchange_source_document(self):
        if self.source_document and self.source_document_id:
            if self.source_document == 'grn':
                grn = self.env['grn.management'].browse(self.source_document_id.id)
                self.rejection_reason = grn.rejection_notes
                self.rejected_by = grn.create_uid
                self.defect_source = grn.rejection_wizard_defect_source
                self.defective_qty = grn.rejection_wizard_defective_qty
                self.suspected_qty = grn.rejection_wizard_suspected_qty
                self.defect_description = grn.rejection_wizard_defect_description
                self.defect_snapshot = grn.rejection_wizard_defect_snapshot

            elif self.source_document == 'complaint':
                complaint = self.env['customer.complaint.handling'].browse(self.source_document_id.id)
                self.rejection_reason = complaint.description or complaint.name
                self.rejected_by = complaint.create_uid
                self.severity = complaint.severity if hasattr(complaint, 'severity') else False
                self.customer_impact = True

            elif self.source_document == 'ncr':
                ncr = self.env['non.conformance'].browse(self.source_document_id.id)
                self.rejection_reason = ncr.name
                self.rejected_by = ncr.create_uid
                self.severity = ncr.severity
                self.customer_impact = ncr.customer_impact
                # Map NCR disposition to our disposition values
                disposition_mapping = {
                    'repair': 'repair',
                    'rework': 'rework',
                    'scrap': 'scrap',
                    'use_as_is': 'use_as_is',
                    'return_to_supplier': 'return_to_supplier',
                    'quarantine': 'quarantine',
                    'concession': 'concession',
                    'other': 'other'
                }
                self.disposition = disposition_mapping.get(ncr.disposition, 'other')

            elif self.source_document == 'calibration':
                calibration = self.env['calibration.sheet'].browse(self.source_document_id.id)
                self.rejection_reason = f"Calibration failure for {calibration.name}"
                self.rejected_by = calibration.create_uid
                self.severity = 'high'  # Calibration failures are typically high severity
                self.defect_source = 'Calibration'
                self.defect_description = f"Calibration failure detected in {calibration.name}"

            elif self.source_document == 'msa':
                msa = self.env['msa.sheet'].browse(self.source_document_id.id)
                self.rejection_reason = f"MSA failure for {msa.name}"
                self.rejected_by = msa.create_uid
                self.severity = 'high'  # MSA failures are typically high severity
                self.defect_source = 'MSA'
                self.defect_description = f"MSA failure detected in {msa.name}"