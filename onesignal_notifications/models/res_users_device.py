from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResUsersDevice(models.Model):
    _name = 'res.users.device'
    _description = "User Devices"
    _rec_name = 'player_id'

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade")
    player_id = fields.Char("OneSignal Player ID", required=True, index=True)
    device_name = fields.Char("Device Name")
    last_seen = fields.Datetime("Last Seen", default=fields.Datetime.now)
    active = fields.Boolean("Active", default=True)

    _sql_constraints = [
        ('unique_player_id', 'unique(player_id)', 'This Player ID is already registered!')
    ]

    @api.model
    def register_device(self, player_id, device_name=None):
        """Register or update a device for the current logged-in user"""
        user = self.env.user
        device = self.search([('player_id', '=', player_id)], limit=1)

        if device:
            device.write({
                'user_id': user.id,
                'device_name': device_name or device.device_name,
                'last_seen': fields.Datetime.now(),
                'active': True
            })
            _logger.info(f"Updated device {player_id} for user {user.login}")
        else:
            self.create({
                'user_id': user.id,
                'player_id': player_id,
                'device_name': device_name or 'Unknown',
                'last_seen': fields.Datetime.now(),
                'active': True
            })
            _logger.info(f"Registered new device {player_id} for user {user.login}")
        return True

    @api.model
    def unregister_device(self, player_id):
        """Deactivate device on logout"""
        device = self.search([('player_id', '=', player_id)], limit=1)
        if device:
            device.write({'active': False})
            _logger.info(f"Unregistered device {player_id} for user {device.user_id.login}")
        return True
