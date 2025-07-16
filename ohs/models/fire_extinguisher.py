from odoo import models, fields, api


class FireExtinguisherChecklist(models.Model):
    _name = 'fire.extinguisher.checklist'
    _description = 'Fire Extinguisher Checklist'

    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    # company = fields.Many2one('res.company', string='Company')
    prepared_by = fields.Many2one('res.users', string='Prepared By')
    approved_by = fields.Many2one('res.users', string='Approved By', default=lambda self: self.env.user)
    checklist_details_ids = fields.One2many('fire.extinguisher.details', 'checklist_id', string='Checklist Details')
    summary_ids = fields.One2many('fire.extinguisher.summary', 'checklist_id', string='Summary')


class FireExtinguisherDetails(models.Model):
    _name = 'fire.extinguisher.details'
    _description = 'Fire Extinguisher Details'

    checklist_id = fields.Many2one('fire.extinguisher.checklist', string='Checklist', ondelete='cascade')
    sl_no = fields.Integer(string='Sl No', compute='_compute_sl_no', store=True, readonly=True)
    location = fields.Char(string='Location')
    code = fields.Char(string='Code')
    type = fields.Selection([('co2', 'CO2'), ('dcp', 'DCP'), ('mf', 'MF'), ('abc', 'ABC')], string='Type')
    capacity = fields.Char(string='Capacity')
    last_date = fields.Date(string='Refilled Date')
    due_date = fields.Date(string='Refill Due Date')

    location_note = fields.Boolean(
        string='Fire Extinguishers Should be in his identified location and Distance maintain properly as per Std. with in 15 mtr. Radius & Hight maintained with in 1.2 mtr. From floor to till bottom of Extinguishers')
    condition_note = fields.Boolean(string='extinguisher should be neat and clean')
    air_pressure_note = fields.Boolean(string='Air pressure should be in Green Zone (11-18.5) For ABC type')
    weight = fields.Char(string='Weight for CO2')
    seal_note = fields.Boolean(string='Seal should be provided on lever pin')

    @api.depends('checklist_id', 'checklist_id.checklist_details_ids')
    def _compute_sl_no(self):
        """Compute sl_no based on position in checklist's details"""
        for checklist in self.mapped('checklist_id'):
            details = self.env['fire.extinguisher.details'].search([
                ('checklist_id', '=', checklist.id)
            ], order='id')
            for i, detail in enumerate(details, 1):
                detail.sl_no = i


class FireExtinguisherSummary(models.Model):
    _name = 'fire.extinguisher.summary'
    _description = 'Fire Extinguisher Summary'

    checklist_id = fields.Many2one('fire.extinguisher.checklist', string='Checklist', ondelete='cascade')
    sl_no = fields.Integer(string='Sl No', compute='_compute_sl_no', store=True, readonly=True)
    extinguisher_type = fields.Char(string='Type of Fire Extinguisher')
    quantity = fields.Integer(string='Qty')
    remarks = fields.Char(string='Remarks')

    @api.depends('checklist_id', 'checklist_id.summary_ids')
    def _compute_sl_no(self):
        """Compute sl_no based on position in checklist's summary lines"""
        for checklist in self.mapped('checklist_id'):
            summary_lines = self.env['fire.extinguisher.summary'].search([
                ('checklist_id', '=', checklist.id)
            ], order='id')
            for i, line in enumerate(summary_lines, 1):
                line.sl_no = i