from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)


class OneSignalController(http.Controller):

    @http.route('/onesignal/register', type='json', auth='user', methods=['POST'], csrf=False)
    def register_device(self, **kwargs):
        """Register device with OneSignal Player ID"""
        try:
            # FIXED: For JSON-RPC routes, parameters come directly as kwargs, not from request.get_json_data()
            player_id = kwargs.get('player_id')
            device_name = kwargs.get('device_name', 'Unknown Device')
            device_type = kwargs.get('device_type', 'other')
            platform = kwargs.get('platform')
            app_version = kwargs.get('app_version')
            os_version = kwargs.get('os_version')

            _logger.info(f"[DEBUG] Received parameters: player_id={player_id}, device_name={device_name}, device_type={device_type}")

            if not player_id:
                return {
                    "status": "error",
                    "message": "Player ID is required"
                }

            _logger.info(f"Registering device: {player_id[:8]}... for user {request.env.user.login}")

            # Register the device
            device_id = request.env['res.users.device'].sudo().register_device(
                player_id=player_id,
                device_name=device_name,
                device_type=device_type,
                platform=platform,
                app_version=app_version,
                os_version=os_version
            )

            _logger.info(f"Device registered successfully with ID: {device_id}")

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

    @http.route('/onesignal/test_notification', type='json', auth='user', methods=['POST'], csrf=False)
    def test_notification(self, **kwargs):
        """Send a test notification to current user"""
        try:
            user = request.env.user
            _logger.info(f"Sending test notification to user: {user.login}")

            result = user.sudo().send_notification_to_user(
                title="Test Notification from Odoo",
                message="This is a test notification to verify your setup!",
                notification_type='custom',
                data={
                    'test': True,
                    'type': 'test',
                    'timestamp': str(request.env.cr.now())
                }
            )

            if result:
                _logger.info("Test notification sent successfully")
                return {
                    "status": "success",
                    "message": "Test notification sent successfully!"
                }
            else:
                _logger.warning("No active devices found for test notification")
                return {
                    "status": "warning",
                    "message": "No active devices found. Please register your device first."
                }

        except Exception as e:
            _logger.error(f"Error sending test notification: {str(e)}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }

    @http.route('/onesignal/unregister', type='json', auth='user', methods=['POST'], csrf=False)
    def unregister_device(self, **kwargs):
        """Unregister device"""
        try:
            # FIXED: Use kwargs directly for JSON-RPC routes
            player_id = kwargs.get('player_id')

            if not player_id:
                return {
                    "status": "error",
                    "message": "Player ID is required"
                }

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
    def update_last_seen(self, **kwargs):
        """Update device last seen timestamp"""
        try:
            # FIXED: Use kwargs directly for JSON-RPC routes
            player_id = kwargs.get('player_id')

            if not player_id:
                return {
                    "status": "error",
                    "message": "Player ID is required"
                }

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

    @http.route('/onesignal/user_devices', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
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
                "devices": device_data,
                "count": len(device_data)
            }
        except Exception as e:
            _logger.error(f"Error getting user devices: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    @http.route('/onesignal/test', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def test_endpoint(self, **kwargs):
        """Test endpoint to verify controller is working"""
        try:
            return {
                "status": "success",
                "message": "OneSignal controller is working perfectly!",
                "user": request.env.user.name,
                "user_id": request.env.user.id,
                "timestamp": str(request.env.cr.now()),
                "session_info": "Active"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Controller error: {str(e)}"
            }