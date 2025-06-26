from odoo import models, fields, api

class ProductionAnalysis(models.Model):
    _name = 'production.analysis'
    _description = 'Monthly Production Analysis'
    _order = 'year desc, month'
    _inherit = "translation.mixin"

    name = fields.Char(string='Month', compute='_compute_name', store=True,translate=True)
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], string="Month", required=True)
    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True
    )
    planned_production = fields.Integer(string='Planned Production', default=0)
    actual_production = fields.Integer(string='Actual Production', default=0)
    achievement_rate = fields.Float(string='Achievement Rate (%)', compute='_compute_achievement_rate', store=True)

    @api.model
    def _get_year_selection(self):
        # Generate years from 2020 to current year + 5
        current_year = fields.Date.today().year
        return [(str(year), str(year)) for year in range(2020, current_year + 6)]

    @api.depends('month', 'year')
    def _compute_name(self):
        month_names = dict(self._fields['month'].selection)
        for record in self:
            if record.month and record.year:
                record.name = f"{month_names[record.month]} {record.year}"
            else:
                record.name = "New Analysis"

    @api.depends('planned_production', 'actual_production')
    def _compute_achievement_rate(self):
        for record in self:
            if record.planned_production:
                # Calculate percentage correctly by dividing actual by planned and multiplying by 100
                achievement = (record.actual_production / record.planned_production)
                record.achievement_rate = achievement
            else:
                record.achievement_rate = 0.0

    @api.constrains('year', 'month')
    def _check_unique_month_year(self):
        for record in self:
            domain = [
                ('year', '=', record.year),
                ('month', '=', record.month),
                ('id', '!=', record.id)
            ]
            if self.search_count(domain) > 0:
                raise models.ValidationError("A record for this month and year already exists!")