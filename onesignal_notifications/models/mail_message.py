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

                # IMPROVED: Better mail detection with more logging
                elif config.send_email_notifications:
                    is_email = self._is_email_message(message)
                    _logger.info(f"[DEBUG] Message {message.id} is_email: {is_email}")
                    if is_email:
                        self._send_email_notification(message)

        except Exception as e:
            _logger.error(f"Error sending OneSignal notification: {str(e)}")

        return messages

    def _is_email_message(self, message):
        """Improved mail message detection with detailed logging"""
        reasons = []

        # Check message type
        if message.message_type in ['mail', 'email_outgoing', 'email']:
            reasons.append(f"message_type={message.message_type}")

        # Check if it has mail-specific fields
        if hasattr(message, 'email_from') and message.email_from:
            reasons.append(f"has email_from={message.email_from}")

        # Check if it's a notification (often mail-related)
        if message.message_type == 'notification':
            reasons.append("is notification")

        # Check if it has mail headers
        if hasattr(message, 'reply_to') and message.reply_to:
            reasons.append(f"has reply_to={message.reply_to}")

        # Additional checks for email detection
        if hasattr(message, 'email_to') and message.email_to:
            reasons.append(f"has email_to={message.email_to}")

        # Check if message has email-related subtypes
        if message.subtype_id and message.subtype_id.name in ['Discussions', 'Note']:
            reasons.append(f"subtype={message.subtype_id.name}")

        # NEW: Check if the message is being sent to partners (likely email)
        if message.partner_ids:
            reasons.append(f"has partners={len(message.partner_ids)}")

        # NEW: Check if message has followers (email recipients)
        if message.model and message.res_id:
            try:
                record = self.env[message.model].browse(message.res_id)
                if record.exists() and hasattr(record, 'message_follower_ids'):
                    if record.message_follower_ids:
                        reasons.append(f"has followers={len(record.message_follower_ids)}")
            except:
                pass

        is_email = bool(reasons)
        _logger.info(f"[DEBUG] _is_email_message for {message.id}: {is_email}, reasons: {reasons}")

        return is_email

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
            all_partners = self.env['res.partner']

            _logger.info(f"[DEBUG][EMAIL] Processing email from {author_name} - Subject: {subject}")

            # PRIORITY 1: Get direct message recipients (the most important)
            if message.partner_ids:
                all_partners |= message.partner_ids
                _logger.info(f"[DEBUG][EMAIL] Found direct recipients: {message.partner_ids.mapped('name')}")

            # PRIORITY 2: Get recipients from notification records
            if hasattr(message, 'notification_ids') and message.notification_ids:
                notification_partners = message.notification_ids.mapped('res_partner_id')
                all_partners |= notification_partners
                _logger.info(f"[DEBUG][EMAIL] Found notification recipients: {notification_partners.mapped('name')}")

            # PRIORITY 3: If this is related to a record, get followers and related partners
            if message.model and message.res_id:
                try:
                    record = self.env[message.model].browse(message.res_id)
                    if record.exists():
                        _logger.info(f"[DEBUG][EMAIL] Processing record: {record.display_name}")

                        # Get followers (people who should be notified about this record)
                        if hasattr(record, 'message_follower_ids'):
                            follower_partners = record.message_follower_ids.mapped('partner_id')
                            all_partners |= follower_partners
                            _logger.info(
                                f"[DEBUG][EMAIL] Found {len(follower_partners)} followers: {follower_partners.mapped('name')}")

                        # Get partners directly related to the record
                        if hasattr(record, 'partner_ids') and record.partner_ids:
                            record_partners = record.partner_ids
                            all_partners |= record_partners
                            _logger.info(f"[DEBUG][EMAIL] Found record partners: {record_partners.mapped('name')}")

                        # Get assigned/responsible users (but only if no other recipients found)
                        if not all_partners:
                            responsible_partners = self._get_responsible_partners_for_record(record)
                            all_partners |= responsible_partners
                            if responsible_partners:
                                _logger.info(
                                    f"[DEBUG][EMAIL] Added responsible partners as fallback: {responsible_partners.mapped('name')}")

                except Exception as e:
                    _logger.warning(f"[DEBUG][EMAIL] Could not process record: {e}")

            # PRIORITY 4: Parse email headers to find recipients
            if not all_partners:
                email_recipients = self._parse_email_recipients(message)
                all_partners |= email_recipients
                if email_recipients:
                    _logger.info(f"[DEBUG][EMAIL] Found email header recipients: {email_recipients.mapped('name')}")

            # PRIORITY 5: Ultimate fallback - but only if we really have no recipients
            if not all_partners:
                _logger.warning(f"[DEBUG][EMAIL] No recipients found, applying fallback")
                fallback_partners = self._get_fallback_partners_for_model(message.model, message)
                all_partners |= fallback_partners
                data['fallback_notification'] = True

            # CRITICAL: Always exclude the message author from notifications
            # (The sender shouldn't get notified about their own sent email)
            if message.author_id:
                original_count = len(all_partners)
                all_partners = all_partners.filtered(lambda p: p.id != message.author_id.id)
                excluded_count = original_count - len(all_partners)
                if excluded_count > 0:
                    _logger.info(f"[DEBUG][EMAIL] Excluded message author from {original_count} recipients")

            _logger.info(
                f"[DEBUG][EMAIL] Final recipient partners: {all_partners.mapped('name')} (IDs: {all_partners.ids})")

            # Find users and devices for final recipients
            if all_partners:
                user_ids = self.env['res.users'].search([
                    ('partner_id', 'in', all_partners.ids),
                    ('active', '=', True)
                ]).ids
            else:
                user_ids = []

            _logger.info(f"[DEBUG][EMAIL] Found users for partners: {user_ids}")

            # Get active devices
            if user_ids:
                devices = self.env['res.users.device'].search([
                    ('user_id', 'in', user_ids),
                    ('active', '=', True),
                    ('push_enabled', '=', True)
                ])
                recipient_ids = devices.mapped('player_id')
            else:
                recipient_ids = []

            recipient_ids = list(set(recipient_ids))  # Remove duplicates
            total_devices = len(recipient_ids)

            _logger.info(f"[DEBUG][EMAIL] Found {total_devices} devices for {len(all_partners)} partners")

            # Send notification if we have recipients
            if total_devices > 0:
                record_name = self._get_record_name(message)
                if record_name:
                    data['record_name'] = record_name
                    content = f"{record_name}: {clean_body}" if clean_body else record_name

                result = self.env['onesignal.notification'].send_notification(
                    title=title,
                    message=content,
                    notification_type='mail',
                    recipient_ids=recipient_ids,
                    data=data
                )

                if result:
                    _logger.info(f"[DEBUG][EMAIL] Email notification sent successfully to {total_devices} devices")
                    return True
                else:
                    _logger.error(f"[DEBUG][EMAIL] Failed to send email notification")
            else:
                _logger.warning(f"[WARNING][EMAIL] No active devices found for email message {message.id}")

        except Exception as e:
            _logger.error(f"[ERROR][EMAIL] Error sending email notification: {str(e)}", exc_info=True)

        return False

    def _parse_email_recipients(self, message):
        """Parse email recipients from message headers and content"""
        recipients = self.env['res.partner']

        try:
            # Check email_to field
            if hasattr(message, 'email_to') and message.email_to:
                email_addresses = self._extract_emails_from_string(message.email_to)
                for email in email_addresses:
                    partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
                    if partner:
                        recipients |= partner
                        _logger.info(f"[DEBUG][EMAIL] Found partner for email_to {email}: {partner.name}")

            # Check email_cc field
            if hasattr(message, 'email_cc') and message.email_cc:
                email_addresses = self._extract_emails_from_string(message.email_cc)
                for email in email_addresses:
                    partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
                    if partner:
                        recipients |= partner
                        _logger.info(f"[DEBUG][EMAIL] Found partner for email_cc {email}: {partner.name}")

        except Exception as e:
            _logger.warning(f"Error parsing email recipients: {e}")

        return recipients

    def _extract_emails_from_string(self, email_string):
        """Extract email addresses from a string like 'Name <email@domain.com>, other@domain.com'"""
        import re
        if not email_string:
            return []

        # Regular expression to find email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, email_string)
        return emails

    def _get_responsible_partners_for_record(self, record):
        """Get responsible partners for a record (only as fallback)"""
        responsible_partners = self.env['res.partner']

        # Common user fields to check
        user_fields = ['user_id', 'responsible_id', 'assigned_to', 'manager_id', 'supervisor_id', 'owner_id']

        for field in user_fields:
            if hasattr(record, field):
                user = getattr(record, field, None)
                if user and hasattr(user, 'partner_id'):
                    responsible_partners |= user.partner_id
                    _logger.info(f"[DEBUG][EMAIL] Found {field}: {user.name}")

        return responsible_partners

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
    def add_follower_to_record(self, model_name, res_id, partner_id=None, user_id=None):
        """Helper method to add followers to records"""
        try:
            if not partner_id and user_id:
                partner_id = self.env['res.users'].browse(user_id).partner_id.id
            elif not partner_id:
                partner_id = self.env.user.partner_id.id

            record = self.env[model_name].browse(res_id)
            if record.exists() and hasattr(record, 'message_subscribe'):
                record.message_subscribe([partner_id])
                return {'status': 'success', 'message': f'Added follower to {record.display_name}'}
            else:
                return {'status': 'error', 'message': 'Record not found or does not support followers'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @api.model
    def setup_default_followers_for_model(self, model_name, user_ids=None):
        """Setup default followers for all records of a specific model"""
        try:
            if not user_ids:
                # Default to admin users
                user_ids = self.env['res.users'].search([('groups_id', 'in', self.env.ref('base.group_system').id)]).ids

            partner_ids = self.env['res.users'].browse(user_ids).mapped('partner_id').ids

            records = self.env[model_name].search([])
            count = 0
            for record in records:
                if hasattr(record, 'message_subscribe'):
                    record.message_subscribe(partner_ids)
                    count += 1

            return {
                'status': 'success',
                'message': f'Added {len(partner_ids)} followers to {count} records of {model_name}'
            }
        except Exception as e:
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
                'subtype_id': message.subtype_id.name if message.subtype_id else None,
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

                        # Get notification recipients
                        if hasattr(message, 'notification_ids'):
                            info['notifications'] = message.notification_ids.mapped('res_partner_id').ids
                except Exception as e:
                    info['record_error'] = str(e)

            return info

        except Exception as e:
            return {'error': str(e)}