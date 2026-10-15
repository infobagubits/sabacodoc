from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _validate_analytic_distribution(self):
        """Le righe della registrazione di storno IVA differita sono
        generate automaticamente: in una registrazione 'entry' tutte le
        righe sono di tipo 'product', quindi la quota indetraibile
        dell'imposta (conto di costo con piano analitico obbligatorio)
        bloccherebbe la conferma. Lo storno non ha effetto economico, perciò
        viene escluso dal controllo."""
        return super(
            AccountMoveLine,
            self.filtered(lambda l: not l.move_id.iva_differita_origin_id),
        )._validate_analytic_distribution()
