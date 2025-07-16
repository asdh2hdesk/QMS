from odoo import models, fields, api, _


class EhsParent(models.Model):
    _name = 'ehs.parent'
    _description = 'EHS Compliance Monitoring Check Sheet Parent'

    # company = fields.Many2one('res.company', string='Company')
    lines_ids = fields.One2many('ehs.compliance.monitoring.check.sheet', 'line_id', string='Lines')


class EhsComplianceMonitoringCheckSheet(models.Model):
    _name = 'ehs.compliance.monitoring.check.sheet'
    _description = 'EHS Compliance Monitoring Check Sheet'

    line_id = fields.Many2one('ehs.parent', string="EHS Compliance")

    # Auto-increment sr_no field
    sr_no = fields.Integer(string='Sr. No.', compute='_compute_sr_no', store=True)
    license_name = fields.Char(string='License Reference (Name)')
    license_reference_no = fields.Char(string='License Reference (No) / QTY')
    valid_from = fields.Date(string='Valid From / Carried out on')
    valid_upto = fields.Date(string='Valid Upto / Disposal or Usage Qty')

    @api.depends('line_id', 'line_id.lines_ids')
    def _compute_sr_no(self):
        """Compute sr_no based on position in parent's lines"""
        for parent in self.mapped('line_id'):
            lines = self.env['ehs.compliance.monitoring.check.sheet'].search([
                ('line_id', '=', parent.id)
            ], order='id')
            for i, line in enumerate(lines, 1):
                line.sr_no = i