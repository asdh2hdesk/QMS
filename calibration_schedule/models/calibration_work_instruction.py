from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)

# class CalibrationSchedule(models.Model):
#     _inherit = 'calibration.schedule'


class CalibrationWorkInstruction(models.Model):
    _name = 'calibration.work.instruction'
    _description = 'Calibration Work Instruction'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Work Instruction Name', required=True, tracking=True)
    document_no = fields.Char(string='Doc. No.', required=True, tracking=True)
    revision_no = fields.Char(string='Rev. No.', required=True, default='0', tracking=True)
    effective_date = fields.Date(string='Effective Date', default=fields.Date.today, tracking=True)
    page_info = fields.Char(string='Page', default='01 of 01', tracking=True)

    # Department and subject
    department = fields.Char(string='Department', default='QA/CALIBRATION', tracking=True)
    subject = fields.Char(string='Subject', required=True, tracking=True)

    # Scope and Parameters
    scope = fields.Text(string='Scope', tracking=True)
    range_lc = fields.Char(string='Range/Least Count', tracking=True)
    reference_standard = fields.Char(string='Reference Standard', tracking=True)
    master_equipment = fields.Char(string='Master Equipment Used', tracking=True)

    # Check points and procedure steps
    check_point_ids = fields.One2many(
        'calibration.work.instruction.step',
        'instruction_id',
        string='Check Points',
        domain=[('step_type', '=', 'check_point')],
    )

    procedure_ids = fields.One2many(
        'calibration.work.instruction.step',
        'instruction_id',
        string='Procedure Steps',
        domain=[('step_type', '=', 'procedure')],
    )

    # Approvals
    prepared_by = fields.Many2one('res.users', string='Prepared By', default=lambda self: self.env.user.id)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By')
    approved_by = fields.Many2one('res.users', string='Approved By')

    # Relation to equipment categories
    equipment_category_ids = fields.Many2many('maintenance.equipment.category',
                                              string='Applicable Equipment Categories')

    # Relation to specific equipment
    equipment_ids = fields.Many2many('maintenance.equipment', string='Applicable Equipment')

    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        if 'step_type' not in vals:
            raise UserError(_("Step Type is missing."))

        domain = [('instruction_id', '=', vals.get('instruction_id')), ('step_type', '=', vals['step_type'])]

        last_seq = self.search(domain, order='sequence desc', limit=1)
        vals['sequence'] = last_seq.sequence + 10 if last_seq else 10

        return super(CalibrationWorkInstructionStep, self).create(vals)

    def download_work_instruction(self):
        self.ensure_one()
        return self._generate_work_instruction_report()

    def _generate_work_instruction_report(self):
        company = self.env.company  # Fetch current company

        # Corrected template variables
        template_vars = {
            'work_instruction': self,
            'check_points': self.check_point_ids.filtered(lambda r: r.step_type == 'check_point'),
            'procedures': self.procedure_ids.filtered(lambda r: r.step_type == 'procedure'),
        }

        html_report = self.env['ir.qweb']._render(
            'calibration_schedule.work_instruction_report_template',
            {'company': company, 'work_instruction': self, **template_vars}  # Pass variables
        )

        try:
            pdf_content = self.env['ir.actions.report']._run_wkhtmltopdf(
                [html_report],
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-margin-bottom': 10,
                    'data-report-margin-left': 10,
                    'data-report-margin-right': 10,
                }
            )

            filename = f"Work_Instruction_{self.name}.pdf"
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

        except Exception as e:
            _logger.warning("wkhtmltopdf failed, falling back to direct HTML: %s", e)

            filename = f"Work_Instruction_{self.name}.html"
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(html_report.encode('utf-8')),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'text/html',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }


class CalibrationWorkInstructionStep(models.Model):
    _name = 'calibration.work.instruction.step'
    _description = 'Work Instruction Step'
    _order = 'sequence, id'

    instruction_id = fields.Many2one('calibration.work.instruction', string='Work Instruction',
                                     required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=1)
    step_type = fields.Selection([
        ('check_point', 'Check Point'),
        ('procedure', 'Procedure')
    ], string='Step Type', required=True)
    description = fields.Text(string='Description', required=True)

    @api.model
    def create(self, vals):
        # Auto-sequence steps
        if vals.get('step_type') == 'check_point':
            domain = [('instruction_id', '=', vals.get('instruction_id')),
                      ('step_type', '=', 'check_point')]
        else:
            domain = [('instruction_id', '=', vals.get('instruction_id')),
                      ('step_type', '=', 'procedure')]

        last_seq = self.search(domain, order='sequence desc', limit=1)
        if last_seq:
            vals['sequence'] = last_seq.sequence + 1
        else:
            vals['sequence'] = 1

        return super(CalibrationWorkInstructionStep, self).create(vals)


# Add a link from calibration schedule to work instructions
class CalibrationSchedule(models.Model):
    _inherit = 'calibration.schedule'

    work_instruction_id = fields.Many2one('calibration.work.instruction', string='Work Instruction')

    def get_work_instruction(self):
        """Get relevant work instruction for the equipment"""
        self.ensure_one()
        if not self.equipment_id:
            raise UserError(_('Please select an instrument first.'))

        # Find work instruction for this specific equipment
        instruction = self.env['calibration.work.instruction'].search([
            ('equipment_ids', 'in', self.equipment_id.id)
        ], limit=1)

        # If not found, check for category
        if not instruction and self.equipment_id.category_id:
            instruction = self.env['calibration.work.instruction'].search([
                ('equipment_category_ids', 'in', self.equipment_id.category_id.id)
            ], limit=1)

        if instruction:
            self.work_instruction_id = instruction.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Work Instruction',
                'res_model': 'calibration.work.instruction',
                'res_id': instruction.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'No Work Instruction Found',
                'res_model': 'calibration.work.instruction',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_equipment_ids': [(6, 0, [self.equipment_id.id])],
                    'default_subject': f'CALIBRATION OF {self.equipment_id.name}',
                }
            }