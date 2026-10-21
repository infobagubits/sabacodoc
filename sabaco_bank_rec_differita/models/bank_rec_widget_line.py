from odoo import api, fields, models


class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    # Esposti al template OWL tramite fields_get (line.data.<campo>).
    deferred_start_date = fields.Date(
        string="Data inizio differita",
        compute='_compute_deferred_start_date',
        store=True,
        readonly=False,
    )
    deferred_end_date = fields.Date(
        string="Data fine differita",
        compute='_compute_deferred_end_date',
        store=True,
        readonly=False,
    )
    sabaco_differita_ammessa = fields.Boolean(compute='_compute_sabaco_differita_ammessa')

    @api.depends('source_aml_id')
    def _compute_deferred_start_date(self):
        for line in self:
            if line.flag in ('aml', 'new_aml'):
                line.deferred_start_date = line.source_aml_id.deferred_start_date
            else:
                line.deferred_start_date = line.deferred_start_date

    @api.depends('source_aml_id')
    def _compute_deferred_end_date(self):
        for line in self:
            if line.flag in ('aml', 'new_aml'):
                line.deferred_end_date = line.source_aml_id.deferred_end_date
            else:
                line.deferred_end_date = line.deferred_end_date

    @api.depends('account_id', 'flag', 'tax_repartition_line_id')
    def _compute_sabaco_differita_ammessa(self):
        # La data differita distribuisce costi o ricavi: non ha senso su cassa, banca,
        # clienti/fornitori, righe da riconciliare o righe d'imposta.
        for line in self:
            line.sabaco_differita_ammessa = (
                line.flag in ('manual', 'auto_balance', 'aml')
                and not line.tax_repartition_line_id
                and line.account_id.internal_group in ('expense', 'income')
            )

    def _get_aml_values(self, **kwargs):
        # La validazione ricrea le righe della transazione da questi valori.
        if self.sabaco_differita_ammessa and self.deferred_start_date:
            kwargs = {
                'deferred_start_date': self.deferred_start_date,
                'deferred_end_date': self.deferred_end_date or self.deferred_start_date,
                **kwargs,
            }
        return super()._get_aml_values(**kwargs)
