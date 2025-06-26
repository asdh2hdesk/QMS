from odoo  import models, fields, api, _
from odoo.exceptions import ValidationError

class CustomerComplaint(models.Model):
    _inherit = 'customer.complaint'

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    non_conformance_id = fields.Many2one('non.conformance', string="Related NCR", ondelete='set null')


class NonConformance(models.Model):
    _name = 'non.conformance'
    _description = 'Non Conformance'
    _inherit = ['iatf.sign.off.members']

    name = fields.Char('NCR Number',
                       default=lambda self: self.env['ir.sequence'].next_by_code('non.conformance'),
                       readonly=True)
    part_id = fields.Many2one('product.product', string='Part Number')
    part_number = fields.Char(related='part_id.default_code', string='Part Number', readonly=True)
    detection_date = fields.Date(string='Detection Date')
    department = fields.Many2one('hr.department', string='Department')
    machine_id= fields.Many2one('maintenance.equipment', string='Machine')
    operator = fields.Many2one('res.users', string='Operator / Responsible Person')
    shift =fields.Selection([('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'), ('e', 'E')], string='Shift')
    non_conformance_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
        ('customer', 'Customer'),
        ('supplier', 'Supplier')
    ], string='Non Conformance Type')
    active = fields.Boolean(default=True)

    non_conformance_category = fields.Selection([
        ('quality', 'Quality'),
        ('delivery', 'Delivery'),
        ('service', 'Service'),
        ('other', 'Other')
    ], string='Non Conformance Category')
    non_conformance_sub_category = fields.Selection([
        ('quality', 'Quality'),
        ('delivery', 'Delivery'),
        ('service', 'Service'),
        ('other', 'Other')
    ], string='Non Conformance Sub Category')
    quantity_affected = fields.Integer(string='Quantity Affected')
    cost = fields.Float(string='Estimated Cost of Non-Conformance')
    cause_type = fields.Selection([
        ('human_error', 'Human Error'),
        ('machine_failure', 'Machine Failure'),
        ('material_defect', 'Material Defect'),
        ('process_issue', 'Process Issue')
    ], string='Cause Type')
    customer_impact = fields.Boolean('Customer Impact?')
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity Level')
    disposition = fields.Selection([
        ('rework', 'Rework'),
        ('repair', 'Repair'),
        ('use_as_is', 'Use As-Is'),
        ('scrap', 'Scrap')
    ], string="Disposition Decision")
    # Add relation to customer complaint for CAPA
    capa_complaint_id = fields.Many2one('customer.complaint', string="CAPA Complaint", readonly=True, ondelete='set null')
    capa_closing_date = fields.Date(string='CAPA Closing Date', readonly=True,
                                    help="Date when the associated CAPA was completed")
    deviation_document = fields.Binary("Deviation Report (PDF)")
    deviation_document_filename = fields.Char("Deviation Document Filename")
    deviation_justification = fields.Text("Deviation Justification")
    deviation_approver = fields.Many2one('res.users', string="Deviation Approved By")
    deviation_approved_date = fields.Date("Approval Date")

    rework_ids = fields.One2many('ncr.rework', 'non_conformance_id', string="Rework Details")
    repair_ids = fields.One2many('ncr.repair', 'non_conformance_id', string="Repair Details")
    useas_is_ids = fields.One2many('ncr.useas_is', 'non_conformance_id', string="Use-As-Is Details")
    scrap_ids = fields.One2many('ncr.scrap', 'non_conformance_id', string="Scrap Details")

    attachment = fields.Binary('Upload Image/Doc')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('evaluated', 'Evaluated'),
        ('capa', 'CAPA Applied'),

        ('closed', 'Closed')
    ], string='Status', default='draft')

    # Add state transition methods
    def action_evaluate(self):
        for record in self:
            record.state = 'evaluated'

    def action_capa(self):
        """Open the CAPA complaint wizard"""
        self.ensure_one()
        return {
            'name': _('Create Customer Complaint for CAPA'),
            'type': 'ir.actions.act_window',
            'res_model': 'customer.complaint.capa.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_non_conformance_id': self.id,
                'default_part_id': self.part_id.id if self.part_id else False,
            }
        }

    @api.depends('capa_complaint_id')
    def _compute_capa_closing_date(self):
        """Update the CAPA closing date when the CAPA complaint changes"""
        for record in self:
            capa_closing_date = False
            if record.capa_complaint_id:
                # Get the corresponding customer.complaint.handling record
                handling_record = self.env['customer.complaint.handling'].search([
                    ('complaint_id', '=', record.capa_complaint_id.id)
                ], limit=1)

                if handling_record:
                    capa_closing_date = handling_record.closing_date

            record.capa_closing_date = capa_closing_date

    def action_close(self):
        """Close the Non Conformance Record after validating CAPA state"""
        for record in self:
            # Update CAPA closing date before validation
            record._compute_capa_closing_date()

            # Check if there is an associated CAPA complaint that's not closed
            if record.capa_complaint_id and not record.capa_closing_date:
                raise ValidationError(_("Cannot close this NCR. The associated CAPA must be completed first."))

            # If we get here, either there's no CAPA or the CAPA is properly closed
            record.state = 'closed'

    @api.constrains('quantity_affected', 'cost')
    def _check_positive_values(self):
        for record in self:
            if record.quantity_affected <= 0:
                raise ValidationError(_("Quantity affected must be greater than zero."))
            if record.cost < 0:
                raise ValidationError(_("Cost cannot be negative."))

    # If using scrap functionality, you may want to link with stock.scrap
    def create_scrap_order(self):
        """Create a stock scrap order linked to this NCR"""
        self.ensure_one()
        if not self.scrap_ids:
            raise ValidationError(_("No scrap details provided."))

        for scrap_line in self.scrap_ids:
            vals = {
                'product_id': self.part_id.id,
                'scrap_qty': scrap_line.scrap_quantity,
                'product_uom_id': self.part_id.uom_id.id,
                'origin': f"NCR {self.name}",
                'date_done': scrap_line.scrap_date,
            }
            scrap_id = self.env['stock.scrap'].create(vals)
            # You might want to add a reference back to the NCR
    
  

