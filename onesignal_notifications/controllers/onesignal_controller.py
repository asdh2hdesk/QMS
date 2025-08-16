from odoo import http
from odoo.http import request

class OneSignalController(http.Controller):

    @http.route('/onesignal/register', type='json', auth='user', methods=['POST'], csrf=False)
    def register_device(self, player_id, device_name=None, **kwargs):
        request.env['res.users.device'].sudo().register_device(player_id, device_name)
        return {"status": "success", "message": "Device registered"}

    @http.route('/onesignal/unregister', type='json', auth='user', methods=['POST'], csrf=False)
    def unregister_device(self, player_id, **kwargs):
        request.env['res.users.device'].sudo().unregister_device(player_id)
        return {"status": "success", "message": "Device unregistered"}
