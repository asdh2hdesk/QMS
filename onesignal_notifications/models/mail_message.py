from odoo import models, api
import logging

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
        """Send OneSignal notification for chat messages to specific recipients"""
        try:
            # Get message details
            author_name = message.author_id.name if message.author_id else 'User'
            subject = message.subject or 'New Message'
            body = message.body or ''

            # Clean HTML from body
            from odoo.tools import html2plaintext
            clean_body = html2plaintext(body)[:100]  # Limit to 100 chars

            if author_name == 'OdooBot':
                title = f"New message from ASD"
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

            # Determine target users based on message context
            target_users = self._get_target_users_for_message(message)

            if target_users:
                # Send notification only to specific users
                for user in target_users:
                    if user.onesignal_player_id:
                        user.send_chat_notification(
                            sender_name=author_name,
                            message=clean_body,
                            channel_id=str(message.res_id) if message.res_id else 'general'
                        )
                        _logger.info(f"Chat notification sent to user {user.login}")
            else:
                _logger.info("No target users found for chat notification")

        except Exception as e:
            _logger.error(f"Error sending chat notification: {str(e)}")

    def _get_target_users_for_message(self, message):
        """Determine which users should receive the notification"""
        target_users = self.env['res.users']

        try:
            # Method 1: Check partner_ids (direct recipients)
            if message.partner_ids:
                partner_users = message.partner_ids.mapped('user_ids').filtered('onesignal_player_id')
                target_users |= partner_users
                _logger.info(f"Found {len(partner_users)} users from partner_ids")

            # Method 2: Check followers of the record
            if message.model and message.res_id:
                try:
                    record = self.env[message.model].browse(message.res_id)
                    if hasattr(record, 'message_follower_ids'):
                        follower_partners = record.message_follower_ids.mapped('partner_id')
                        follower_users = follower_partners.mapped('user_ids').filtered('onesignal_player_id')
                        target_users |= follower_users
                        _logger.info(f"Found {len(follower_users)} follower users")
                except Exception as e:
                    _logger.warning(f"Could not get followers for {message.model}: {str(e)}")

            # Method 3: Check if it's a direct message (private channel)
            if message.model == 'mail.channel':
                try:
                    channel = self.env['mail.channel'].browse(message.res_id)
                    if channel and hasattr(channel, 'channel_member_ids'):
                        member_partners = channel.channel_member_ids.mapped('partner_id')
                        member_users = member_partners.mapped('user_ids').filtered('onesignal_player_id')
                        target_users |= member_users
                        _logger.info(f"Found {len(member_users)} channel member users")
                except Exception as e:
                    _logger.warning(f"Could not get channel members: {str(e)}")

            # Method 4: For specific models, add custom logic
            if message.model == 'project.task':
                try:
                    task = self.env['project.task'].browse(message.res_id)
                    if task:
                        # Notify assigned users
                        assigned_users = task.user_ids.filtered('onesignal_player_id')
                        target_users |= assigned_users
                        _logger.info(f"Found {len(assigned_users)} assigned task users")
                except Exception as e:
                    _logger.warning(f"Could not get task users: {str(e)}")

            # Method 5: For sale orders, notify salesperson
            elif message.model == 'sale.order':
                try:
                    sale_order = self.env['sale.order'].browse(message.res_id)
                    if sale_order and sale_order.user_id and sale_order.user_id.onesignal_player_id:
                        target_users |= sale_order.user_id
                        _logger.info(f"Added sale order user: {sale_order.user_id.login}")
                except Exception as e:
                    _logger.warning(f"Could not get sale order user: {str(e)}")

            # Exclude the author from receiving their own message notification
            if message.author_id and message.author_id.user_ids:
                author_users = message.author_id.user_ids
                target_users -= author_users
                _logger.info(f"Excluded author {message.author_id.name} from notifications")

            # Remove duplicates and filter active users
            target_users = target_users.filtered(lambda u: u.active and u.onesignal_player_id)

            _logger.info(f"Final target users for notification: {[u.login for u in target_users]}")
            return target_users

        except Exception as e:
            _logger.error(f"Error determining target users: {str(e)}")
            return self.env['res.users']

    def _send_email_notification(self, message):
        """Send OneSignal notification for email messages to specific recipients"""
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

            # Get target users for email notification
            target_users = self._get_target_users_for_message(message)

            if target_users:
                for user in target_users:
                    if user.onesignal_player_id:
                        user.send_notification_to_user(
                            title=title,
                            message=content,
                            notification_type='email',
                            data=data
                        )
                        _logger.info(f"Email notification sent to user {user.login}")
            else:
                _logger.info("No target users found for email notification")

        except Exception as e:
            _logger.error(f"Error sending email notification: {str(e)}")


# Helper class for custom notifications
class OneSignalHelper(models.TransientModel):
    _name = 'onesignal.helper'
    _description = 'OneSignal Helper Methods'

    @api.model
    def send_alert_to_user(self, user_id, title, message, data=None):
        """Send alert notification to specific user"""
        user = self.env['res.users'].browse(user_id)
        if user.exists() and user.onesignal_player_id:
            return user.send_notification_to_user(
                title=title,
                message=message,
                notification_type='alert',
                data=data
            )
        return False

    @api.model
    def send_alert_to_users(self, user_ids, title, message, data=None):
        """Send alert notification to specific users"""
        return self.env['res.users'].send_notification_to_users(
            user_ids=user_ids,
            title=title,
            message=message,
            notification_type='alert',
            data=data
        )

    @api.model
    def send_custom_notification_to_user(self, user_id, title, message, data=None, url=None):
        """Send custom notification to specific user"""
        user = self.env['res.users'].browse(user_id)
        if user.exists() and user.onesignal_player_id:
            if data is None:
                data = {}
            if url:
                data['url'] = url
            return user.send_notification_to_user(
                title=title,
                message=message,
                notification_type='custom',
                data=data
            )
        return False

    @api.model
    def send_notification_to_role(self, group_xml_id, title, message, data=None):
        """Send notification to all users with a specific role/group"""
        try:
            group = self.env.ref(group_xml_id)
            users = group.users.filtered('onesignal_player_id')

            if users:
                return self.env['res.users'].send_notification_to_users(
                    user_ids=users.ids,
                    title=title,
                    message=message,
                    notification_type='custom',
                    data=data
                )
            return False
        except Exception as e:
            _logger.error(f"Error sending notification to role {group_xml_id}: {str(e)}")
            return False