

from odoo import models, fields,api


class VehicleInspectionSheet(models.Model):
    _name = 'vehicle.inspection.sheet'
    _description = 'Vehicle Inspection Sheet'

    inspection_line_ids = fields.One2many(
        'vehicle.inspection.register',
        'sheet_id',
        string='Inspection Entries'
    )


class VehicleInspectionRegister(models.Model):
    _name = 'vehicle.inspection.register'
    _description = 'Inspection Register for PUC & Driving License'
    sheet_id = fields.Many2one('vehicle.inspection.sheet', string='Inspection Sheet', ondelete='cascade')

    sl_no = fields.Integer(string='Sl No', compute='_compute_sl_no', store=True)
    category_of_vehicle = fields.Char(string='Category of Vehicle')
    vehicle_no = fields.Char(string='Vehicle No.')
    vehicle_belongs_to = fields.Char(string='Vehicle Belongs To')

    rc_status = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string='RC Status')

    insurance_status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('not_available', 'Not Available')
    ], string='Insurance Status')

    emission_status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('not_available', 'Not Available')
    ], string='Emission Status (Poll. Cert.)')
    emission_valid_upto = fields.Date(string='Emission Valid Upto')

    license_status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('not_available', 'Not Available')
    ], string='Driving License Status')
    license_valid_upto = fields.Date(string='License Valid Upto')

    checked_by = fields.Many2one('res.users', string='Checked By (S/S)' )  # fields.Char(string='Checked By (S/S)')
    verified_by = fields.Many2one('res.users',string='Verified By (HR Rep.)')  # fields.Char(string='Verified By (HR Rep.)')
    reviewed_by = fields.Many2one('res.users', string='Reviewed By (HR & Admin)')  # fields.Char(string='Reviewed By (HR & Admin)')

    @api.depends('sheet_id', 'sheet_id.inspection_line_ids')
    def _compute_sl_no(self):
        """Compute sl_no based on position in sheet's inspection entries"""
        for sheet in self.mapped('sheet_id'):
            inspection_entries = self.env['vehicle.inspection.register'].search([
                ('sheet_id', '=', sheet.id)
            ], order='id')
            for i, entry in enumerate(inspection_entries, 1):
                entry.sl_no = i
