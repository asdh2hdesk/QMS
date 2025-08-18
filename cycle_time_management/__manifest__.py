{
    'name': 'Manufacturing Cycle Time Management',
    'version': '1.0.0',
    'category': 'Manufacturing',
    'summary': 'Manage manufacturing cycle time calculations and production planning',
    'description': """
        This module provides comprehensive cycle time management for manufacturing operations:
        - Track part operations and machine assignments
        - Calculate cycle times and takt times
        - Monitor production efficiency and capacity planning
        - Generate production reports and analytics
    """,
    'author': 'asd',
    'sequence': '-1000',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr', 'base','iatf','product', 'maintenance', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/cycle_time_calculation_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}