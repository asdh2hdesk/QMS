{
    'name': 'ASD Production',
    'version': '16.0.1.0.0',
    'summary': 'Custom Production Management Module',
    "sequence": 1,
    'category': 'Manufacturing',
    'author': 'ASD',
    'License': 'LGPL-3',
    'depends': ['base', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/production_order_views.xml',
        # 'views/production_bom_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