class NCRReworkReport(models.Model):
    _name = 'ncr.rework'
    _description = 'NCR Rework Details'
    _inherit = "translation.mixin"

    non_conformance_id = fields.Many2one('non.conformance', string="NCR", ondelete='cascade')

    rework_action = fields.Text("Rework Action",translate=True)
    responsible_person = fields.Many2one('res.users', string="Responsible Person")
    ok_quantity_after = fields.Integer('Ok Quantity After Rework')
    not_ok_quantity = fields.Integer('Not OK Quantity After Rework')
    rework_deadline = fields.Date("Rework Deadline")
    rework_completed = fields.Boolean("Completed")


class NCRRepairReport(models.Model):
    _name = 'ncr.repair'
    _description = 'NCR Repair Details'
    _inherit = "translation.mixin"

    non_conformance_id = fields.Many2one('non.conformance', string="NCR", ondelete='cascade')
    repair_details = fields.Text("Repair Details",translate=True)
    technician = fields.Many2one('res.users', string="Technician")
    ok_quantity_after = fields.Integer('Ok Quantity After Rework')
    not_ok_quantity = fields.Integer('Not OK Quantity After Rework')
    repair_date = fields.Date("Repair Date")


class NCRUseAsIsReport(models.Model):
    _name = 'ncr.useas_is'
    _description = 'NCR Use-As-Is Details'
    _inherit = "translation.mixin"

    non_conformance_id = fields.Many2one('non.conformance', string="NCR", ondelete='cascade')
    justification = fields.Text("Justification",translate=True)
    approver = fields.Many2one('res.users', string="Approved By")
    approval_date = fields.Date("Approval Date")


class NCRScrapReport(models.Model):
    _name = 'ncr.scrap'
    _description = 'NCR Scrap Details'
    _inherit = "translation.mixin"

    non_conformance_id = fields.Many2one('non.conformance', string="NCR", ondelete='cascade')
    reason = fields.Text("Scrap Reason",translate=True)
    scrap_quantity = fields.Integer("Scrapped Quantity")
    scrap_confirmed_by = fields.Many2one('res.users', string="Confirmed By")
    scrap_date = fields.Date("Scrap Date")




class CustomerComplaintCapaWizard(models.TransientModel):
    _name = 'customer.complaint.capa.wizard'
    _description = 'Customer Complaint CAPA Wizard'
    _inherit = "translation.mixin"

    non_conformance_id = fields.Many2one('non.conformance', string='Non Conformance', readonly=True)
    part_id = fields.Many2one('product.product', string='Part', required=True)
    customer_name = fields.Char(string='Customer Name', required=True,translate=True)
    customer_email = fields.Char(string='Email', required=True)
    customer_phone = fields.Char(string='Phone')
    category_id = fields.Many2one('customer.complaint.category', string='Complaint Category', required=True)
    assigned_to = fields.Many2one('res.users', string='Assigned To', required=True)
    complaint_description = fields.Text(string='Complaint Description', required=True,translate=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')



    def action_submit_complaint(self):
        self.ensure_one()

        if not self.customer_email:
            raise ValidationError(_("Email is required to create a complaint"))

        partner = self.env['res.partner'].search([('email', '=', self.customer_email)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.customer_name,
                'email': self.customer_email,
                'phone': self.customer_phone,
                'type': 'contact',
            })
        else:
            partner.write({
                'name': self.customer_name,
                'phone': self.customer_phone,
            })

        draft_state = self.env['customer.complaint.category.state'].search([('name', '=', 'draft')], limit=1)
        if not draft_state:
            raise ValidationError(_("Cannot find 'draft' state for customer complaint"))

        complaint = self.env['customer.complaint'].create({
            'part_id': self.part_id.id if self.part_id else False,
            'customer_id': partner.id,
            'category_id': self.category_id.id,
            'assigned_to': self.assigned_to.id,
            'description': self.complaint_description,
            'complaint_date': fields.Date.today(),
            'state_id': draft_state.id,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)] if self.attachment_ids else False,
            'non_conformance_id': self.non_conformance_id.id if self.non_conformance_id else False,
        })

        self.non_conformance_id.write({
            'capa_complaint_id': complaint.id,
            'state': 'capa'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'customer.complaint',
            'res_id': complaint.id,
            'view_mode': 'form',
            'target': 'current',
        }