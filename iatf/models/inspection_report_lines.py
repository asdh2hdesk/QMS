from odoo import models, fields

class Inspection(models.Model):
    _name = 'inspection'
    _description = 'Inspection'
    _inherit = "translation.mixin"

    name = fields.Char(string='Inspection Name', required=True,translate=True)
    line_ids = fields.One2many('inspection.line', 'inspection_id', string='Inspection Lines')

class InspectionLine(models.Model):
    _name = 'inspection.line'
    _description = 'Inspection Line'
    _inherit = "translation.mixin"

    name = fields.Char(string='Line Description', required=True,translate=True)
    inspection_id = fields.Many2one('inspection', string='Inspection', ondelete='cascade')
