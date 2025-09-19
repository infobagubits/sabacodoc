{
    'name': 'Teste de Atualização de Campos',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Módulo de teste para verificar atualização de campos',
    'description': """
        Este módulo adiciona campos de teste para verificar se a atualização
        de módulos funciona corretamente sem desinstalar.
    """,
    'author': 'Teste',
    'website': 'https://www.teste.com',
    'depends': ['base', 'contacts', 'res_partner_customization'],
    'data': [
        'views/res_partner_test_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
