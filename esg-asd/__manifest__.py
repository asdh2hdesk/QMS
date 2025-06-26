{
    'name': 'Environmental, Social and Governance Reports',
    'version': '16.0.1.0',
    'category': 'Custom',
    'summary': 'Manage ESG metrics integrated with IATF QMS',
    'description': """
        This module integrates Environmental, Social, and Governance (ESG) metrics
        with an IATF 16949-compliant Quality Management System (QMS) in Odoo.
        Features include tracking emissions, social compliance, governance audits,
        and generating consolidated ESG reports.
    """,
    'author': 'ASD',
    'price': 0,
    'license': 'LGPL-3',
    'sequence': 1,
    'currency': "INR",
    'depends': ['base', 'mail'],  # Added 'mail' for chatter and activities
    'data': [
        'security/ir.model.access.csv',
        'data/esg_sequences.xml',
'views/esg_environmental_views.xml',

        'views/esg_social_views.xml',
        'views/esg_governance_views.xml',



    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}