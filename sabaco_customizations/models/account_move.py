import base64
import logging
import re

from lxml import etree

from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.tools.misc import formatLang

try:
    from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature
except ImportError:
    remove_signature = None

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_xml_amount_total = fields.Monetary(
        string='Totale XML',
        compute='_compute_xml_total_mismatch_warning',
        currency_field='currency_id',
    )
    xml_total_mismatch_warning = fields.Char(
        string='Avviso totale XML',
        compute='_compute_xml_total_mismatch_warning',
    )

    def _sabaco_normalize_edi_xml(self, raw):
        """Normalizza contenuto grezzo in bytes XML (gestisce file .p7m firmati)."""
        if not raw:
            return None
        if raw.strip().startswith(b'<'):
            return raw
        if remove_signature is not None:
            try:
                unwrapped = remove_signature(raw)
            except Exception as e:
                _logger.warning(
                    "Rimozione firma .p7m fallita (account.move id=%s): %s", self.id, e,
                )
                unwrapped = None
            if unwrapped and unwrapped.strip().startswith(b'<'):
                return unwrapped
        return None

    def _sabaco_decode_attachment_bytes(self, attachment):
        """Legge i bytes di un ir.attachment (filestore o db_datas)."""
        if not attachment:
            return None
        raw = attachment.raw
        if raw:
            return raw
        if attachment.datas:
            try:
                return base64.b64decode(attachment.datas)
            except Exception:
                return None
        return None

    def _sabaco_xml_from_attachment_record(self, attachment):
        raw = self._sabaco_decode_attachment_bytes(attachment)
        if not raw:
            return None
        return self._sabaco_normalize_edi_xml(raw)

    def _sabaco_get_edi_xml_bytes(self):
        """
        Restituisce i bytes XML della fattura elettronica collegata alla registrazione.

        Strategia (in ordine):
          1. l10n_it_edi_attachment_id / l10n_it_edi_attachment_file (standard l10n_it_edi)
          2. ir.attachment collegati alla fattura (.xml / .p7m), inclusi quelli postati
             nel chatter all'importazione (res_field vuoto — caso restore/cassetto fiscale)
        """
        self.ensure_one()

        att = self.l10n_it_edi_attachment_id
        xml = self._sabaco_xml_from_attachment_record(att)
        if xml:
            return xml

        xml_file = self.l10n_it_edi_attachment_file
        if xml_file:
            try:
                raw = base64.b64decode(xml_file)
            except Exception:
                raw = xml_file if isinstance(xml_file, bytes) else xml_file.encode('utf-8')
            xml = self._sabaco_normalize_edi_xml(raw)
            if xml:
                return xml

        Attachment = self.env['ir.attachment'].sudo()
        base_domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            '|', ('name', 'ilike', '.xml'), ('name', 'ilike', '.p7m'),
        ]
        # Allegati EDI sul campo Binary (esclusi dalla search standard)
        atts = Attachment.search(
            base_domain + [('res_field', '=', 'l10n_it_edi_attachment_file')],
            order='id desc',
        )
        # Allegati generici sul chatter (caso restore: XML senza res_field)
        atts |= Attachment.search(
            base_domain + [('res_field', '=', False)],
            order='id desc',
        )
        for attachment in atts:
            xml = self._sabaco_xml_from_attachment_record(attachment)
            if xml:
                return xml

        return None

    def _sabaco_get_xml_payment_total_from_chatter(self):
        """
        Fallback: legge il totale XML dal messaggio postato da l10n_it_edi all'import.
        Utile se l'XML è nel chatter ma il filestore non è disponibile (restore parziale).
        """
        self.ensure_one()
        messages = self.env['mail.message'].search([
            ('model', '=', 'account.move'),
            ('res_id', '=', self.id),
            '|',
            ('body', 'ilike', 'Valore totale dal file XML'),
            ('body', 'ilike', 'Total amount from the XML File'),
        ], order='id desc', limit=1)
        if not messages:
            return None

        text = re.sub(r'<[^>]+>', '', messages.body or '')
        match = re.search(
            r'(?:Valore totale dal file XML|Total amount from the XML File)\s*:\s*([\d.,]+)',
            text,
            re.IGNORECASE,
        )
        if not match:
            return None

        raw_value = match.group(1).strip()
        if ',' in raw_value and '.' in raw_value:
            normalized = raw_value.replace('.', '').replace(',', '.')
        elif ',' in raw_value:
            normalized = raw_value.replace(',', '.')
        else:
            normalized = raw_value

        try:
            return float(normalized)
        except ValueError:
            return None

    def _sabaco_get_xml_payment_total(self):
        """
        Totale XML: prima da ImportoPagamento nel file EDI, poi fallback chatter.
        """
        self.ensure_one()
        xml_bytes = self._sabaco_get_edi_xml_bytes()
        if xml_bytes:
            try:
                tree = etree.fromstring(xml_bytes)
                amounts = [
                    float(el.text.strip())
                    for el in tree.xpath('.//ImportoPagamento')
                    if el.text and el.text.strip()
                ]
                if amounts:
                    return sum(amounts)
            except etree.XMLSyntaxError as e:
                _logger.warning(
                    "XML EDI non valido per account.move id=%s: %s", self.id, e,
                )

        return self._sabaco_get_xml_payment_total_from_chatter()

    @api.depends(
        'amount_total',
        'currency_id',
        'move_type',
        'l10n_it_edi_attachment_file',
        'l10n_it_edi_attachment_id',
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.tax_ids',
    )
    def _compute_xml_total_mismatch_warning(self):
        for move in self:
            move.l10n_it_xml_amount_total = 0.0
            move.xml_total_mismatch_warning = False

            if move.move_type not in ('in_invoice', 'in_refund'):
                continue

            xml_total = move._sabaco_get_xml_payment_total()
            if xml_total is None:
                continue

            move.l10n_it_xml_amount_total = xml_total

            if float_compare(
                move.amount_total,
                xml_total,
                precision_rounding=move.currency_id.rounding,
            ) != 0:
                invoice_total_fmt = formatLang(
                    move.env, move.amount_total, currency_obj=move.currency_id,
                )
                xml_total_fmt = formatLang(
                    move.env, xml_total, currency_obj=move.currency_id,
                )
                move.xml_total_mismatch_warning = _(
                    "Attenzione: il totale fattura (%(invoice_total)s) differisce dal "
                    "valore totale dal file XML (%(xml_total)s)."
                ) % {
                    'invoice_total': invoice_total_fmt,
                    'xml_total': xml_total_fmt,
                }
