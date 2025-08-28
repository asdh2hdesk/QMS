from odoo import models, fields, api
import requests
import json
import logging
import ast

_logger = logging.getLogger(__name__)


class OneSignalNotification(models.Model):
    _name = 'onesignal.notification'
    _description = 'OneSignal Notification Log'
    _order = 'create_date desc'

    name = fields.Char('Notification Title', required=True)
    message = fields.Text('Message Content', required=True)
    notification_type = fields.Selection([
        ('chat', 'Chat Message'),
        ('mail', 'Email'),
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
                          user_ids=None,
                          data=None, url=None, large_icon=None, big_picture=None):
        """Send notification via OneSignal API"""

        notification = None
        try:
            config = self.env['onesignal.config'].get_active_config()

            if user_ids and not recipient_ids:
                recipient_ids = self.get_recipient_ids_for_users(user_ids)
                if not recipient_ids:
                    _logger.warning(f"No active devices found for users {user_ids}")
                    return False

            # FIXED: Don't truncate message content when creating the notification record
            notification = self.create({
                'name': title,
                'message': message,  # Store full message without truncation
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
                'contents': {'en': message},  # Send full message to OneSignal
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

            # IMPROVED: Add message length limits for OneSignal
            # OneSignal has limits: title max 64 chars, message max 4000 chars
            if len(title) > 64:
                payload['headings']['en'] = title[:61] + '...'
                _logger.info(f"Truncated title from {len(title)} to 64 characters")

            if len(message) > 4000:
                payload['contents']['en'] = message[:3997] + '...'
                _logger.info(f"Truncated message from {len(message)} to 4000 characters")

            # Send notification
            headers = {
                'Authorization': f'Basic {config.rest_api_key}',
                'Content-Type': 'application/json'
            }

            _logger.info(f"Sending notification to player IDs: {recipient_ids}")
            _logger.info(f"Message length: {len(message)} characters")
            _logger.info(f"Payload contents length: {len(payload['contents']['en'])}")

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
                _logger.info(f"Recipients: {result.get('recipients', 'N/A')}")
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
            _logger.error(error_msg, exc_info=True)
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

    def action_send_custom(self):
        for rec in self:
            recipient_ids = None
            segments = None
            data = None

            if rec.recipient_ids:
                try:
                    recipient_ids = json.loads(rec.recipient_ids)
                except Exception:
                    try:
                        recipient_ids = ast.literal_eval(rec.recipient_ids)
                    except Exception:
                        recipient_ids = [rec.recipient_ids]

            if rec.segments:
                try:
                    segments = json.loads(rec.segments)
                except Exception:
                    try:
                        segments = ast.literal_eval(rec.segments)
                    except Exception:
                        segments = [rec.segments]

            if rec.data:
                try:
                    data = json.loads(rec.data)
                except Exception:
                    data = {"raw": rec.data}

            # FIXED: Use the model's own send_notification method instead of helper
            result = self.send_notification(
                title=rec.name,
                message=rec.message,  # Send full message
                notification_type=rec.notification_type,
                recipient_ids=recipient_ids,
                segments=segments,
                data=data,
                url=rec.url,
                large_icon=rec.large_icon,
                big_picture=rec.big_picture
            )

            if result:
                rec.write({'status': 'sent'})
            else:
                rec.write({'status': 'failed'})
        return True

    @api.model
    def get_recipient_ids_for_users(self, user_ids):
        """Get all active player IDs for specific users"""
        if not user_ids:
            return []

        device_model = self.env['res.users.device']
        active_devices = device_model.search([
            ('user_id', 'in', user_ids),
            ('active', '=', True),
            ('push_enabled', '=', True)
        ])

        player_ids = active_devices.mapped('player_id')
        _logger.info(f"Found {len(player_ids)} active devices for users {user_ids}: {player_ids}")
        return player_ids
