# -*- coding: utf-8 -*-
from odoo import fields, models


class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    # Campi "risconto" sulla riga del widget. Il widget carica i campi da
    # fields_get(), quindi vengono esposti automaticamente al componente OWL:
    # nel template `line.data.deferred_start_date` e' disponibile senza altro.
    deferred_start_date = fields.Date(string="Data inizio risconto")
    deferred_end_date = fields.Date(string="Data fine risconto")

    # -------------------------------------------------------------------
    # PROPAGAZIONE VERSO account.move.line
    # -------------------------------------------------------------------
    # Alla validazione (_action_validate -> _validation_lines_vals) ogni riga
    # viene convertita in vals di account.move.line tramite _get_aml_values()
    # (verificato sul sorgente 18.0: bank_rec_widget.py, chiamato dentro
    # _validation_lines_vals con Command.create(line._get_aml_values(...))).
    def _get_aml_values(self, **kwargs):
        vals = super()._get_aml_values(**kwargs)
        # Applica le date solo se entrambe valorizzate, per non passare
        # valori parziali ad account.move.line.
        if self.deferred_start_date and self.deferred_end_date:
            vals['deferred_start_date'] = self.deferred_start_date
            vals['deferred_end_date'] = self.deferred_end_date
        return vals
