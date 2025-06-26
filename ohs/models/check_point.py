from odoo import models, fields,api

class CheckPointMaster(models.Model):
    _name = 'check.point.master'
    _description = 'Check Point Master'


    date = fields.Date(string='Date', default=fields.Date.today)
    company = fields.Many2one('res.company', string='Company')
    check_point_ids = fields.One2many('check.point', 'master_id', string='Check Points')

class CheckPoint(models.Model):
    _name = 'check.point'
    _description = 'Check Point'

    master_id = fields.Many2one('check.point.master', string='Master Checklist', ondelete='cascade')
    sl_no = fields.Integer(string='Sl No', required=True)
    hydrant_location = fields.Many2one('hydrant.location', string='Hydrant Location', required=True)
    type = fields.Selection([
        ('fire_hose_box', 'Fire Hose Box'),
        ('fire_hose_reel', 'Fire Hose Reel')
    ], string='Type')
    qty = fields.Integer(string='Qty')
    no_blockage = fields.Boolean(string='No Blockage in Pipe Line')
    water_pressure = fields.Boolean(string='Water Pressure should be ok as per required')
    no_leakage = fields.Boolean(string='No Leakage in Pipe')
    remark = fields.Char(string='Remark')
    ok_qty = fields.Integer(string='OK Qty')
    ng_qty = fields.Integer(string='NG Qty')
    checked_by = fields.Char(string='Checked By')
    approved_by = fields.Char(string='Approved By')

    @api.depends('master_id', 'master_id.check_point_ids')
    def _compute_sl_no(self):
        """Compute sl_no based on position in master's check points"""
        for master in self.mapped('master_id'):
            check_points = self.env['check.point'].search([
                ('master_id', '=', master.id)
            ], order='id')
            for i, check_point in enumerate(check_points, 1):
                check_point.sl_no = i

class HydrantLocation(models.Model):
    _name = 'hydrant.location'
    _description = 'Hydrant Location'

    hydrant_location = fields.Char(string='Location Name', required=True)