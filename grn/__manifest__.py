{
    'name': 'GRN_Management',
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
    'depends': ['hr', 'base', 'sale', 'mrp', 'product', 'maintenance', 'crm', 'project', 'l10n_in','board','web','mail','global_translation'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/grn_management.xml',
        'views/grn_control_plan.xml',
        'views/grn_inspection.xml',


    ],

    'external_dependencies': {
        'python': ['qrcode'],
        # 'bin': ['wkhtmltopdf'],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
