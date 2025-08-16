from odoo import models, api
import tools
import logging
import json

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
        """Send OneSignal notification for chat messages"""
        try:
            # Get message details
            author_name = message.author_id.name if message.author_id else 'User'
            subject = message.subject or 'New Message'
            body = message.body or ''

            # Clean HTML from body
            from odoo.tools import html2plaintext
            clean_body = html2plaintext(body)[:100]  # Limit to 100 chars

            if author_name == 'OdooBot':
                title = f"New message from {'ASD'}"
            else:
                title = f"New message from {author_name}"
            content = f"{subject}: {clean_body}"

            # Additional data for the notification
            data = {
                'type': 'chat',
                'message_id': message.id,
                'author_id': message.author_id.id if message.author_id else None,
                'model': message.model,
                'res_id': message.res_id,
            }

            recipient_ids = []
            for partner in message.partner_ids:
                for user in partner.user_ids:
                    if user.onesignal_player_id:
                        recipient_ids.append(user.onesignal_player_id)

            self.env['onesignal.notification'].send_notification(
                title=title,
                message=content,
                notification_type='chat',
                data=data
            )

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
                    if user.onesignal_player_id:
                        recipient_ids.append(user.onesignal_player_id)

            self.env['onesignal.notification'].send_notification(
                title=title,
                message=content,
                notification_type='email',
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