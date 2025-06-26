{
    'name': 'Calibration Schedule',
    'version': '1.0',
    'category': 'Maintenance',
    'depends': ['base', 'maintenance', 'calendar'],  # <-- Add 'maintenance' here
    'data': [
        'security/ir.model.access.csv',
        'data/scheduled_actions.xml',
        'views/report_templates.xml',
        'views/report_template_work.xml',
        'views/calibration_report_wizard_view.xml',
        'views/calibration_work_instruction_views.xml',
        'views/calibration_year_views.xml',
        'views/calibration_view.xml'

    ],
    'installable': True,
    'application': True,
}
