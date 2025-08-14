from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class OneSignalNotification(models.Model):
    _name = 'onesignal.notification'
    _description = 'OneSignal Notification Log'
    _order = 'create_date desc'

    name = fields.Char('Notification Title', required=True)
    message = fields.Text('Message Content', required=True)
    notification_type = fields.Selection([
        ('chat', 'Chat Message'),
        ('email', 'Email'),
        ('alert', 'Alert'),
        ('custom', 'Custom')
    ], string='Type', required=True, default='custom')

    recipient_ids = fields.Text('Recipient IDs', help='JSON list of OneSignal player IDs')
    segments = fields.Text('Segments', help='JSON list of segments to send to')
    send_to_all = fields.Boolean('Send to All Users', default=False)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ], string='Status', default='draft')

    onesignal_id = fields.Char('OneSignal Notification ID')
    error_message = fields.Text('Error Message')

    # Additional data
    data = fields.Text('Additional Data', help='JSON data to send with notification')
    url = fields.Char('URL', help='URL to open when notification is clicked')
    large_icon = fields.Char('Large Icon URL')
    big_picture = fields.Char('Big Picture URL')

    @api.model
    def send_notification(self, title, message, notification_type='custom',
                          recipient_ids=None, segments=None, send_to_all=False,
                          data=None, url=None, large_icon=None, big_picture=None):
        """Send notification via OneSignal API"""

        notification = None
        try:
            config = self.env['onesignal.config'].get_active_config()

            # Create notification record
            notification = self.create({
                'name': title,
                'message': message,
                'notification_type': notification_type,
                'recipient_ids': json.dumps(recipient_ids) if recipient_ids else None,
                'segments': json.dumps(segments) if segments else None,
                'send_to_all': send_to_all,
                'data': json.dumps(data) if data else None,
                'url': url,
                'large_icon': large_icon,
                'big_picture': big_picture,
            })

            # Prepare OneSignal payload
            payload = {
                'app_id': config.app_id,
                'headings': {'en': title},
                'contents': {'en': message},
            }

            # Set recipients
            if send_to_all:
                payload['included_segments'] = ['All']
            elif segments:
                payload['included_segments'] = segments
            elif recipient_ids:
                payload['include_player_ids'] = recipient_ids
            else:
                payload['included_segments'] = ['All']

            # Add additional data
            if data:
                payload['data'] = data
            if url:
                payload['url'] = url
            if large_icon:
                payload['large_icon'] = large_icon
            if big_picture:
                payload['big_picture'] = big_picture

            # Send notification - THIS WAS THE BUG!
            headers = {
                'Authorization': f'Basic {config.rest_api_key}',  # Fixed: was self.rest_api_key
                'Content-Type': 'application/json'
            }

            response = requests.post(
                'https://onesignal.com/api/v1/notifications',
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                notification.write({
                    'status': 'sent',
                    'onesignal_id': result.get('id')
                })
                _logger.info(f"OneSignal notification sent successfully: {result.get('id')}")
                # _logger.info(f"OneSignal notification sent successfully: {result.get('recipient_ids')}")
                _logger.debug(f"Full OneSignal response: {json.dumps(result, indent=2)}")

                return notification
            else:
                error_msg = f"OneSignal API error: {response.status_code} - {response.text}"
                notification.write({
                    'status': 'failed',
                    'error_message': error_msg
                })
                _logger.error(error_msg)
                return False

        except Exception as e:
            error_msg = f"Failed to send OneSignal notification: {str(e)}"
            _logger.error(error_msg)
            if notification:
                notification.write({
                    'status': 'failed',
                    'error_message': error_msg
                })
            return False


    def clean_old_notifications(self, days=30):
        """Clean notifications older than specified days"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        old_notifications = self.search([
            ('create_date', '<', cutoff_date.strftime('%Y-%m-%d %H:%M:%S'))
        ])
        count = len(old_notifications)
        old_notifications.unlink()
        _logger.info(f"Cleaned {count} old OneSignal notifications")
        return count