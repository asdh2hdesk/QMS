from odoo import models, fields

class ProductionBOM(models.Model):
    _name = 'production.bom'
    _description = 'Bill of Materials'

    name = fields.Char(string='Reference', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    bom_line_ids = fields.One2many('production.bom.line', 'bom_id', string='Components')
