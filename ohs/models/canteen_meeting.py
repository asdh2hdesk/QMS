from odoo import models, fields, api, _

class CanteenMeeting(models.Model):
    _name = 'canteen.meeting'
    _description = 'Canteen Meeting'

    line_ids = fields.One2many('canteen.meeting.line', 'meeting_id', string='Meeting Lines')


class CanteenMeetingLine(models.Model):
    _name = 'canteen.meeting.line'
    _description = 'Canteen Meeting Line'

    meeting_id = fields.Many2one('canteen.meeting', string='Meeting Reference')
    jan = fields.Date(string='Jan')
    feb = fields.Date(string='Feb')
    mar = fields.Date(string='Mar')
    apr = fields.Date(string='Apr')
    may = fields.Date(string='May')
    jun = fields.Date(string='Jun')
    jul = fields.Date(string='Jul')
    aug = fields.Date(string='Aug')
    sep = fields.Date(string='Sep')
    oct = fields.Date(string='Oct')
    nov = fields.Date(string='Nov')
    dec = fields.Date(string='Dec')
