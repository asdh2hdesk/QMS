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

                # Send notification for emails - FIXED CONDITION
                elif (config.send_email_notifications and
                      message.message_type in ['email', 'email_outgoing']):  # Added email_outgoing
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

            # Additional data for the notification - IMPROVED
            data = {
                'type': 'chat',  # Keep as 'chat'
                'message_id': message.id,
                'author_id': message.author_id.id if message.author_id else None,
                'model': message.model,
                'res_id': message.res_id,
                'channel_id': message.res_id if message.model == 'mail.channel' else None,
                'partner_id': message.author_id.id if message.author_id else None,
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
                    _logger.info(
                        f"[DEBUG] Partner {partner.id} ({partner.name}) → User {user.id} → Devices {devices.ids} → Player IDs {devices.mapped('player_id')}")
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
        """Send OneSignal notification for email messages - COMPLETELY REWRITTEN"""
        try:
            author_name = message.author_id.name if message.author_id else 'Unknown Sender'
            subject = message.subject or 'New Email'

            title = f"New email from {author_name}"
            content = f"Subject: {subject}"

            # FIXED: Use 'mail' type instead of 'email'
            data = {
                'type': 'mail',  # Changed from 'email' to 'mail'
                'message_id': message.id,
                'author_id': message.author_id.id if message.author_id else None,
                'model': message.model,
                'res_id': message.res_id,
                'record_name': self._get_record_name(message),
                'document_name': self._get_record_name(message),
            }

            # IMPROVED: Better recipient detection for emails
            recipient_ids = []
            partners = self.env['res.partner']

            # Method 1: Direct partner_ids
            if message.partner_ids:
                partners |= message.partner_ids
                _logger.info(f"[DEBUG][EMAIL] Found direct partners: {message.partner_ids.ids}")

            # Method 2: Extract from email_to if available
            if hasattr(message, 'email_to') and message.email_to:
                email_addresses = message.email_to.split(',')
                for email in email_addresses:
                    email = email.strip()
                    partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
                    if partner:
                        partners |= partner
                        _logger.info(f"[DEBUG][EMAIL] Found partner by email {email}: {partner.id}")

            # Method 3: If it's related to a record, get followers/partners
            if message.model and message.res_id:
                try:
                    record = self.env[message.model].browse(message.res_id)
                    if record.exists():
                        # Try to get followers first
                        if hasattr(record, 'message_follower_ids'):
                            follower_partners = record.message_follower_ids.mapped('partner_id')
                            partners |= follower_partners
                            _logger.info(f"[DEBUG][EMAIL] Found followers: {follower_partners.ids}")

                        # Try other partner fields
                        if hasattr(record, 'partner_id') and record.partner_id:
                            partners |= record.partner_id
                            _logger.info(f"[DEBUG][EMAIL] Found record partner: {record.partner_id.id}")

                        if hasattr(record, 'partner_ids'):
                            partners |= record.partner_ids
                            _logger.info(f"[DEBUG][EMAIL] Found record partners: {record.partner_ids.ids}")

                except Exception as e:
                    _logger.warning(f"[DEBUG][EMAIL] Could not fetch record partners: {e}")

            # Method 4: If still no partners, try to find by email domain or other methods
            if not partners and message.email_from:
                partner = self.env['res.partner'].search([('email', '=', message.email_from)], limit=1)
                if partner:
                    # Find users associated with this partner's company or similar
                    company_partners = self.env['res.partner'].search([
                        ('parent_id', '=', partner.parent_id.id if partner.parent_id else partner.id)
                    ])
                    partners |= company_partners

            # Exclude the message author from notifications
            if message.author_id:
                partners = partners.filtered(lambda p: p.id != message.author_id.id)

            _logger.info(f"[DEBUG][EMAIL] Final recipient partners for message {message.id}: {partners.ids}")

            # Get active devices for all recipient partners
            for partner in partners:
                for user in partner.user_ids:
                    devices = self.env['res.users.device'].search([
                        ('user_id', '=', user.id),
                        ('active', '=', True),
                        ('push_enabled', '=', True)
                    ])
                    _logger.info(
                        f"[DEBUG][EMAIL] Partner {partner.id} ({partner.name}) → User {user.id} → Devices {devices.ids} → Player IDs {devices.mapped('player_id')}")
                    recipient_ids.extend(devices.mapped('player_id'))

            # Remove duplicates
            recipient_ids = list(set(recipient_ids))

            _logger.info(f"Sending email notification to {len(recipient_ids)} devices")

            if recipient_ids:
                result = self.env['onesignal.notification'].send_notification(
                    title=title,
                    message=content,
                    notification_type='mail',  # Changed from 'email' to 'mail'
                    recipient_ids=recipient_ids,
                    data=data
                )
                if result:
                    _logger.info(f"Email notification sent successfully: {result.onesignal_id}")
                else:
                    _logger.warning("Email notification failed to send")
            else:
                _logger.warning(f"No active devices found for email message {message.id}")

        except Exception as e:
            _logger.error(f"Error sending email notification: {str(e)}")

    def _get_record_name(self, message):
        """Helper method to get the name of the related record"""
        try:
            if message.model and message.res_id:
                record = self.env[message.model].browse(message.res_id)
                if record.exists():
                    if hasattr(record, 'name'):
                        return record.name
                    elif hasattr(record, 'display_name'):
                        return record.display_name
                    else:
                        return f"{message.model} #{message.res_id}"
        except Exception as e:
            _logger.warning(f"Could not get record name: {e}")
        return None


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

    @api.model
    def test_email_notification(self):
        """Test method to send a sample email notification"""
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
                    'message_id': 'test',
                    'model': 'test.model',
                    'res_id': 1
                }

                result = self.env['onesignal.notification'].send_notification(
                    title="Test Email Notification",
                    message="This is a test email notification",
                    notification_type='mail',
                    recipient_ids=devices.mapped('player_id'),
                    data=data
                )

                return {'status': 'success', 'message': f'Test sent to {len(devices)} devices'}
            else:
                return {'status': 'error', 'message': 'No active devices found'}

        except Exception as e:
            _logger.error(f"Error in test email notification: {str(e)}")
            return {'status': 'error', 'message': str(e)}