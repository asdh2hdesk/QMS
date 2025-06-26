from odoo import fields, models

class Inspection(models.Model):
    _name = 'inspection.report'
    _description = 'Report of inspection'
    _inherit = "translation.mixin"

    customer = fields.Char("Customer/Supplier Name", required=True,translate=True)
    part = fields.Char("Part Name", required=True,translate=True)
    drawing_no = fields.Integer("Drawing No.", required=True)
    sample_Description = fields.Char("Sample Description", required=True,translate=True)
    part_no = fields.Integer("Part NO.", required=True)
    rev_no = fields.Integer("Rev. No.", required=True)
    level = fields.Char("Level", required=True,translate=True)

    inspection_line_ids = fields.One2many(
        comodel_name='inspection.line',
        inverse_name='inspection_id',
        string="Inspection Lines"
    )

class InspectionLine(models.Model):
    _name = 'inspection.line'
    _description = 'Report of inspection Line'
    _inherit = "translation.mixin"

    series = fields.Char("Sr. No.",translate=True)
    dimension = fields.Char("Dimension Description",translate=True)
    specification = fields.Char("Dimension Specification",translate=True)
    mi = fields.Char("M. I.",translate=True)
    observation1 = fields.Char(string='Observation 1',translate=True)
    observation2 = fields.Char(string='Observation 2',translate=True)
    observation3 = fields.Char(string='Observation 3',translate=True)
    observation4 = fields.Char(string='Observation 4',translate=True)
    observation5 = fields.Char(string='Observation 5',translate=True)
    remarks = fields.Char("Remarks",translate=True)
    inspection_id = fields.Many2one('inspection.report', string='Inspection', ondelete='cascade')
