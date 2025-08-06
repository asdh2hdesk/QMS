from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    onesignal_player_id = fields.Char('OneSignal Player ID')
    onesignal_device_info = fields.Text('Device Info')

    def update_onesignal_player_id(self, player_id):
        """Update the current user's OneSignal Player ID"""
        self.write({'onesignal_player_id': player_id})
        _logger.info(f"Updated OneSignal Player ID for user {self.name}: {player_id}")
        return True

    def send_onesignal_notification(self, title, message, data=None):
        """Send OneSignal notification to this user"""
        if not self.onesignal_player_id:
            _logger.warning(f"No OneSignal Player ID for user {self.name}")
            return False

        app_id = self.env['ir.config_parameter'].sudo().get_param('onesignal.app_id')
        rest_api_key = self.env['ir.config_parameter'].sudo().get_param('onesignal.rest_api_key')

        if not app_id or not rest_api_key:
            _logger.error("OneSignal configuration missing")
            return False

        headers = {
            'Authorization': f'Basic {rest_api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'app_id': app_id,
            'include_player_ids': [self.onesignal_player_id],
            'headings': {'en': title},
            'contents': {'en': message},
        }

        if data:
            payload['data'] = data

        try:
            response = requests.post(
                'https://onesignal.com/api/v1/notifications',
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                _logger.info(f"OneSignal notification sent to {self.name}: {title}")
                return True
            else:
                _logger.error(f"OneSignal API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Error sending OneSignal notification: {e}")
            return False