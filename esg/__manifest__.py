{
    'name': 'Environmental Social Governance',
    'version': '16.0.1.0',
    'category': 'Custom',
    'summary': '',
    'description': """""",
    'author': 'ASD',
    'price': 0,
    'license': 'LGPL-3',
    'sequence': 1,
    'currency': "INR",
    'website': 'https://asdsoftwares.com/',
    'depends': ['hr', 'base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/esg_framework.xml',
        'views/esg_material_topic.xml',
        'views/esg_disclosure.xml',
        'views/esg_emission_activity.xml',
        'views/esg_emission_factors.xml',

        'views/esg_metric.xml',
        'views/esg_goal.xml',
        'views/esg_target.xml',
        'views/esg_dataentry.xml',

    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
