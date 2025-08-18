from odoo import models, fields, api

class ProductionOrder(models.Model):
    _name = 'production.order'
    _description = 'Production Order'

    name = fields.Char(string='production no', required=True, copy=False, readonly=True,  default='xxx001')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty_produce = fields.Float(string='Quantity to Produce', required=True)
    planned_qty = fields.Float(string='Planned Quantity')
    actual_qty = fields.Float(string='Actual Quantity Produced')
    rejected_qty = fields.Float(string='Rejected Quantity', compute='_compute_rejected_qty', store=True)
    planned_date = fields.Datetime(string='Planned Date')
    shift = fields.Selection([
        ('shift_A', 'Shift A'),
        ('shift_B', 'Shift B'),
        ('shift_C', 'Shift C')
    ], string='Production Shift')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    order_line_ids = fields.One2many('production.order.line', 'production_order_id', string='Components')
    lot_ids = fields.One2many('production.lot', 'production_order_id', string='Lots')

    @api.depends('planned_qty', 'actual_qty')
    def _compute_rejected_qty(self):
        for order in self:
            if order.planned_qty and order.actual_qty:
                order.rejected_qty = order.planned_qty - order.actual_qty
            else:
                order.rejected_qty = 0.0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('production.order') or 'New'
        return super().create(vals)

    def action_confirm(self):
        for order in self:
            order.state = 'confirmed'

    def action_done(self):
        for order in self:
            order.state = 'done'

    def action_cancel(self):
        for order in self:
            order.state = 'cancelled'
