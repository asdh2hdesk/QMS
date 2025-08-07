{
    'name': 'OneSignal Notifications',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'Send notifications to Flutter app via OneSignal',
    'description': '''
        This module integrates Odoo with OneSignal to send push notifications
        for chat messages, alerts, and emails to your Flutter mobile application.
    ''',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/onesignal_config_views.xml',
        'views/menu_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}