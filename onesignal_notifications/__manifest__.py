{
    'name': 'OneSignal Notifications',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'OneSignal Push Notifications Integration',
    'description': '''
        This module integrates OneSignal push notifications with Odoo.
        It sends notifications for:
        - New chat messages
        - New emails
        - Approval requests
    ''',
    'depends': ['base', 'mail'],
    'data': [
        'data/ir_config_parameter.xml',
    ],
    'installable': True,
    'auto_install': False,
}