from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class OneSignalController(http.Controller):

    @http.route('/onesignal/register', type='json', auth='user', methods=['POST'], csrf=False)
    def register_device(self, player_id, device_name=None, device_type='web',
                        platform=None, app_version=None, os_version=None, **kwargs):
        """Register device with enhanced parameters"""
        try:
            _logger.info(f"Registering device: {player_id[:8]}... for user {request.env.user.login}")

            device_id = request.env['res.users.device'].sudo().register_device(
                player_id=player_id,
                device_name=device_name,
                device_type=device_type,
                platform=platform,
                app_version=app_version,
                os_version=os_version
            )

            return {
                "status": "success",
                "message": "Device registered successfully",
                "device_id": device_id
            }
        except Exception as e:
            _logger.error(f"Error registering device: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    @http.route('/onesignal/unregister', type='json', auth='user', methods=['POST'], csrf=False)
    def unregister_device(self, player_id, **kwargs):
        """Unregister device"""
        try:
            _logger.info(f"Unregistering device: {player_id[:8]}...")

            success = request.env['res.users.device'].sudo().unregister_device(player_id)

            return {
                "status": "success" if success else "warning",
                "message": "Device unregistered" if success else "Device not found"
            }
        except Exception as e:
            _logger.error(f"Error unregistering device: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    @http.route('/onesignal/update_last_seen', type='json', auth='user', methods=['POST'], csrf=False)
    def update_last_seen(self, player_id, **kwargs):
        """Update device last seen timestamp"""
        try:
            success = request.env['res.users.device'].sudo().update_last_seen(player_id)
            return {
                "status": "success" if success else "warning",
                "message": "Last seen updated" if success else "Device not found"
            }
        except Exception as e:
            _logger.error(f"Error updating last seen: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    @http.route('/onesignal/test_notification', type='json', auth='user', methods=['POST'], csrf=False)
    def test_notification(self, **kwargs):
        """Send a test notification to current user"""
        try:
            user = request.env.user
            result = user.sudo().send_notification_to_user(
                title="Test Notification",
                message="This is a test notification from Odoo!",
                notification_type='custom',
                data={'test': True}
            )

            return {
                "status": "success" if result else "warning",
                "message": "Test notification sent" if result else "No active devices found"
            }
        except Exception as e:
            _logger.error(f"Error sending test notification: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    @http.route('/onesignal/user_devices', type='json', auth='user', methods=['GET'], csrf=False)
    def get_user_devices(self, **kwargs):
        """Get current user's devices"""
        try:
            devices = request.env['res.users.device'].sudo().get_user_devices()
            device_data = []

            for device in devices:
                device_data.append({
                    'id': device.id,
                    'player_id': device.player_id,
                    'device_name': device.device_name,
                    'device_type': device.device_type,
                    'active': device.active,
                    'push_enabled': device.push_enabled,
                    'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                    'is_online': device.is_online
                })

            return {
                "status": "success",
                "devices": device_data
            }
        except Exception as e:
            _logger.error(f"Error getting user devices: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }