{
    'name': 'Gauge R&R',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Module for Gauge R&R Data Entry',
    'depends': ['base','board', 'maintenance', 'calendar','mail','global_translation'],  # Add 'mail' here
    
    "data": [
        "security/ir.model.access.csv",
        "views/constant_values.xml",
        "views/measuring_instruments.xml",
        "views/msa_view.xml",
        
    ],
    'installable': True,
    'application': True,
}