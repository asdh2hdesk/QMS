{
    'name': 'engineering_change_note',
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
    'depends': ['hr', 'base', 'sale', 'mrp', 'product', 'maintenance', 'crm', 'project', 'l10n_in','board','web','iatf','xf_doc_approval','global_translation'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_ecn_template.xml',
        'views/ecn_view.xml',
        'views/ppap_view.xml'

    ],


    'installable': True,
    'auto_install': False,
    'application': True,
}
