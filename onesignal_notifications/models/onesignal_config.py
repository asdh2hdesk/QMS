from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class OneSignalConfig(models.Model):
    _name = 'onesignal.config'
    _description = 'OneSignal Configuration'
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True, default='Default OneSignal Config')
    app_id = fields.Char('OneSignal App ID', required=True, help='Your OneSignal App ID')
    rest_api_key = fields.Char('REST API Key', required=True, help='Your OneSignal REST API Key')
    user_auth_key = fields.Char('User Auth Key', help='Your OneSignal User Auth Key (optional)')
    active = fields.Boolean('Active', default=True)


    # Notification settings
    send_chat_notifications = fields.Boolean('Send Chat Notifications', default=True)
    send_email_notifications = fields.Boolean('Send Email Notifications', default=True)
    send_alert_notifications = fields.Boolean('Send Alert Notifications', default=True)

    @api.model
    def get_active_config(self):
        """Get the active OneSignal configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise ValueError("No active OneSignal configuration found")
        return config

    def test_connection(self):
        """Test OneSignal API connection"""
        try:
            # Test by getting app details
            url = f"https://onesignal.com/api/v1/apps/{self.app_id}"

            headers = {
                'Authorization': f'Basic {self.rest_api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                app_data = response.json()
                app_name = app_data.get('name', 'Unknown App')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success!',
                        'message': f'OneSignal connection successful! App: {app_name}',
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error!',
                        'message': f'Connection failed: {response.status_code} - {response.text}',
                        'type': 'danger',
                    }
                }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Error!',
                    'message': f'Failed to connect: {str(e)}',
                    'type': 'danger',
                }
            }