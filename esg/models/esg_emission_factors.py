from odoo import fields, models, api,_




class ESGEmissionFactor(models.Model):
    _name = 'esg.emission.factor'
    _description = 'Emission Factor'

    name = fields.Char(required=True)
    activity_id = fields.Many2one('esg.emission.activity', required=True)
    original_unit = fields.Char()
    target_unit = fields.Char()
    conversion_rate = fields.Float()