from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)


class OneSignalController(http.Controller):

    @http.route('/onesignal/register', type='http', auth='user', methods=['POST'], csrf=False)
    def register_device(self, **kwargs):
        """Register device with OneSignal Player ID"""
        try:
            # For HTTP routes, get JSON data from request body
            if request.httprequest.is_json:
                data = request.get_json_data()
            else:
                # Fallback to reading raw data
                raw_data = request.httprequest.data.decode('utf-8')
                data = json.loads(raw_data) if raw_data else {}

            _logger.info(f"[DEBUG] Received data: {data}")

            player_id = data.get('player_id')
            device_name = data.get('device_name', 'Unknown Device')
            device_type = data.get('device_type', 'other')
            platform = data.get('platform')
            app_version = data.get('app_version')
            os_version = data.get('os_version')

            _logger.info(f"[DEBUG] Extracted values: player_id={player_id}, device_name={device_name}")

            if not player_id:
                return request.make_json_response({
                    "status": "error",
                    "message": "Player ID is required"
                })

            _logger.info(f"Registering device: {player_id[:8]}... for user {request.env.user.login}")

            # TEMPORARY DEBUG: Let's see what register_device is receiving
            _logger.info(
                f"[DEBUG] About to call register_device with player_id='{player_id}' (type: {type(player_id)})")

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

            return request.make_json_response({
                "status": "success",
                "message": "Device registered successfully",
                "device_id": device_id
            })

        except Exception as e:
            _logger.error(f"Error registering device: {str(e)}")
            return request.make_json_response({
                "status": "error",
                "message": str(e)
            })

    @http.route('/onesignal/test_notification', type='http', auth='user', methods=['POST'], csrf=False)
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
                return request.make_json_response({
                    "status": "success",
                    "message": "Test notification sent successfully!"
                })
            else:
                _logger.warning("No active devices found for test notification")
                return request.make_json_response({
                    "status": "warning",
                    "message": "No active devices found. Please register your device first."
                })

        except Exception as e:
            _logger.error(f"Error sending test notification: {str(e)}")
            return request.make_json_response({
                "status": "error",
                "message": f"Error: {str(e)}"
            })

    @http.route('/onesignal/unregister', type='http', auth='user', methods=['POST'], csrf=False)
    def unregister_device(self, **kwargs):
        """Unregister device"""
        try:
            if request.httprequest.is_json:
                data = request.get_json_data()
            else:
                raw_data = request.httprequest.data.decode('utf-8')
                data = json.loads(raw_data) if raw_data else {}

            player_id = data.get('player_id')

            if not player_id:
                return request.make_json_response({
                    "status": "error",
                    "message": "Player ID is required"
                })

            _logger.info(f"Unregistering device: {player_id[:8]}...")

            success = request.env['res.users.device'].sudo().unregister_device(player_id)

            return request.make_json_response({
                "status": "success" if success else "warning",
                "message": "Device unregistered" if success else "Device not found"
            })
        except Exception as e:
            _logger.error(f"Error unregistering device: {str(e)}")
            return request.make_json_response({
                "status": "error",
                "message": str(e)
            })

    @http.route('/onesignal/update_last_seen', type='http', auth='user', methods=['POST'], csrf=False)
    def update_last_seen(self, **kwargs):
        """Update device last seen timestamp"""
        try:
            if request.httprequest.is_json:
                data = request.get_json_data()
            else:
                raw_data = request.httprequest.data.decode('utf-8')
                data = json.loads(raw_data) if raw_data else {}

            player_id = data.get('player_id')

            if not player_id:
                return request.make_json_response({
                    "status": "error",
                    "message": "Player ID is required"
                })

            success = request.env['res.users.device'].sudo().update_last_seen(player_id)
            return request.make_json_response({
                "status": "success" if success else "warning",
                "message": "Last seen updated" if success else "Device not found"
            })
        except Exception as e:
            _logger.error(f"Error updating last seen: {str(e)}")
            return request.make_json_response({
                "status": "error",
                "message": str(e)
            })

    @http.route('/onesignal/user_devices', type='http', auth='user', methods=['GET', 'POST'], csrf=False)
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

            return request.make_json_response({
                "status": "success",
                "devices": device_data,
                "count": len(device_data)
            })
        except Exception as e:
            _logger.error(f"Error getting user devices: {str(e)}")
            return request.make_json_response({
                "status": "error",
                "message": str(e)
            })

    @http.route('/onesignal/test', type='http', auth='user', methods=['GET', 'POST'], csrf=False)
    def test_endpoint(self, **kwargs):
        """Test endpoint to verify controller is working"""
        try:
            return request.make_json_response({
                "status": "success",
                "message": "OneSignal controller is working perfectly!",
                "user": request.env.user.name,
                "user_id": request.env.user.id,
                "timestamp": str(request.env.cr.now()),
                "session_info": "Active"
            })
        except Exception as e:
            return request.make_json_response({
                "status": "error",
                "message": f"Controller error: {str(e)}"
            })