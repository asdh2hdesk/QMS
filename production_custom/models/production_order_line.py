from odoo import models, fields

class ProductionOrderLine(models.Model):
    _name = 'production.order.line'
    _description = 'Production Order Line'

    production_order_id = fields.Many2one('production.order', string='Production Order')
    raw_material_id = fields.Many2one('product.product', string='Raw Material', required=True)
    quantity_required = fields.Float(string='Quantity Required', required=True)
    quantity_consumed = fields.Float(string='Quantity Consumed')
