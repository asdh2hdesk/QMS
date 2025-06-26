# models/oee_analysis.py
from odoo import models, fields, api


class OEEAnalysis(models.Model):
    _name = 'oee.analysis'
    _description = 'OEE (Overall Equipment Effectiveness) Analysis'
    _order = 'year desc, month'
    _inherit = "translation.mixin"

    name = fields.Char(string='Label', compute='_compute_name', store=True,translate=True)


    month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string="Month", required=True)

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True
    )

    planned_efficiency = fields.Float(string='Planned Efficiency (%)', required=True)
    actual_efficiency = fields.Float(string='Actual Efficiency (%)', default=0.0)
    efficiency_gap = fields.Float(string='Efficiency Gap (%)', compute='_compute_efficiency_gap', store=True)

    @api.model
    def _get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(2020, current_year + 6)]

    @api.depends('month', 'year')
    def _compute_name(self):
        month_names = dict(self._fields['month'].selection)
        for rec in self:
            rec.name = f"{month_names.get(rec.month)} {rec.year}"

    @api.depends('actual_efficiency', 'planned_efficiency')
    def _compute_efficiency_gap(self):
        for rec in self:
            rec.efficiency_gap = rec.actual_efficiency - rec.planned_efficiency

    @api.constrains( 'month', 'year')
    def _check_unique_entry(self):
        for rec in self:
            domain = [

                ('month', '=', rec.month),
                ('year', '=', rec.year),
                ('id', '!=', rec.id)
            ]
            if self.search_count(domain):
                raise models.ValidationError("This equipment already has a record for the given month and year.")
