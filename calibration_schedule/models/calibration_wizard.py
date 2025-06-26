from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from odoo.tools import format_date
import logging

_logger = logging.getLogger(__name__)


class CalibrationReportWizard(models.Model):
    _name = 'calibration.report.wizard'
    _description = 'Calibration Report Wizard'

    line_id = fields.Many2one('calibration.schedule.line', string="Calibration Line", ondelete='cascade', required=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Instrument')

    # Standard length wizard lines for measurements
    standard_length_ids = fields.One2many('calibration.standard.length', 'wizard_id', string='Standard Lengths')

    # Get next scheduled calibration date
    next_calibration_date = fields.Date(string='Next Calibration Date', compute='_compute_next_calibration_date')
    conclusion = fields.Selection([
        ('satisfactory', 'Satisfactory'),
        ('not_satisfactory', 'Not Satisfactory')
    ], string='Conclusion', default='satisfactory', required=True)
    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status', default='draft')

    approved_by = fields.Many2one('res.users', string="Approved By")
    rejected_by = fields.Many2one('res.users', string="Rejected By", readonly=True)

    def action_submit(self):
        """Submit for approval"""
        self.ensure_one()
        self.write({'approval_state': 'to_approve'})

        # Return the same form with updated values
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calibration.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
            'flags': {'mode': 'readonly'},  # Prevents further edits while in approval
        }

    def action_approve(self):
        """Approve the calibration report"""
        self.ensure_one()
        self.write({
            'approval_state': 'approved',
            'approved_by': self.env.user.id,
        })

        context = dict(self.env.context)
        context.pop('default_approval_state', None)  # Remove any default state from context

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calibration.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
            'flags': {'mode': 'readonly'},
            'context': context,
        }

    def action_reject(self):
        """Reject the calibration report"""
        self.ensure_one()
        self.write({
            'approval_state': 'rejected',
            'rejected_by': self.env.user.id,
        })

        context = dict(self.env.context)
        context.pop('default_approval_state', None)  # Remove any default state from context

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calibration.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
            'flags': {'mode': 'readonly'},
            'context': context,
        }

    def action_save_report(self):
        """Save the report and update the schedule line's approval status"""
        self.ensure_one()

        # Update the approval status in calibration schedule line
        if self.line_id:
            self.line_id.approval_state = self.approval_state

        return {'type': 'ir.actions.act_window_close'}

    def action_open_calibration_report(self):
        def action_open_calibration_report(self):
            """Open existing calibration report or create a new one"""
            self.ensure_one()

            # Search for an existing calibration report linked to this line
            existing_report = self.env['calibration.report.wizard'].search([
                ('line_id', '=', self.id)
            ], limit=1)

            if existing_report:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'calibration.report.wizard',
                    'view_mode': 'form',
                    'res_id': existing_report.id,  # Open existing record
                    'target': 'new',
                    'context': self.env.context,
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'calibration.report.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_line_id': self.id},  # Correctly set the default line_id
                }


    @api.onchange('line_id', 'conclusion', 'approval_state')
    def _onchange_auto_save(self):
        """Automatically save changes when any field is modified."""
        if self:
            self.write({
                'line_id': self.line_id.id if self.line_id else False,
                'conclusion': self.conclusion,
                'approval_state': self.approval_state,
            })





    @api.model
    def default_get(self, fields_list):
        res = super(CalibrationReportWizard, self).default_get(fields_list)

        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')

        if active_model == 'calibration.schedule.line' and active_id:
            line = self.env['calibration.schedule.line'].browse(active_id)
            res['line_id'] = line.id

            # Create default standard lengths (example values)
            standard_lengths = []
            standard_length_vals = []

            for idx, length in enumerate(standard_lengths, 1):
                min_limit = length - 0.05
                max_limit = length + 0.05

                standard_length_vals.append((0, 0, {
                    'sequence': idx,
                    'standard_length': length,
                    'min_limit': min_limit,
                    'max_limit': max_limit,
                }))

            res['standard_length_ids'] = standard_length_vals

        return res

    @api.depends('line_id')
    def _compute_next_calibration_date(self):
        for wizard in self:
            if wizard.line_id:
                # Find the next scheduled calibration after this one
                next_calibration = self.env['calibration.schedule.line'].search([
                    ('equipment_id', '=', wizard.line_id.equipment_id.id),
                    ('schedule_date', '>', wizard.line_id.schedule_date)
                ], order='schedule_date asc', limit=1)

                if next_calibration:
                    wizard.next_calibration_date = next_calibration.schedule_date
                else:
                    # If no next calibration exists, calculate one
                    schedule = wizard.line_id.schedule_id
                    wizard.next_calibration_date = schedule._get_next_calibration_date(
                        wizard.line_id.cal_freq,
                        wizard.line_id.interval,
                        wizard.line_id.schedule_date
                    )
            else:
                wizard.next_calibration_date = False

    def generate_report(self):
        self.ensure_one()

        if not self.line_id:
            raise UserError(_('No calibration line selected.'))

        # Mark the line as done
        # self.line_id.write({'status': 'done'})

        # Generate measurement rows HTML
        measurement_rows_html = ""

        for length in self.standard_length_ids:
            measurement_rows_html += f"""
            <tr>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.sequence}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.standard_length}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.upper_reading or ''}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.center_reading or ''}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.lower_reading or ''}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.average or ''}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.min_limit}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: center;">{length.max_limit}</td>
            </tr>
            """

        # Prepare attachments HTML
        attachments_html = ""
        if self.line_id.attachment_ids:
            attachments_html = "<div style='margin-top: 20px;'><h3>Attachments</h3><ul>"
            for attachment in self.line_id.attachment_ids:
                attachments_html += f"<li>{attachment.name}</li>"
            attachments_html += "</ul></div>"

        # Get frequency text
        freq_text = dict(self.line_id._fields['cal_freq'].selection).get(self.line_id.cal_freq, '')
        if self.line_id.interval > 1:
            freq_text = f"Every {self.line_id.interval} {freq_text}s"
        else:
            freq_text = f"Every {freq_text}"

        # Format template variables
        template_vars = {
            'equipment_name': self.line_id.equipment_id.name or "INSTRUMENT",
            'equipment_code': self.line_id.code or "N/A",
            'calibration_date': format_date(self.env, self.line_id.schedule_date),
            'calibration_frequency': freq_text,
            'instrument_number': self.line_id.equipment_id.serial_no or "N/A",
            'make': self.line_id.make or "N/A",
            'calibration_instructions': "Place the standard length between measuring jaws of the caliper at three different positions and determine the length.",
            'measurement_rows': measurement_rows_html,
            'next_calibration_date': format_date(self.env, self.next_calibration_date),
            'done_by': self.env.user.name,
            'checked_by': self.line_id.equipment_id.technician_user_id.name if self.line_id.equipment_id.technician_user_id else "____________",
            'current_date': format_date(self.env, fields.Date.today()),
            'attachments_html': attachments_html,
            'conclusion': 'satisfactory' if self.conclusion == 'satisfactory' else 'not satisfactory'
        }

        # Render HTML report
        html_report = self.env['ir.qweb']._render('calibration_schedule.calibration_report_template', template_vars)

        try:
            # Try to use wkhtmltopdf first
            pdf_content = self.env['ir.actions.report']._run_wkhtmltopdf(
                [html_report],
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-margin-bottom': 10,
                    'data-report-margin-left': 10,
                    'data-report-margin-right': 10,
                }
            )
        except Exception as e:
            # Create a plain HTML file as fallback if PDF generation fails
            filename = f"Calibration_Report_{self.line_id.equipment_id.name}.html"

            # Create an attachment for the HTML content
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(html_report.encode('utf-8')),
                'res_model': 'calibration.schedule.line',
                'res_id': self.line_id.id,
                'mimetype': 'text/html',
            })

            # Return the HTML as a download
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

        # Create an attachment for the PDF
        filename = f"Calibration_Report_{self.line_id.equipment_id.name}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'calibration.schedule.line',
            'res_id': self.line_id.id,
            'mimetype': 'application/pdf',
        })

        # Return the PDF as a download
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class CalibrationStandardLength(models.Model):
    _name = 'calibration.standard.length'
    _description = 'Calibration Standard Length Measurements'
    _order = 'sequence'

    wizard_id = fields.Many2one('calibration.report.wizard', string='Wizard', ondelete='cascade')
    sequence = fields.Integer(string='Sr. No.')
    standard_length = fields.Float(string='Standard Length (mm)', digits=(10, 2))
    upper_reading = fields.Float(string='Upper Reading (mm)', digits=(10, 2))
    center_reading = fields.Float(string='Center Reading (mm)', digits=(10, 2))
    lower_reading = fields.Float(string='Lower Reading (mm)', digits=(10, 2))
    min_limit = fields.Float(string='Min Limit (mm)', digits=(10, 2))
    max_limit = fields.Float(string='Max Limit (mm)', digits=(10, 2))
    average = fields.Float(string='Average Reading (mm)', compute='_compute_average', store=True, digits=(10, 2))

    @api.depends('upper_reading', 'center_reading', 'lower_reading')
    def _compute_average(self):
        for record in self:
            readings = [
                reading for reading in [
                    record.upper_reading, record.center_reading, record.lower_reading
                ] if reading
            ]
            record.average = sum(readings) / len(readings) if readings else 0.0

    @api.onchange('standard_length')
    def _onchange_standard_length(self):
        if self.standard_length:
            self.min_limit = self.standard_length - 0.05
            self.max_limit = self.standard_length + 0.05

    @api.onchange('standard_length', 'upper_reading', 'center_reading', 'lower_reading')
    def _onchange_auto_save(self):
        """Automatically save when a measurement value is changed."""
        if self:
            self.write({
                'standard_length': self.standard_length,
                'upper_reading': self.upper_reading,
                'center_reading': self.center_reading,
                'lower_reading': self.lower_reading,
                'min_limit': self.standard_length - 0.05 if self.standard_length else 0.0,
                'max_limit': self.standard_length + 0.05 if self.standard_length else 0.0,
            })