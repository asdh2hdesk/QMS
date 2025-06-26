from odoo import models, fields,api

class LegalRegisterMatrix(models.Model):
    _name = 'legal.register.matrix'
    _description = 'Legal Register Compliance Matrix'

    company = fields.Many2one('res.company', string='Company')
    legal_ids = fields.One2many('legal.register', 'matrix_id', string='Legal Descriptions')


class LegalRegister(models.Model):
    _name = 'legal.register'
    _description = 'Legal Register'

    matrix_id = fields.Many2one('legal.register.matrix', string='Legal Register Matrix', ondelete='cascade')
    serial_no = fields.Integer(string='S. No',compute='_compute_serial_no', store=True)
    rules = fields.Char(string='Title of Applicable Rule / Regulations / Other Requirements')
    line_ids = fields.One2many('legal.register.line', 'register_id', string='Descriptions')

    @api.depends('matrix_id', 'matrix_id.legal_ids')
    def _compute_serial_no(self):
        """Compute serial_no based on position in matrix's legal records"""
        for matrix in self.mapped('matrix_id'):
            legal_records = self.env['legal.register'].search([
                ('matrix_id', '=', matrix.id)
            ], order='id')
            for i, record in enumerate(legal_records, 1):
                record.serial_no = i


class LegalRegisterLine(models.Model):
    _name = 'legal.register.line'
    _description = 'Legal Register Line Entry'

    register_id = fields.Many2one('legal.register', string='Legal Register', ondelete='cascade')
    description = fields.Text(string='Brief Description of Requirement')
    responsibility = fields.Many2one('res.users', string='Responsibility')
    statutory_body = fields.Char(string='Statutory Body')
    frequency = fields.Char(string='Frequency of Submission / Noncompliance')
    due_date = fields.Date(string='Due Date of Submission')
    license_no = fields.Char(string='License / Consent No.')
    license_validity = fields.Date(string='License / Consent Validity')
    remarks = fields.Text(string='Remarks')
    status = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='Status', default='available')
