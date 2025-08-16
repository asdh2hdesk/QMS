from odoo import models, fields, api
import logging
import json

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    device_ids = fields.One2many(
        "res.users.device",
        "user_id",
        string="Devices"
    )

    # OneSignal Player ID field
    # onesignal_player_id = fields.Char(
    #     'OneSignal Player ID',
    #     help="OneSignal Player ID for push notifications"
    # )
    # onesignal_device_info = fields.Text(
    #     'Device Info',
    #     help="Device information for OneSignal"
    # )
    # onesignal_last_updated = fields.Datetime(
    #     'OneSignal Last Updated',
    #     default=fields.Datetime.now
    # )

    def update_onesignal_player_id(self, player_id, device_info=None):
        """Update OneSignal Player ID for current user"""
        current_user = self.env.user
        current_user.write({
            'onesignal_player_id': player_id,
            'onesignal_device_info': device_info or '{}',
            'onesignal_last_updated': fields.Datetime.now()
        })
        _logger.info(f"Updated OneSignal Player ID for user {current_user.login}: {player_id}")
        return True

    def send_notification_to_user(self, title, message, notification_type='custom', data=None):
        """Send notification to all active devices of this user"""
        devices = self.device_ids.filtered(lambda d: d.active)
        if not devices:
            return False

        player_ids = devices.mapped("player_id")

        return self.env["onesignal.notification"].send_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            recipient_ids=player_ids,
            data=data
        )
        #
        # except Exception as e:
        #     _logger.error(f"Error sending notification to user {self.login}: {str(e)}")
        #     return False

    def send_chat_notification(self, sender_name, message, channel_id=None):
        """Send chat notification to this user"""
        notification_data = {
            'type': 'chat',
            'sender': sender_name,
            'message': message,
            'channel_id': channel_id or 'general',
            'user_id': self.id,
        }

        return self.send_notification_to_user(
            title=f"New message from {sender_name}",
            message=message,
            notification_type='chat',
            data=notification_data
        )

    def send_odoo_notification(self, model_name, record_name, message, action_id=None):
        """Send Odoo-specific notification to this user"""
        notification_data = {
            'type': 'odoo_message',
            'model': model_name,
            'record_name': record_name,
            'message': message,
            'action_id': action_id,
            'user_id': self.id,
        }

        return self.send_notification_to_user(
            title=f"Update in {model_name}",
            message=message,
            notification_type='custom',
            data=notification_data
        )

    @api.model
    def send_notification_to_users(self, user_ids, title, message, notification_type='custom', data=None):
        """Send notification to multiple specific users"""
        users = self.browse(user_ids).filtered('onesignal_player_id')

        if not users:
            _logger.warning("No users found with OneSignal Player IDs")
            return False

        player_ids = users.mapped('onesignal_player_id')

        # Add user_ids to data for reference
        if data is None:
            data = {}
        data['target_user_ids'] = user_ids

        try:
            return self.env['onesignal.notification'].send_notification(
                title=title,
                message=message,
                notification_type=notification_type,
                recipient_ids=player_ids,
                data=data
            )
        except Exception as e:
            _logger.error(f"Error sending notification to users {user_ids}: {str(e)}")
            return False

    def get_users_with_onesignal(self):
        """Get all users that have OneSignal Player IDs"""
        return self.search([('onesignal_player_id', '!=', False)])

    def clear_onesignal_data(self):
        """Clear OneSignal data for this user (useful for logout)"""
        self.write({
            'onesignal_player_id': False,
            'onesignal_device_info': False,
            'onesignal_last_updated': fields.Datetime.now()
        })
        _logger.info(f"Cleared OneSignal data for user {self.login}")
        return True