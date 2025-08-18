from odoo import models, fields

class ProductionLot(models.Model):
    _name = 'production.lot'
    _description = 'Lot/Serial Number'

    production_order_id = fields.Many2one('production.order', string='Production Order')
    name = fields.Char(string='Serial Number', required=True)
    product_id = fields.Many2one('product.product', string='Product')
