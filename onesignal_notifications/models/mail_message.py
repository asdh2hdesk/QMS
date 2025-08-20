from odoo import models, api
import logging
from odoo.tools import html2plaintext
import re

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to send OneSignal notifications for new messages"""
        for vals in vals_list:
            _logger.info(f"[EMAIL_DEBUG] Creating message: type={vals.get('message_type')}, "
                         f"model={vals.get('model')}, email_from={vals.get('email_from')}, "
                         f"subject={vals.get('subject')}")
        messages = super().create(vals_list)

        try:
            config = self.env['onesignal.config'].get_active_config()
            if not config:
                _logger.warning("No active OneSignal config found")
                return messages

            for message in messages:
                _logger.info(
                    f"[DEBUG] Processing message {message.id}: type={message.message_type}, model={message.model}, author={message.author_id.name if message.author_id else 'None'}")

                # Send notification for chat messages
                if (config.send_chat_notifications and
                        message.message_type == 'comment' and
                        not message.is_internal):
                    self._send_chat_notification(message)

                # IMPROVED: Better mail detection
                elif config.send_email_notifications and self._is_email_message(message):
                    self._send_email_notification(message)

        except Exception as e:
            _logger.error(f"Error sending OneSignal notification: {str(e)}")

        return messages

    def _is_email_message(self, message):
        """Improved mail message detection"""
        # Check message type
        if message.message_type in ['mail', 'email_outgoing']:
            return True

        # Check if it has mail-specific fields
        if hasattr(message, 'email_from') and message.email_from:
            return True

        # Check if it's a notification (often mail-related)
        if message.message_type == 'notification':
            return True

        # Check if it has mail headers
        if hasattr(message, 'reply_to') and message.reply_to:
            return True

        return False

    def _send_chat_notification(self, message):
        try:
            author_name = message.author_id.name if message.author_id else 'User'
            subject = message.subject or 'New Message'
            body = message.body or ''

            clean_body = html2plaintext(body)[:100] if body else ''

            title = f"New message from {'ASD' if author_name == 'OdooBot' else author_name}"
            content = f"{subject}: {clean_body}" if clean_body else subject

            data = {
                'type': 'chat',
                'message_id': message.id,
                'author_id': message.author_id.id if message.author_id else None,
                'model': message.model,
                'res_id': message.res_id,
                'channel_id': message.res_id if message.model == 'mail.channel' else None,
                'partner_id': message.author_id.id if message.author_id else None,
            }

            recipient_ids = []
            partners = message.partner_ids

            # For discuss/mail channels
            if message.model == 'mail.channel' and message.res_id:
                try:
                    channel = self.env['mail.channel'].browse(message.res_id)
                    if channel.exists():
                        partners |= channel.channel_partner_ids
                        data['channel_name'] = channel.name
                        _logger.info(f"[DEBUG] Channel {channel.id} members: {channel.channel_partner_ids.ids}")
                except Exception as e:
                    _logger.warning(f"[DEBUG] Could not fetch channel partners: {e}")

            # For other models, also try followers
            elif not partners and message.model:
                try:
                    record = self.env[message.model].browse(message.res_id)
                    if hasattr(record, 'message_partner_ids'):
                        partners = record.message_partner_ids
                    elif hasattr(record, 'partner_ids'):
                        partners = record.partner_ids
                except Exception as e:
                    _logger.warning(f"[DEBUG] Could not fetch partners from model {message.model}: {e}")

            # Exclude the message author from notifications
            if message.author_id:
                partners = partners.filtered(lambda p: p.id != message.author_id.id)

            _logger.info(f"[DEBUG] Final recipient partners for message {message.id}: {partners.ids}")

            # Get active devices for all recipient partners
            for partner in partners:
                for user in partner.user_ids:
                    devices = self.env['res.users.device'].search([
                        ('user_id', '=', user.id),
                        ('active', '=', True),
                        ('push_enabled', '=', True)
                    ])
                    recipient_ids.extend(devices.mapped('player_id'))

            recipient_ids = list(set(recipient_ids))

            _logger.info(f"Sending chat notification to {len(recipient_ids)} devices")

            if recipient_ids:
                result = self.env['onesignal.notification'].send_notification(
                    title=title,
                    message=content,
                    notification_type='chat',
                    recipient_ids=recipient_ids,
                    data=data
                )
                if result:
                    _logger.info(f"Chat notification sent successfully: {result.onesignal_id}")
                else:
                    _logger.warning("Chat notification failed to send")
            else:
                _logger.warning(f"No active devices found for message {message.id}")

        except Exception as e:
            _logger.error(f"Error sending chat notification: {str(e)}")

    def _send_email_notification(self, message):
        try:
            author_name = message.author_id.name if message.author_id else 'User'
            subject = message.subject or 'New Email'
            body = message.body or ''

            clean_body = html2plaintext(body)[:100] if body else ''
            title = f"New email from {'ASD' if author_name == 'OdooBot' else author_name}"
            content = f"{subject}: {clean_body}" if clean_body else subject

            data = {
                'type': 'mail',
                'message_id': message.id,
                'model': message.model,
                'res_id': message.res_id,
                'author_id': message.author_id.id if message.author_id else None,
            }

            recipient_ids = []
            partners = message.partner_ids

            # For other models, also try followers
            if not partners and message.model:
                try:
                    record = self.env[message.model].browse(message.res_id)
                    if hasattr(record, 'message_partner_ids'):
                        partners = record.message_partner_ids
                    elif hasattr(record, 'partner_ids'):
                        partners = record.partner_ids
                    _logger.info(f"[DEBUG][EMAIL] Method 2 - Processing record {record.display_name if record.exists() else 'N/A'}")
                except Exception as e:
                    _logger.warning(f"[DEBUG][EMAIL] Could not fetch partners from model {message.model}: {e}")

            # Exclude the message author from notifications
            if message.author_id:
                partners = partners.filtered(lambda p: p.id != message.author_id.id)

            _logger.info(f"[DEBUG][EMAIL] Message details - Model: {message.model}, Res_ID: {message.res_id}, Partner_IDs: {partners.ids}, Email_From: {message.email_from}")

            # FIXED: Correctly find users associated with the partners
            if partners:
                user_ids = self.env['res.users'].search([('partner_id', 'in', partners.ids), ('active', '=', True)]).ids
            else:
                user_ids = []

            _logger.info(f"[DEBUG][EMAIL] Found users for partners {partners.ids}: {user_ids}")

            # Get active devices for these users
            if user_ids:
                devices = self.env['res.users.device'].search([
                    ('user_id', 'in', user_ids),
                    ('active', '=', True),
                    ('push_enabled', '=', True)
                ])
                recipient_ids = devices.mapped('player_id')
            else:
                recipient_ids = []

            recipient_ids = list(set(recipient_ids))  # Deduplicate
            total_devices = len(recipient_ids)
            _logger.info(f"[DEBUG][EMAIL] Found {total_devices} unique devices from {len(devices)} total devices")

            if total_devices > 0:
                record_name = self._get_record_name(message)
                if record_name:
                    data['record_name'] = record_name
                    content = f"{record_name}: {clean_body}" if clean_body else record_name

                self.env['onesignal.notification'].send_notification(
                    title=title,
                    message=content,
                    notification_type='mail',
                    recipient_ids=recipient_ids,
                    data=data
                )
                _logger.info(f"[DEBUG][EMAIL] Sending mail notification to {total_devices} unique devices from {len(devices)} total devices")
            else:
                _logger.warning(f"[WARNING][EMAIL] No active devices found for mail message {message.id}")

        except Exception as e:
            _logger.error(f"[ERROR][EMAIL] Error sending mail notification: {str(e)}", exc_info=True)

        return False

    def _get_record_name(self, message):
        """Helper method to get the name of the related record"""
        try:
            if not getattr(message, 'model', None) or not getattr(message, 'res_id', None):
                return None
            record = self.env[message.model].browse(message.res_id)
            if record.exists():
                return getattr(record, 'display_name', getattr(record, 'name', f"{message.model} #{message.res_id}"))
        except Exception as e:
            _logger.warning(f"Could not get record name for message {getattr(message, 'id', 'N/A')}: {e}")
        return None

# ENHANCED Helper class for testing and custom notifications
class OneSignalHelper(models.TransientModel):
    _name = 'onesignal.helper'
    _description = 'OneSignal Helper Methods'

    @api.model
    def send_alert(self, title, message, data=None):
        """Send alert notification"""
        return self.env['onesignal.notification'].send_notification(
            title=title,
            message=message,
            notification_type='alert',
            data=data
        )

    @api.model
    def send_custom_notification(self, title, message, recipient_ids=None,
                                 segments=None, data=None, url=None):
        """Send custom notification"""
        return self.env['onesignal.notification'].send_notification(
            title=title,
            message=message,
            notification_type='mail',
            recipient_ids=recipient_ids,
            segments=segments,
            data=data,
            url=url
        )

    @api.model
    def test_email_notification(self):
        """Enhanced test method to simulate mail notification"""
        try:
            current_user = self.env.user
            devices = self.env['res.users.device'].search([
                ('user_id', '=', current_user.id),
                ('active', '=', True),
                ('push_enabled', '=', True)
            ])

            if devices:
                data = {
                    'type': 'mail',
                    'message_id': 'test_email',
                    'model': 'test.model',
                    'res_id': 1,
                    'author_id': current_user.id,
                }

                result = self.env['onesignal.notification'].send_notification(
                    title="Test Email Notification",
                    message="This is a test mail notification from OneSignal Helper",
                    notification_type='mail',
                    recipient_ids=devices.mapped('player_id'),
                    data=data
                )

                if result:
                    return {
                        'status': 'success',
                        'message': f'Test mail sent to {len(devices)} devices',
                        'onesignal_id': result.onesignal_id if hasattr(result, 'onesignal_id') else 'N/A'
                    }
                else:
                    return {'status': 'error', 'message': 'Failed to send test notification'}
            else:
                return {'status': 'error', 'message': 'No active devices found for current user'}

        except Exception as e:
            _logger.error(f"Error in test mail notification: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @api.model
    def debug_message_info(self, message_id):
        """Debug method to analyze a message"""
        try:
            message = self.env['mail.message'].browse(message_id)
            if not message.exists():
                return {'error': 'Message not found'}

            info = {
                'id': message.id,
                'message_type': message.message_type,
                'model': message.model,
                'res_id': message.res_id,
                'author_id': message.author_id.id if message.author_id else None,
                'author_name': message.author_id.name if message.author_id else None,
                'partner_ids': message.partner_ids.ids,
                'subject': message.subject,
                'email_from': getattr(message, 'email_from', 'N/A'),
                'email_to': getattr(message, 'email_to', 'N/A'),
                'is_email': self.env['mail.message']._is_email_message(message),
            }

            # Get related record info
            if message.model and message.res_id:
                try:
                    record = self.env[message.model].browse(message.res_id)
                    if record.exists():
                        info['record_name'] = getattr(record, 'name', getattr(record, 'display_name', 'N/A'))

                        # Get followers if available
                        if hasattr(record, 'message_follower_ids'):
                            info['followers'] = record.message_follower_ids.mapped('partner_id').ids
                except:
                    info['record_error'] = 'Could not fetch record'

            return info

        except Exception as e:
            return {'error': str(e)}