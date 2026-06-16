from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _sabaco_linked_account_moves(self):
        moves = self.env['account.move']
        for attachment in self:
            if attachment.res_model != 'account.move' or not attachment.res_id:
                continue
            name = (attachment.name or '').lower()
            if not (name.endswith('.xml') or name.endswith('.p7m')):
                continue
            moves |= self.env['account.move'].browse(attachment.res_id)
        return moves

    def _sabaco_invalidate_xml_total_warning(self):
        moves = self._sabaco_linked_account_moves()
        if moves:
            moves.invalidate_recordset([
                'xml_total_mismatch_warning',
                'l10n_it_xml_amount_total',
            ])

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        attachments._sabaco_invalidate_xml_total_warning()
        return attachments

    def write(self, vals):
        res = super().write(vals)
        self._sabaco_invalidate_xml_total_warning()
        return res

    def unlink(self):
        moves = self._sabaco_linked_account_moves()
        res = super().unlink()
        if moves:
            moves.invalidate_recordset([
                'xml_total_mismatch_warning',
                'l10n_it_xml_amount_total',
            ])
        return res
