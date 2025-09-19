from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campos de teste para verificar atualização
    campo_teste_1 = fields.Char(
        string='Campo Teste 1',
        help='Campo de teste para verificar atualização',
        groups='base.group_user',
    )

    campo_teste_2 = fields.Selection([
        ('opcao1', 'Opção 1'),
        ('opcao2', 'Opção 2'),
        ('opcao3', 'Opção 3'),
    ], string='Campo Teste 2', help='Campo de seleção para teste')

    campo_teste_3 = fields.Text(
        string='Campo Teste 3',
        help='Campo de texto para teste',
        groups='base.group_user',
    )

    campo_teste_4 = fields.Boolean(
        string='Campo Teste 4',
        help='Campo booleano para teste',
        default=False,
    )

    campo_teste_5 = fields.Float(
        string='Campo Teste 5',
        help='Campo numérico para teste',
        digits=(16, 2),
    )
