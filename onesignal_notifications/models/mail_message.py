from odoo import models, api, fields
import json
import logging
import requests
_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _get_target_users_for_message(self, message):
        """Determine which users should receive the notification - FIXED VERSION"""
        target_users = self.env['res.users']

        try:
            _logger.info(f"Processing message: ID={message.id}, model={message.model}, res_id={message.res_id}")
            _logger.info(f"Message author: {message.author_id.name if message.author_id else 'None'}")
            _logger.info(f"Partner IDs: {[p.name for p in message.partner_ids]}")

            # Method 1: Check partner_ids (direct recipients)
            if message.partner_ids:
                for partner in message.partner_ids:
                    # FIXED: Search for user with proper domain
                    user = self.env['res.users'].search([
                        ('partner_id', '=', partner.id),
                        ('active', '=', True),
                        ('onesignal_player_id', '!=', False)
                    ], limit=1)
                    if user:
                        target_users |= user
                        _logger.info(
                            f"Found user from partner: {user.login} (Player ID: {user.onesignal_player_id[:8]}...)")

            # Method 2: For mail.channel (chat messages) - IMPROVED
            if message.model == 'mail.channel' and message.res_id:
                try:
                    channel = self.env['mail.channel'].browse(message.res_id)
                    if channel.exists():
                        _logger.info(f"Processing channel: {channel.name}")

                        # FIXED: Better way to get channel members
                        if hasattr(channel, 'channel_partner_ids'):
                            # Odoo 15+ uses channel_partner_ids
                            channel_partners = channel.channel_partner_ids
                        else:
                            # Older versions might use channel_last_seen_partner_ids
                            channel_partners = getattr(channel, 'channel_last_seen_partner_ids',
                                                       self.env['res.partner'])

                        for partner in channel_partners:
                            user = self.env['res.users'].search([
                                ('partner_id', '=', partner.id),
                                ('active', '=', True),
                                ('onesignal_player_id', '!=', False)
                            ], limit=1)
                            if user:
                                target_users |= user
                                _logger.info(f"Found channel member: {user.login}")

                except Exception as e:
                    _logger.warning(f"Could not get channel members: {str(e)}")

            # Method 3: For other models, try to get followers
            if message.model and message.res_id and message.model != 'mail.channel':
                try:
                    # Get the record and its followers
                    if message.model in self.env:
                        record = self.env[message.model].browse(message.res_id)
                        if record.exists() and hasattr(record, 'message_partner_ids'):
                            for partner in record.message_partner_ids:
                                user = self.env['res.users'].search([
                                    ('partner_id', '=', partner.id),
                                    ('active', '=', True),
                                    ('onesignal_player_id', '!=', False)
                                ], limit=1)
                                if user:
                                    target_users |= user
                                    _logger.info(f"Found follower: {user.login}")
                except Exception as e:
                    _logger.warning(f"Could not get followers for {message.model}: {str(e)}")

            # IMPORTANT: Remove the message author from receiving notification
            if message.author_id:
                author_user = self.env['res.users'].search([
                    ('partner_id', '=', message.author_id.id)
                ], limit=1)
                if author_user and author_user in target_users:
                    target_users -= author_user
                    _logger.info(f"Excluded author {author_user.login} from notifications")

            # Final filtering - ENSURE we only get users with Player IDs
            target_users = target_users.filtered(lambda u: u.active and u.onesignal_player_id)

            _logger.info(
                f"Final target users: {[(u.login, u.onesignal_player_id[:8] + '...' if u.onesignal_player_id else 'No ID') for u in target_users]}")
            return target_users

        except Exception as e:
            _logger.error(f"Error determining target users: {str(e)}")
            return self.env['res.users']


# ISSUE 2: Fix the OneSignal API call in onesignal_notification.py
# The authorization header format was incorrect

