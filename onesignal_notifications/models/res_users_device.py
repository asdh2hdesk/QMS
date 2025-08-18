from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ResUsersDevice(models.Model):
    _name = 'res.users.device'
    _description = "User Devices"
    _rec_name = 'player_id'
    _order = 'last_seen desc'

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade", index=True)
    player_id = fields.Char("OneSignal Player ID", required=True, index=True)
    device_name = fields.Char("Device Name")
    device_type = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web Browser'),
        ('other', 'Other')
    ], string="Device Type", default='other')
    platform = fields.Char("Platform")
    app_version = fields.Char("App Version")
    os_version = fields.Char("OS Version")
    last_seen = fields.Datetime("Last Seen", default=fields.Datetime.now)
    created_at = fields.Datetime("Registered At", default=fields.Datetime.now, readonly=True)
    active = fields.Boolean("Active", default=True)
    push_enabled = fields.Boolean("Push Notifications Enabled", default=True)

    # Computed fields
    device_display_name = fields.Char("Display Name", compute="_compute_device_display_name", store=True)
    days_since_seen = fields.Integer("Days Since Last Seen", compute="_compute_days_since_seen")
    is_online = fields.Boolean("Is Online", compute="_compute_is_online")

    _sql_constraints = [
        ('unique_player_id', 'unique(player_id)', 'This Player ID is already registered!'),
        ('check_player_id', 'CHECK(LENGTH(player_id) > 10)', 'Player ID seems invalid (too short)')
    ]

    @api.depends('device_name', 'device_type', 'player_id')
    def _compute_device_display_name(self):
        for record in self:
            try:
                if record.device_name:
                    # Get the display value for selection field
                    device_type_display = dict(record._fields['device_type'].selection).get(record.device_type, 'Unknown')
                    record.device_display_name = f"{record.device_name} ({device_type_display})"
                else:
                    device_type_display = dict(record._fields['device_type'].selection).get(record.device_type, 'Unknown')
                    player_id_short = record.player_id[:8] + '...' if record.player_id and len(record.player_id) > 8 else (record.player_id or 'Unknown')
                    record.device_display_name = f"{device_type_display} Device - {player_id_short}"
            except Exception as e:
                _logger.error(f"Error computing device display name: {e}")
                record.device_display_name = f"Device - {record.player_id[:8] if record.player_id else 'Unknown'}"

    @api.depends('last_seen')
    def _compute_days_since_seen(self):
        for record in self:
            if record.last_seen:
                try:
                    delta = fields.Datetime.now() - record.last_seen
                    record.days_since_seen = delta.days
                except:
                    record.days_since_seen = 999
            else:
                record.days_since_seen = 999

    @api.depends('last_seen')
    def _compute_is_online(self):
        """Consider device online if seen within last 5 minutes"""
        try:
            threshold = fields.Datetime.now() - timedelta(minutes=5)
            for record in self:
                record.is_online = bool(record.last_seen and record.last_seen >= threshold)
        except Exception as e:
            _logger.error(f"Error computing is_online: {e}")
            for record in self:
                record.is_online = False

    @api.model
    def register_device(self, player_id, device_name=None, device_type='other',
                        platform=None, app_version=None, os_version=None):
        """Register or update a device for the current logged-in user"""
        if not player_id or len(player_id) < 10:
            raise ValidationError("Invalid Player ID provided")

        user = self.env.user
        device = self.search([('player_id', '=', player_id)], limit=1)

        values = {
            'user_id': user.id,
            'device_name': device_name,
            'device_type': device_type,
            'platform': platform,
            'app_version': app_version,
            'os_version': os_version,
            'last_seen': fields.Datetime.now(),
            'active': True,
            'push_enabled': True
        }

        if device:
            # Update existing device
            device.write(values)
            _logger.info(f"Updated device {player_id[:8]}... for user {user.login}")
            return device.id
        else:
            # Create new device
            values['device_name'] = device_name or 'Unknown Device'
            device = self.create(values)
            _logger.info(f"Registered new device {player_id[:8]}... for user {user.login}")
            return device.id

    @api.model
    def unregister_device(self, player_id):
        """Deactivate device on logout"""
        device = self.search([('player_id', '=', player_id)], limit=1)
        if device:
            device.write({'active': False, 'push_enabled': False})
            _logger.info(f"Unregistered device {player_id[:8]}... for user {device.user_id.login}")
            return True
        return False

    @api.model
    def update_last_seen(self, player_id):
        """Update last seen timestamp for a device"""
        device = self.search([('player_id', '=', player_id)], limit=1)
        if device:
            device.write({'last_seen': fields.Datetime.now()})
            return True
        return False

    @api.model
    def get_user_devices(self, user_id=None, active_only=True):
        """Get all devices for a user"""
        domain = []
        if user_id:
            domain.append(('user_id', '=', user_id))
        else:
            domain.append(('user_id', '=', self.env.user.id))

        if active_only:
            domain.append(('active', '=', True))

        return self.search(domain)

    @api.model
    def cleanup_old_devices(self, days=30):
        """Clean up devices that haven't been seen for X days"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_devices = self.search([
            ('last_seen', '<', cutoff_date),
            ('active', '=', True)
        ])

        if old_devices:
            old_devices.write({'active': False})
            _logger.info(f"Deactivated {len(old_devices)} old devices")

        return len(old_devices)

    def toggle_push_notifications(self):
        """Toggle push notification setting for device"""
        for device in self:
            device.push_enabled = not device.push_enabled
            _logger.info(
                f"Push notifications {'enabled' if device.push_enabled else 'disabled'} for device {device.player_id[:8]}...")

    @api.model
    def get_active_player_ids(self, user_ids=None):
        """Get all active player IDs, optionally filtered by user IDs"""
        domain = [('active', '=', True), ('push_enabled', '=', True)]
        if user_ids:
            domain.append(('user_id', 'in', user_ids))

        devices = self.search(domain)
        return devices.mapped('player_id')

    def name_get(self):
        """Custom name display for devices"""
        result = []
        for record in self:
            try:
                name = record.device_display_name or record.player_id or f"Device {record.id}"
            except:
                name = f"Device {record.id}"
            result.append((record.id, name))
        return result