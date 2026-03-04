# -*- coding: utf-8 -*-

import re
from datetime import datetime, time, timedelta

import pytz

from odoo import api, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # Formati data comuni per il parsing del nome lotto (nome = data -> data di scadenza)
    _DATE_NAME_FORMATS = [
        '%Y-%m-%d',      # 2026-12-31
        '%d/%m/%Y',      # 31/12/2026
        '%d-%m-%Y',      # 31-12-2026
        '%d.%m.%Y',      # 31.12.2026
        '%d/%m/%y',      # 31/12/26
        '%d-%m-%y',      # 31-12-26
        '%d.%m.%y',      # 31.12.26
        '%y%m%d',        # 261231 (usato in codici a barre)
        '%Y%m%d',        # 20261231
    ]

    def _date_to_expiration_datetime_utc(self, parsed_date):
        """
        Converte la data (solo giorno) in datetime UTC "fine giornata" nel fuso dell'utente.
        Così in interfaccia la data di scadenza mostra esattamente il giorno inserito (es. 23/03/2026).
        """
        if not parsed_date:
            return None
        tz_name = self.env.user.tz or 'UTC'
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.utc
        local_end_of_day = datetime.combine(parsed_date, time(23, 59, 59))
        local_end_of_day = tz.localize(local_end_of_day, is_dst=False)
        utc_dt = local_end_of_day.astimezone(pytz.utc)
        return utc_dt.replace(tzinfo=None)

    def _product_default_expiration_datetime(self):
        """
        Restituisce la data di scadenza di default del prodotto (oggi + expiration_time giorni),
        come fa il compute di product_expiry. Usare quando il nome lotto non è una data.
        """
        if not self.product_id or not self.product_id.use_expiration_date:
            return None
        duration = self.product_id.product_tmpl_id.expiration_time
        if duration is None or duration is False:
            duration = 0
        return datetime.now() + timedelta(days=duration)

    @api.onchange('name')
    def _onchange_name_set_expiration_date(self):
        """
        Se il nome del lotto è interpretabile come data e il prodotto ha
        "Usa data di scadenza", imposta quella data come data di scadenza.
        Se il nome non è una data, imposta la scadenza del prodotto (oggi + expiration_time).
        """
        if not self.name or not self.product_id or not self.product_id.use_expiration_date:
            return
        parsed = self._parse_date_from_lot_name(self.name)
        if parsed:
            self.expiration_date = self._date_to_expiration_datetime_utc(parsed)
        else:
            self.expiration_date = self._product_default_expiration_datetime()

    @api.model_create_multi
    def create(self, vals_list):
        """
        Se il nome è una data: imposta expiration_date a quella data (con write per persistere).
        Se il nome non è una data e il prodotto ha scadenza: imposta expiration_date alla scadenza del prodotto.
        """
        lots = super().create(vals_list)
        for lot, vals in zip(lots, vals_list):
            name = vals.get('name')
            if not name or not lot.product_id or not lot.product_id.use_expiration_date:
                continue
            parsed = self._parse_date_from_lot_name(name)
            if parsed:
                exp_utc = lot._date_to_expiration_datetime_utc(parsed)
                if exp_utc:
                    lot.write({'expiration_date': exp_utc})
            else:
                default_exp = lot._product_default_expiration_datetime()
                if default_exp:
                    lot.write({'expiration_date': default_exp})
        return lots

    def write(self, vals):
        """
        Se si modifica il nome in una data: aggiorna expiration_date a quella data.
        Se si modifica il nome in qualcosa che non è una data: imposta expiration_date alla scadenza del prodotto.
        """
        if vals.get('name') and (self.product_id or vals.get('product_id')):
            product = self.product_id or self.env['product.product'].browse(vals.get('product_id'))
            if product.use_expiration_date:
                parsed = self._parse_date_from_lot_name(vals['name'])
                if parsed:
                    exp_utc = self._date_to_expiration_datetime_utc(parsed)
                    if exp_utc:
                        vals['expiration_date'] = exp_utc
                else:
                    duration = product.product_tmpl_id.expiration_time
                    if duration is not None and duration is not False:
                        vals['expiration_date'] = datetime.now() + timedelta(days=duration)
        return super().write(vals)

    @api.model
    def _parse_date_from_lot_name(self, name):
        """
        Tenta di interpretare la stringa come data. Restituisce un datetime.date
        o None se non interpretabile come data. La data restituita è esattamente quella interpretata (nessun anno aggiunto).
        """
        if not name or not isinstance(name, str):
            return None
        raw = name.strip()
        if not raw:
            return None
        # Solo cifre e separatori tipici di date
        if not re.match(r'^[\d/\-\.]+$', raw):
            return None
        for fmt in self._DATE_NAME_FORMATS:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None
