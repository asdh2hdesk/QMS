from odoo import models, fields,api


class Observation(models.Model):
    _name = 'observation.record'
    _description = 'Observation Record'

    type = fields.Char(string='Type of Area', required=True)
    date = fields.Date(string='Date', required=True)
    observers = fields.Char(string='Observer(s)', required=True)
    observation_details_ids = fields.One2many('observation.details', 'observation_id', string='Observation Details')

class ObservationDetails(models.Model):
    _name = 'observation.details'
    _description = 'Observation Details'

    observation_id = fields.Many2one('observation.record', string='Observation', ondelete='cascade')
    sl_no = fields.Integer(string='Sl No', required=True)
    observations = fields.Text(string='Observations')
    observer_signature = fields.Binary(string='Observer Signature')
    corrective_actions = fields.Text(string='Corrective Actions')
    responsibility = fields.Char(string='Responsibility')
    target_date = fields.Date(string='Target Date')
    completed_date = fields.Date(string='Completed Date')
    verified = fields.Boolean(string='Verified')
    verified_date = fields.Date(string='Verified Date')
    verified_signature = fields.Binary(string='Verified Signature')
    vendor = fields.Char(string='Vendor')

    @api.depends('observation_id', 'observation_id.observation_details_ids')
    def _compute_sl_no(self):
        """Compute sl_no based on position in parent's observation details"""
        for observation in self.mapped('observation_id'):
            details = self.env['observation.details'].search([
                ('observation_id', '=', observation.id)
            ], order='id')
            for i, detail in enumerate(details, 1):
                detail.sl_no = i