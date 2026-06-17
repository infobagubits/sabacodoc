from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _sabaco_autofill_deferred_end_date_vals(self, vals):
        if vals.get('deferred_start_date') and not vals.get('deferred_end_date'):
            vals['deferred_end_date'] = vals['deferred_start_date']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sabaco_autofill_deferred_end_date_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get('deferred_start_date') and 'deferred_end_date' not in vals:
            if all(not line.deferred_end_date for line in self):
                vals['deferred_end_date'] = vals['deferred_start_date']
            else:
                lines_without_end = self.filtered(lambda line: not line.deferred_end_date)
                if lines_without_end:
                    super().write(vals)
                    for line in lines_without_end:
                        if line.deferred_start_date and not line.deferred_end_date:
                            super(AccountMoveLine, line).write({
                                'deferred_end_date': line.deferred_start_date,
                            })
                    return True
        return super().write(vals)

    @api.onchange('deferred_start_date')
    def _onchange_deferred_start_date(self):
        super()._onchange_deferred_start_date()
        if self.deferred_start_date and not self.deferred_end_date:
            self.deferred_end_date = self.deferred_start_date
