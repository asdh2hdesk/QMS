# models/ppm_analysis.py
from odoo import models, fields, api

class PPMAnalysis(models.Model):
    _name = 'ppm.analysis'
    _description = 'PPM (Parts Per Million) Analysis'
    _order = 'year desc, month'
    _inherit = "translation.mixin"

    name = fields.Char(string='Label', compute='_compute_name', store=True,translate=True)

    month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string="Month")

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year'
    )

    total_parts = fields.Integer(string='Total Parts Produced')
    defective_parts = fields.Integer(string='Defective Parts')
    ppm_level = fields.Float(string='PPM Level', compute='_compute_ppm', store=True)

    @api.model
    def _get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(2020, current_year + 6)]

    @api.depends('month', 'year')
    def _compute_name(self):
        month_names = dict(self._fields['month'].selection)
        for rec in self:
            if rec.month and rec.year:
                rec.name = f"{month_names.get(rec.month)} {rec.year}"
            else:
                rec.name = "PPM Entry"

    @api.depends('total_parts', 'defective_parts')
    def _compute_ppm(self):
        for rec in self:
            if rec.total_parts > 0:
                rec.ppm_level = (rec.defective_parts / rec.total_parts) * 1_000_000
            else:
                rec.ppm_level = 0.0

    @api.constrains('month', 'year')
    def _check_unique_entry(self):
        for rec in self:
            domain = [('month', '=', rec.month), ('year', '=', rec.year), ('id', '!=', rec.id)]
            if self.search_count(domain):
                raise models.ValidationError("This month and year entry already exists.")
