import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Tipi di documento per cui l'arrivo di un XML/p7m di fattura elettronica
# come allegato genera automaticamente il PDF visivo.
# Le fatture passive (in_invoice/in_refund) restano sul flusso di import
# (_extend_with_attachments in account_move.py) e NON passano da qui.
EDI_PDF_TRIGGER_TYPES = ('out_invoice', 'out_refund')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _edi_pdf_is_xml_like(self):
        """True se l'allegato sembra un XML di fattura elettronica (anche firmato .p7m)."""
        self.ensure_one()
        name = (self.name or '').lower()
        mimetype = (self.mimetype or '').lower()
        return (
            name.endswith('.xml') or name.endswith('.p7m')
            or 'xml' in mimetype or 'pkcs7' in mimetype
        )

    def _edi_pdf_candidate_moves(self):
        """Fatture di vendita a cui è appena stato collegato un XML/p7m.

        Filtro volutamente economico (solo campi già in cache) prima di qualsiasi
        browse: create/write di ir.attachment sono percorsi caldi.
        """
        move_ids = set()
        for attachment in self:
            if attachment.res_model != 'account.move' or not attachment.res_id:
                continue
            if not attachment._edi_pdf_is_xml_like():
                continue
            move_ids.add(attachment.res_id)
        if not move_ids:
            return self.env['account.move']
        moves = self.env['account.move'].browse(sorted(move_ids)).exists()
        return moves.filtered(lambda m: m.move_type in EDI_PDF_TRIGGER_TYPES)

    def _edi_pdf_auto_generate(self):
        """Genera il PDF visivo sulle fatture di vendita collegate. Mai bloccante."""
        if self.env.context.get('skip_edi_pdf_auto'):
            return
        for move in self._edi_pdf_candidate_moves():
            try:
                move.with_context(skip_edi_pdf_auto=True)._auto_generate_edi_pdf()
            except Exception as e:  # noqa: BLE001 - l'upload dell'XML non deve mai fallire
                _logger.warning(
                    "Generazione automatica PDF EDI fallita (vendita) per account.move id=%s: %s",
                    move.id, e,
                )

    @api.model_create_multi
    def create(self, vals_list):
        # Copre: caricamento dalla casella allegati, Documenti, API, import e
        # l'invio allo SdI (res_field='l10n_it_edi_attachment_file').
        attachments = super().create(vals_list)
        attachments._edi_pdf_auto_generate()
        return attachments

    def write(self, vals):
        # Copre il composer del chatter: l'allegato nasce come
        # mail.compose.message/res_id=0 e viene ricollegato alla fattura con un
        # write su res_model/res_id (mail.thread._message_post_process_attachments).
        # Aggiornamenti di raw/name (es. XML firmato dopo lo SdI) non rigenerano.
        res = super().write(vals)
        if 'res_model' in vals or 'res_id' in vals:
            self._edi_pdf_auto_generate()
        return res
