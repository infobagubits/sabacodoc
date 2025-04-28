from odoo import models, fields, api
from odoo.exceptions import ValidationError

class GiroOrdine(models.Model):
    _name = 'giri.ordine'
    _description = 'Giro Ordini'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nome', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Valuta',
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
    
    # Campo obbligatorio per il funzionamento della vista
    riga_ids = fields.One2many('giri.ordine.riga', 'giro_id', string='Clienti sul giro')
    
    # Lista degli ordini collegati al giro
    order_ids = fields.One2many(
        'sale.order',
        'giro_id',
        string='Ordini del giro',
        domain=[('stato_preparazione', '!=', 'stampato')]
    )

    # Campo calcolato per il totale degli ordini
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

    sequence = fields.Integer(string='Sequenza', default=10)
    giro_id = fields.Many2one('giri.ordine', string='Giro Ordine', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    telefono = fields.Char(string='Telefono', related='partner_id.phone', store=True)
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
        """Aggiorna la sequenza degli ordini"""
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
            # Riordina tutte le righe del giro
            all_lines = self.env['giri.ordine.riga'].search([
                ('giro_id', '=', self.giro_id.id)
            ], order='sequence')
            
            # Aggiorna le sequenze per garantire l'ordine corretto
            sequence = 1
            for line in all_lines:
                if line.sequence != sequence:
                    super(GiroOrdineRiga, line).write({'sequence': sequence})
                    # Aggiorna immediatamente gli ordini associati
                    orders = self.env['sale.order'].search([
                        ('giro_id', '=', line.giro_id.id),
                        ('partner_id', '=', line.partner_id.id)
                    ])
                    if orders:
                        orders.write({'sequenza_consegna': sequence})
                sequence += 1
            
            self.env.cr.commit()
        return result

    @api.model
    def create(self, vals):
        if vals.get('giro_id'):
            # Conta quanti record esistono già in questo giro
            existing_count = self.env['giri.ordine.riga'].search_count([
                ('giro_id', '=', vals['giro_id'])
            ])
            # Imposta la sequenza come numero successivo
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
        
        # Ottiene il listino prezzi predefinito dell'azienda corrente
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
            # Mappatura dei giorni della settimana Odoo in numeri (0-6, dove 0 è lunedì)
            giorni_mapping = {
                'lunedi': 0,    # Lunedì
                'martedi': 1,   # Martedì
                'mercoledi': 2, # Mercoledì
                'giovedi': 3,   # Giovedì
                'venerdi': 4,   # Venerdì
                'sabato': 5,    # Sabato
                'domenica': 6,  # Domenica
            }
            
            from datetime import datetime, timedelta
            import pytz
            
            # Ottiene la data attuale nel fuso orario dell'utente
            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            today = datetime.now(user_tz).date()
            
            # Giorno della settimana attuale (0-6)
            current_weekday = today.weekday()
            
            # Giorno della settimana desiderato del giro
            target_weekday = giorni_mapping[self.giro_id.giorno_consegna]
            
            # Calcola quanti giorni mancano al prossimo giorno della settimana desiderato
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Se è oggi o è già passato questa settimana
                days_ahead += 7
            
            # Calcola la prossima data
            delivery_date = today + timedelta(days=days_ahead)
            
            # Aggiorna il campo commitment_date con la data calcolata
            self.commitment_date = datetime.combine(delivery_date, datetime.min.time())