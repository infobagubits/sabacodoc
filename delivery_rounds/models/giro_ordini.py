from odoo import models, fields, api
from odoo.exceptions import ValidationError

class GiroOrdine(models.Model):
    _name = 'giri.ordine'
    _description = 'Giro Ordini'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nome', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        readonly=True,
        default=lambda self: self.env.company.currency_id
    )

    giorno_consegna = fields.Selection(
        [
            ('lunedi', 'Lunedì'),
            ('martedi', 'Martedì'),
            ('mercoledi', 'Mercoledì'),
            ('giovedi', 'Giovedì'),
            ('venerdi', 'Venerdì'),
            ('sabato', 'Sabato'),
            ('domenica', 'Domenica'),
        ],
        string="Giorno consegna"
    )

    note = fields.Text(string='Note')
    
    # CAMPO OBRIGATÓRIO PARA FUNCIONAR A VIEW
    riga_ids = fields.One2many('giri.ordine.riga', 'giro_id', string='Clienti sul giro')
    
    # NOVO: lista de pedidos vinculados ao giro
    order_ids = fields.One2many(
        'sale.order',
        'giro_id',
        string='Ordini del giro',
        domain=[('stato_preparazione', '!=', 'stampato')]
    )

    # Campo computado para o total dos pedidos
    total_ordini = fields.Monetary(
        string='Totale',
        compute='_compute_total_ordini',
        currency_field='currency_id',
        store=True
    )

    @api.depends('order_ids.amount_total', 'order_ids.state', 'order_ids.stato_preparazione')
    def _compute_total_ordini(self):
        for record in self:
            total = sum(order.amount_total for order in record.order_ids.filtered(
                lambda o: o.state != 'cancel' and o.stato_preparazione != 'stampato'))
            record.total_ordini = total

class GiroOrdineRiga(models.Model):
    _name = 'giri.ordine.riga'
    _description = 'Riga Giro Ordini'
    _order = 'sequence, id'
    _sql_constraints = [
        ('unique_partner_giro', 
         'UNIQUE(giro_id, partner_id)',
         'Non è possibile aggiungere lo stesso cliente due volte nello stesso giro!')
    ]

    sequence = fields.Integer(string='Sequence', default=10)
    giro_id = fields.Many2one('giri.ordine', string='Giro Ordine', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    telefono = fields.Char(string='Telefona', related='partner_id.phone', store=True)
    stato = fields.Selection([
        ('da_chiamare', 'Da chiamare'),
        ('sospeso', 'Sospeso'),
        ('non_vuole', 'Non vuole niente'),
        ('ordinato', 'Ordinato')
    ], string='Stato')
    note = fields.Text(string='Note')

    ordini_aperti = fields.Integer(string='Ordini aperti', compute='_compute_ordini_aperti', store=False)

    @api.constrains('giro_id', 'partner_id')
    def _check_partner_unique(self):
        for record in self:
            if record.partner_id and record.giro_id:
                count = self.search_count([
                    ('giro_id', '=', record.giro_id.id),
                    ('partner_id', '=', record.partner_id.id),
                    ('id', '!=', record.id)
                ])
                if count > 0:
                    raise ValidationError('Non è possibile aggiungere lo stesso cliente due volte nello stesso giro!')

    def _update_order_sequence(self):
        """Atualiza a sequência dos pedidos"""
        if self.giro_id and self.partner_id:
            orders = self.env['sale.order'].search([
                ('giro_id', '=', self.giro_id.id),
                ('partner_id', '=', self.partner_id.id)
            ])
            if orders:
                orders.write({'sequenza_consegna': self.sequence})

    def write(self, vals):
        result = super().write(vals)
        if 'sequence' in vals:
            # Reordena todas as linhas do giro
            all_lines = self.env['giri.ordine.riga'].search([
                ('giro_id', '=', self.giro_id.id)
            ], order='sequence')
            
            # Atualiza as sequências para garantir ordem correta
            sequence = 1
            for line in all_lines:
                if line.sequence != sequence:
                    line.sequence = sequence
                sequence += 1
                
            # Atualiza a sequência dos pedidos
            self._update_order_sequence()
            self.env.cr.commit()
        return result

    @api.model
    def create(self, vals):
        if vals.get('giro_id'):
            # Conta quantos registros já existem neste giro
            existing_count = self.env['giri.ordine.riga'].search_count([
                ('giro_id', '=', vals['giro_id'])
            ])
            # Define a sequência como o próximo número
            vals['sequence'] = existing_count + 1
        
        riga = super().create(vals)
        if riga.giro_id:
            riga._update_order_sequence()
        return riga

    @api.depends('partner_id')
    def _compute_ordini_aperti(self):
        for riga in self:
            count = self.env['sale.order'].search_count([
                ('partner_id', '=', riga.partner_id.id),
                ('giro_id', '=', riga.giro_id.id),
                ('state', '=', 'draft'),
                ('stato_preparazione', '!=', 'stampato')
            ])
            riga.ordini_aperti = count

    def action_apri_ordini(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ordini del cliente',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id},
        }
    
    def action_criar_ordini_giro(self):
        self.ensure_one()
        # Obtém a lista de preços padrão da empresa atual
        pricelist = self.env['product.pricelist'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuovo Ordine',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_giro_id': self.giro_id.id,
                'default_sequenza_consegna': self.sequence,
                'default_pricelist_id': pricelist.id,
            },
        }

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    giro_id = fields.Many2one('giri.ordine', string='Giro')
    sequenza_consegna = fields.Integer(string='Sequenza consegna')
    stato_preparazione = fields.Selection([
        ('da_preparare', 'Da preparare'),
        ('preparato', 'Preparato'),
        ('stampato', 'Stampato')
    ], string='Stato preparazione', default='da_preparare', tracking=True)

    @api.onchange('giro_id')
    def _onchange_giro_id(self):
        if self.giro_id and self.giro_id.giorno_consegna:
            # Mapeamento dos dias da semana do Odoo para números (0-6, onde 0 é segunda-feira)
            giorni_mapping = {
                'lunedi': 0,    # Segunda-feira
                'martedi': 1,   # Terça-feira
                'mercoledi': 2, # Quarta-feira
                'giovedi': 3,   # Quinta-feira
                'venerdi': 4,   # Sexta-feira
                'sabato': 5,    # Sábado
                'domenica': 6,  # Domingo
            }
            
            from datetime import datetime, timedelta
            import pytz
            
            # Obtém a data atual no timezone do usuário
            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            today = datetime.now(user_tz).date()
            
            # Dia da semana atual (0-6)
            current_weekday = today.weekday()
            
            # Dia da semana desejado do giro
            target_weekday = giorni_mapping[self.giro_id.giorno_consegna]
            
            # Calcula quantos dias faltam para o próximo dia da semana desejado
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Se for hoje ou já passou na semana
                days_ahead += 7
            
            # Calcula a próxima data
            delivery_date = today + timedelta(days=days_ahead)
            
            # Atualiza o campo commitment_date com a data calculada
            self.commitment_date = datetime.combine(delivery_date, datetime.min.time())