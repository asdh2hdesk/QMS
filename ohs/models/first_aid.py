from odoo import models, fields, api

class FirstAidBox(models.Model):
    _name = 'first.aid.box'
    _description = 'First Aid Box'

    location = fields.Selection([
        ('gate', 'Gate'),
        ('dispatch', 'Dispatch'),
        ('office', 'Office'),
        ('mixing', 'Mixing')
    ], string='Location', required=True)
    year = fields.Char(string='Year', required=True)
    month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December')
    ], string='Month', required=True)
    sl_no = fields.Integer(string='Sl No')
    box_no = fields.Integer(string='First Aid Box No.')
    item_ids = fields.One2many('first.aid.box.item', 'box_id', string='Contents')
    signature = fields.Char(string='Signature')
    date = fields.Date(string='Date')
    


class FirstAidBoxItem(models.Model):
    _name = 'first.aid.box.item'
    _description = 'First Aid Box Item'

    

    name = fields.Selection([
        ('band_aid', 'Band Aid'),
        ('eye_drop', 'Eye Drop'),
        ('burnol', 'Burnol'),
        ('soframycin', 'Soframycin'),
        ('cotton', 'Cotton'),
        ('bandage', 'Bandage')
    ], string='Content', required=True)
    availability = fields.Selection([
        ('available', 'Available (√)'),
        ('not_available', 'Not Available (X)')
    ], default='available', string='Availability')
    box_id = fields.Many2one('first.aid.box', string='First Aid Box')
    
    # Weekly check fields for each month
    # January
    w1 = fields.Selection([('tick', '√'), ('cross', 'X')], string='W1')
    w2 = fields.Selection([('tick', '√'), ('cross', 'X')], string='W2')
    w3 = fields.Selection([('tick', '√'), ('cross', 'X')], string='W3')
    w4 = fields.Selection([('tick', '√'), ('cross', 'X')], string='W4')

    # Display field for showing (√/X) format in views
    @api.depends('availability')
    def _compute_availability_display(self):
        for record in self:
            if record.availability == 'available':
                record.availability_display = '(√/X)'
            else:
                record.availability_display = '(√/X)'
    
    availability_display = fields.Char(string='A', compute='_compute_availability_display')