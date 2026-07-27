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
        string="Giorno consegna",
        required=True  # Campo obbligatorio per creare un giro
    )

    note = fields.Text(string='Note')
    
    # CAMPO OBBLIGATORIO PER FUNZIONARE LA VIEW
    riga_ids = fields.One2many('giri.ordine.riga', 'giro_id', string='Clienti sul giro')
    
    # NUOVO: lista di ordini collegati al giro
    order_ids = fields.One2many(
        'sale.order',
        'giro_id',
        string='Ordini del giro',
        domain=[ ('state', '!=', 'cancel'),('stato_preparazione', '!=', 'stampato')]
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

    # Mappatura weekday Python (0=lunedì, 6=domenica) -> valore giorno_consegna
    _GIORNO_CONSEGNA_BY_WEEKDAY = {
        0: 'lunedi',
        1: 'martedi',
        2: 'mercoledi',
        3: 'giovedi',
        4: 'venerdi',
        5: 'sabato',
        6: 'domenica',
    }

    @api.model
    def _cron_reset_stato_da_chiamare(self):
        """
        Ogni giorno: per i giri il cui giorno di consegna è oggi o ieri,
        imposta tutte le righe (contatti) a stato "Da chiamare".
        Es.: giro lunedì → lunedì sera o martedì tutti i contatti tornano "Da chiamare".
        Usa il timezone dell'utente (cron) per il "oggi" e sudo() per evitare limiti di permessi.
        """
        from datetime import datetime
        try:
            import pytz
        except ImportError:
            pytz = None

        # Data "oggi" nel timezone dell'utente (res.users.tz) o UTC
        tz_name = self.env.user.tz or 'UTC'
        if pytz:
            tz = pytz.timezone(tz_name)
            today = datetime.now(tz).date()
        else:
            today = datetime.now().date()

        weekday_today = today.weekday()  # 0=lunedì, 6=domenica
        weekday_yesterday = (weekday_today - 1) % 7
        giorni_to_reset = [
            self._GIORNO_CONSEGNA_BY_WEEKDAY[weekday_today],
            self._GIORNO_CONSEGNA_BY_WEEKDAY[weekday_yesterday],
        ]
        giri = self.sudo().search([('giorno_consegna', 'in', giorni_to_reset)])
        for giro in giri:
            if giro.riga_ids:
                giro.riga_ids.sudo().write({'stato': 'da_chiamare'})

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
    ], string='Stato', default='da_chiamare')
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
            
            # Aggiorna le sequenze per garantire ordine corretto
            sequence = 1
            for line in all_lines:
                if line.sequence != sequence:
                    line.sequence = sequence
                sequence += 1
                
            # Aggiorna la sequenza degli ordini
            self._update_order_sequence()
            self.env.cr.commit()
        return result

    @api.model
    def create(self, vals):
        if vals.get('giro_id'):
            # Conta quanti record esistono già in questo giro
            existing_count = self.env['giri.ordine.riga'].search_count([
                ('giro_id', '=', vals['giro_id'])
            ])
            # Definisce la sequenza come il prossimo numero
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

    def unlink(self):
        giro_ids = self.mapped('giro_id')
        result = super(GiroOrdineRiga, self).unlink()
        for giro in giro_ids:
            linhas = self.env['giri.ordine.riga'].search([
                ('giro_id', '=', giro.id)
            ], order='sequence')
            sequence = 1
            for linha in linhas:
                if linha.sequence != sequence:
                    linha.sequence = sequence
                sequence += 1
        return result

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    giro_id = fields.Many2one(
        'giri.ordine',
        string='Giro',
        groups='delivery_rounds.group_delivery_rounds_user',
    )
    sequenza_consegna = fields.Integer(
        string='Sequenza consegna',
        groups='delivery_rounds.group_delivery_rounds_user',
    )
    stato_preparazione = fields.Selection([
        ('da_preparare', 'Da preparare'),
        ('preparato', 'Preparato'),
        ('stampato', 'Stampato')
    ], string='Stato preparazione', default='da_preparare', tracking=True,
        groups='delivery_rounds.group_delivery_rounds_user')

    @api.onchange('giro_id')
    def _onchange_giro_id(self):
        if self.giro_id and self.giro_id.giorno_consegna:
            # Mappatura dei giorni della settimana di Odoo a numeri (0-6, dove 0 è lunedì)
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
            
            # Ottiene la data corrente nel timezone dell'utente
            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            today = datetime.now(user_tz).date()
            
            # Giorno della settimana corrente (0-6)
            current_weekday = today.weekday()
            
            # Giorno della settimana desiderato del giro
            target_weekday = giorni_mapping[self.giro_id.giorno_consegna]
            
            # Calcola quanti giorni mancano al prossimo giorno della settimana desiderato
            days_ahead = target_weekday - current_weekday
            if days_ahead < 0:  # Se è già passato nella settimana
                days_ahead += 7
            
            # Calcola la prossima data
            delivery_date = today + timedelta(days=days_ahead)

            # Imposta l'orario desiderato (17:00) nel timezone utente
            delivery_datetime = datetime.combine(delivery_date, datetime.min.time()).replace(hour=17)
            # Se il campo commitment_date è di tipo datetime aware, converti nel timezone corretto
            if delivery_datetime.tzinfo is None:
                # Aggiungi il timezone utente
                user_tz = pytz.timezone(self.env.user.tz or 'UTC')
                delivery_datetime = user_tz.localize(delivery_datetime)
            self.commitment_date = delivery_datetime