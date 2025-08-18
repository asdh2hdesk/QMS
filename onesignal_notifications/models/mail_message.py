from odoo import models, api
import logging
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to send OneSignal notifications for new messages"""
        messages = super().create(vals_list)

        try:
            config = self.env['onesignal.config'].get_active_config()

            for message in messages:
                # Send notification for chat messages
                if (config.send_chat_notifications and
                        message.message_type == 'comment' and
                        not message.is_internal):
                    self._send_chat_notification(message)

                # Send notification for emails
                elif (config.send_email_notifications and
                      message.message_type == 'email'):
                    self._send_email_notification(message)

        except Exception as e:
            _logger.error(f"Error sending OneSignal notification: {str(e)}")

        return messages

    def _send_chat_notification(self, message):
        try:
            author_name = message.author_id.name if message.author_id else 'User'
            subject = message.subject or 'New Message'
            body = message.body or ''

            clean_body = html2plaintext(body)[:100] if body else ''

            title = f"New message from {'ASD' if author_name == 'OdooBot' else author_name}"
            content = f"{subject}: {clean_body}" if clean_body else subject

            # Additional data for the notification
            data = {
                'type': 'chat',
                'message_id': message.id,
                'author_id': message.author_id.id if message.author_id else None,
                'model': message.model,
                'res_id': message.res_id,
            }

            # Collect recipient devices - IMPROVED LOGIC
            recipient_ids = []

            # Get partners from the message
            partners = message.partner_ids

            # For discuss/mail channels
            if message.model == 'mail.channel' and message.res_id:
                try:
                    channel = self.env['mail.channel'].browse(message.res_id)
                    if channel.exists():
                        partners |= channel.channel_partner_ids
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
                    _logger.info(f"[DEBUG] Partner {partner.id} ({partner.name}) → User {user.id} → Devices {devices.ids} → Player IDs {devices.mapped('player_id')}")
                    recipient_ids.extend(devices.mapped('player_id'))

            # Remove duplicates
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
        """Send OneSignal notification for email messages"""
        try:
            author_name = message.author_id.name if message.author_id else 'Unknown Sender'
            subject = message.subject or 'New Email'

            title = f"New email from {author_name}"
            content = f"Subject: {subject}"

            data = {
                'type': 'email',
                'message_id': message.id,
                'author_id': message.author_id.id if message.author_id else None,
            }

            recipient_ids = []
            for partner in message.partner_ids:
                for user in partner.user_ids:
                    devices = self.env['res.users.device'].search([
                        ('user_id', '=', user.id),
                        ('active', '=', True),
                        ('push_enabled', '=', True)
                    ])
                    _logger.info(f"[DEBUG][EMAIL] Partner {partner.id} → User {user.id} → Devices {devices.ids} → Player IDs {devices.mapped('player_id')}")
                    recipient_ids.extend(devices.mapped('player_id'))

            if recipient_ids:
                self.env['onesignal.notification'].send_notification(
                    title=title,
                    message=content,
                    notification_type='email',
                    recipient_ids=recipient_ids,
                    data=data
                )

        except Exception as e:
            _logger.error(f"Error sending email notification: {str(e)}")


# Helper class for custom notifications
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
            notification_type='custom',
            recipient_ids=recipient_ids,
            segments=segments,
            data=data,
            url=url
        )
