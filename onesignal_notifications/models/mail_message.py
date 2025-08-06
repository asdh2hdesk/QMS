from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)

        for message in messages:
            self._send_notification_for_message(message)

        return messages

    def _send_notification_for_message(self, message):
        """Send OneSignal notification for new messages"""
        try:
            # Skip system messages
            if message.message_type == 'notification':
                return

            # Handle different message types
            if message.message_type == 'email':
                self._handle_email_notification(message)
            elif message.message_type == 'comment':
                self._handle_chat_notification(message)

        except Exception as e:
            _logger.error(f"Error handling message notification: {e}")

    def _handle_email_notification(self, message):
        """Handle email notifications"""
        if message.partner_ids:
            for partner in message.partner_ids:
                if partner.user_ids:
                    user = partner.user_ids[0]
                    title = "New Email"
                    content = f"From: {message.author_id.name}\nSubject: {message.subject or 'No Subject'}"

                    user.send_onesignal_notification(
                        title,
                        content,
                        data={
                            'type': 'mail',
                            'message_id': message.id,
                            'model': message.model,
                            'res_id': message.res_id
                        }
                    )

    def _handle_chat_notification(self, message):
        """Handle chat notifications"""
        if message.partner_ids:
            for partner in message.partner_ids:
                if partner.user_ids and message.author_id.id != partner.id:
                    user = partner.user_ids[0]
                    title = f"New message from {message.author_id.name}"
                    content = message.body or "New message received"

                    user.send_onesignal_notification(
                        title,
                        content,
                        data={
                            'type': 'chat',
                            'message_id': message.id,
                            'author_id': message.author_id.id
                        }
                    )