class OneSignalNotification(models.Model):
    _inherit = 'onesignal.notification'

    @api.model
    def send_notification(self, title, message, notification_type='custom',
                          recipient_ids=None, segments=None, send_to_all=False,
                          data=None, url=None, large_icon=None, big_picture=None):
        """Send notification via OneSignal API - FIXED VERSION"""

        notification = None
        try:
            config = self.env['onesignal.config'].get_active_config()

            # Validate that we have player IDs
            if recipient_ids:
                _logger.info(f"Sending to specific player IDs: {recipient_ids}")
            elif not send_to_all and not segments:
                _logger.warning("No recipients specified and not sending to all")
                return False

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
                _logger.error("No recipients specified")
                return False

            # Add additional data
            if data:
                payload['data'] = data
            if url:
                payload['url'] = url
            if large_icon:
                payload['large_icon'] = large_icon
            if big_picture:
                payload['big_picture'] = big_picture

            # FIXED: Correct authorization header format
            headers = {
                'Authorization': f'Basic {config.rest_api_key}',  # This is correct
                'Content-Type': 'application/json'
            }

            _logger.info(f"OneSignal payload: {json.dumps(payload, indent=2)}")

            response = requests.post(
                'https://onesignal.com/api/v1/notifications',
                headers=headers,
                json=payload,
                timeout=30
            )

            _logger.info(f"OneSignal response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                result = response.json()
                notification.write({
                    'status': 'sent',
                    'onesignal_id': result.get('id')
                })
                _logger.info(f"OneSignal notification sent successfully: {result.get('id')}")
                _logger.info(f"Recipients: {result.get('recipients', 0)}")
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


# ISSUE 3: Add debugging method to test notifications

class OneSignalHelper(models.TransientModel):
    _name = 'onesignal.helper'

    @api.model
    def debug_user_notifications(self, user_id=None):
        """Debug method to check notification setup for a user"""
        if not user_id:
            user_id = self.env.user.id

        user = self.env['res.users'].browse(user_id)

        debug_info = {
            'user_login': user.login,
            'user_name': user.name,
            'user_active': user.active,
            'has_player_id': bool(user.onesignal_player_id),
            'player_id': user.onesignal_player_id[:8] + '...' if user.onesignal_player_id else None,
            'device_info': user.onesignal_device_info,
            'last_updated': str(user.onesignal_last_updated) if user.onesignal_last_updated else None,
        }

        _logger.info(f"User Debug Info: {json.dumps(debug_info, indent=2)}")
        return debug_info

    @api.model
    def test_notification_to_current_user(self):
        """Send a test notification to the current user"""
        user = self.env.user

        if not user.onesignal_player_id:
            _logger.error(f"Current user {user.login} has no OneSignal Player ID")
            return False

        _logger.info(f"Sending test notification to {user.login} (Player ID: {user.onesignal_player_id})")

        return user.send_notification_to_user(
            title="Test Notification",
            message=f"This is a test notification sent to {user.name}",
            notification_type='custom',
            data={
                'type': 'test',
                'timestamp': fields.Datetime.now().isoformat(),
                'user_id': user.id
            }
        )


# ISSUE 4: Improve the Flutter app player ID sending

# Add this method to res_users.py to better handle player ID updates
class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def comprehensive_debug(self):
        """Comprehensive debugging for OneSignal notifications"""

        debug_results = {
            'timestamp': fields.Datetime.now().isoformat(),
            'current_user': {},
            'onesignal_config': {},
            'all_users_with_player_ids': [],
            'recent_notifications': [],
            'test_notification_result': None
        }

        try:
            # 1. Check current user
            user = self.env.user
            debug_results['current_user'] = {
                'id': user.id,
                'login': user.login,
                'name': user.name,
                'active': user.active,
                'has_player_id': bool(user.onesignal_player_id),
                'player_id': user.onesignal_player_id,
                'player_id_length': len(user.onesignal_player_id) if user.onesignal_player_id else 0,
                'device_info': user.onesignal_device_info,
                'last_updated': str(user.onesignal_last_updated) if user.onesignal_last_updated else None,
            }

            # 2. Check OneSignal configuration
            try:
                config = self.env['onesignal.config'].get_active_config()
                debug_results['onesignal_config'] = {
                    'exists': True,
                    'name': config.name,
                    'app_id': config.app_id[:8] + '...' if config.app_id else None,
                    'has_rest_api_key': bool(config.rest_api_key),
                    'rest_api_key_length': len(config.rest_api_key) if config.rest_api_key else 0,
                    'send_chat_notifications': config.send_chat_notifications,
                    'send_email_notifications': config.send_email_notifications,
                    'send_alert_notifications': config.send_alert_notifications,
                }
            except Exception as e:
                debug_results['onesignal_config'] = {
                    'exists': False,
                    'error': str(e)
                }

            # 3. Check all users with player IDs
            users_with_player_ids = self.env['res.users'].search([
                ('onesignal_player_id', '!=', False),
                ('active', '=', True)
            ])

            for u in users_with_player_ids:
                debug_results['all_users_with_player_ids'].append({
                    'id': u.id,
                    'login': u.login,
                    'name': u.name,
                    'player_id': u.onesignal_player_id[:8] + '...' if u.onesignal_player_id else 'None',
                    'last_updated': str(u.onesignal_last_updated) if u.onesignal_last_updated else None,
                })

            # 4. Check recent notifications
            recent_notifications = self.env['onesignal.notification'].search([
                ('create_date', '>=', fields.Datetime.now() - timedelta(hours=24))
            ], limit=10, order='create_date desc')

            for notif in recent_notifications:
                debug_results['recent_notifications'].append({
                    'id': notif.id,
                    'name': notif.name,
                    'status': notif.status,
                    'notification_type': notif.notification_type,
                    'create_date': str(notif.create_date),
                    'onesignal_id': notif.onesignal_id,
                    'error_message': notif.error_message,
                    'recipient_count': len(json.loads(notif.recipient_ids)) if notif.recipient_ids else 0,
                })

            # 5. Test notification if user has player ID
            if user.onesignal_player_id:
                try:
                    test_notification = user.send_notification_to_user(
                        title="Debug Test Notification",
                        message=f"Test sent at {fields.Datetime.now()}",
                        notification_type='custom',
                        data={'type': 'debug_test', 'user_id': user.id}
                    )
                    debug_results['test_notification_result'] = {
                        'sent': bool(test_notification),
                        'notification_id': test_notification.id if test_notification else None,
                        'status': test_notification.status if test_notification else None,
                    }
                except Exception as e:
                    debug_results['test_notification_result'] = {
                        'sent': False,
                        'error': str(e)
                    }
            else:
                debug_results['test_notification_result'] = {
                    'sent': False,
                    'error': 'Current user has no player ID'
                }

        except Exception as e:
            debug_results['error'] = str(e)

        # Log the full debug results
        _logger.info(f"OneSignal Debug Results: {json.dumps(debug_results, indent=2)}")

        return debug_results

    # Call this from Odoo's python console:
    # self.env['onesignal.helper'].comprehensive_debug()

    # ADDITIONAL DEBUGGING: Add this to check message processing
    @api.model
    def debug_message_notification(self, message_id):
        """Debug a specific message's notification processing"""

        message = self.env['mail.message'].browse(message_id)
        if not message.exists():
            return {'error': 'Message not found'}

        debug_info = {
            'message_id': message_id,
            'message_subject': message.subject,
            'message_body': message.body[:100] if message.body else None,
            'message_type': message.message_type,
            'model': message.model,
            'res_id': message.res_id,
            'author': message.author_id.name if message.author_id else None,
            'partner_ids': [p.name for p in message.partner_ids],
            'target_users': [],
            'notification_sent': False,
        }

        # Get target users using the same logic as mail_message.py
        try:
            target_users = message._get_target_users_for_message(message)
            debug_info['target_users'] = [
                {
                    'login': u.login,
                    'name': u.name,
                    'has_player_id': bool(u.onesignal_player_id),
                    'player_id': u.onesignal_player_id[:8] + '...' if u.onesignal_player_id else None,
                }
                for u in target_users
            ]

            # Try to send notification to these users
            if target_users:
                for user in target_users:
                    if user.onesignal_player_id:
                        try:
                            result = user.send_chat_notification(
                                sender_name=message.author_id.name or 'User',
                                message=message.body[:100] if message.body else 'No content',
                                channel_id=str(message.res_id) if message.res_id else 'general'
                            )
                            debug_info['notification_sent'] = bool(result)
                        except Exception as e:
                            debug_info['notification_error'] = str(e)

        except Exception as e:
            debug_info['error'] = str(e)

        _logger.info(f"Message Debug Info: {json.dumps(debug_info, indent=2)}")
        return debug_info

    @api.model
    def update_onesignal_player_id(self, player_id, device_info=None):
        """Update OneSignal Player ID for current user - IMPROVED VERSION"""
        if not player_id:
            _logger.warning("Empty player_id provided")
            return False

        current_user = self.env.user

        # Validate player ID format (OneSignal player IDs are UUIDs)
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, player_id, re.IGNORECASE):
            _logger.warning(f"Invalid player_id format: {player_id}")
            return False

        # Check if player ID is already assigned to another user
        existing_user = self.search([
            ('onesignal_player_id', '=', player_id),
            ('id', '!=', current_user.id)
        ], limit=1)

        if existing_user:
            _logger.warning(f"Player ID {player_id} is already assigned to user {existing_user.login}")
            # Optionally, you might want to clear it from the other user
            # existing_user.write({'onesignal_player_id': False})

        current_user.write({
            'onesignal_player_id': player_id,
            'onesignal_device_info': device_info or '{}',
            'onesignal_last_updated': fields.Datetime.now()
        })

        _logger.info(f"Successfully updated OneSignal Player ID for user {current_user.login}: {player_id}")

        # Send a test notification to verify it works
        try:
            test_result = current_user.send_notification_to_user(
                title="OneSignal Connected",
                message=f"Push notifications are now enabled for {current_user.name}",
                notification_type='custom',
                data={'type': 'welcome', 'user_id': current_user.id}
            )
            _logger.info(f"Welcome notification sent: {bool(test_result)}")
        except Exception as e:
            _logger.error(f"Failed to send welcome notification: {str(e)}")

        return True