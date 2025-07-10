
from odoo import models, fields, api, _
class ESGEmissionActivity(models.Model):
    _name = 'esg.emission.activity'
    _description = 'Emission Activity'

    name = fields.Char(required=True)
    activity_type = fields.Char()
    description = fields.Text()