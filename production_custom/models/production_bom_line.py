from odoo import models, fields

class ProductionBOMLine(models.Model):
    _name = 'production.bom.line'
    _description = 'BOM Line'

    bom_id = fields.Many2one('production.bom', string='BOM')
    component_id = fields.Many2one('product.product', string='Component', required=True)
    quantity = fields.Float(string='Quantity', required=True)
