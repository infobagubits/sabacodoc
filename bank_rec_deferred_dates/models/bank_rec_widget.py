# -*- coding: utf-8 -*-
from odoo import fields, models


class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    # Campi "risconto" replicati sulla riga del widget di riconciliazione.
    # Sono campi non memorizzati (il modello è transiente): servono solo a
    # trasportare il valore fino alla creazione dell'account.move.line.
    deferred_start_date = fields.Date(string="Data inizio")
    deferred_end_date = fields.Date(string="Data fine")

    # -------------------------------------------------------------------
    # PROPAGAZIONE VERSO account.move.line
    # -------------------------------------------------------------------
    # ATTENZIONE: verifica il nome esatto del metodo nella TUA point-release
    #   file:  addons/account_accountant/models/bank_rec_widget.py
    # Nelle versioni 18.0 il metodo che costruisce i vals della riga
    # contabile a partire dalla riga del widget è, di norma:
    #       _prepare_move_line_default_vals(self)
    # e restituisce una LISTA di dizionari di vals.
    # Se nella tua versione ha firma/nome diversi, adegua l'override qui sotto.
    def _prepare_move_line_default_vals(self, counterpart_vals=None):
        vals_list = super()._prepare_move_line_default_vals(
            counterpart_vals=counterpart_vals
        )
        for vals in vals_list:
            if self.deferred_start_date:
                vals['deferred_start_date'] = self.deferred_start_date
            if self.deferred_end_date:
                vals['deferred_end_date'] = self.deferred_end_date
        return vals_list


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    # Se nella tua versione la creazione della riga manuale azzera i campi
    # extra (perché ricostruisce line_ids da zero), potresti dover intervenire
    # anche qui, ad es. nel metodo che aggiunge/aggiorna la riga manuale
    # (tipicamente _action_add_new_amls / _lines_widget_recompute_*).
    # Lasciato come punto di estensione: di norma NON serve toccarlo se
    # l'override sopra è sufficiente.
    pass
