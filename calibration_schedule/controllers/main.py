from odoo import http
from odoo.http import request, content_disposition


class CalibrationReportController(http.Controller):
    @http.route('/web/content/calibration.schedule/<int:schedule_id>/report/<string:filename>', type='http',
                auth='user')
    def get_pdf(self, schedule_id, filename, **kw):
        schedule = request.env['calibration.schedule'].browse(schedule_id)
        if not schedule.exists():
            return request.not_found()

        pdf_content = schedule.get_pdf_report()
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition(filename)),
        ]
        return request.make_response(pdf_content, headers=headers)