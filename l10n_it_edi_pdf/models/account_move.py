import base64
import logging
import os
import subprocess
import tempfile

import lxml.etree as ET

from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        res = super().write(vals)
        trigger_file = 'l10n_it_edi_attachment_file' in vals
        trigger_name = 'l10n_it_edi_attachment_name' in vals
        if trigger_file or trigger_name:
            for move in self:
                # Fatture vendita: reagire solo a l10n_it_edi_attachment_name
                # Fatture acquisto: reagire solo a l10n_it_edi_attachment_file
                if move.move_type in ('out_invoice', 'out_refund') and not trigger_name:
                    continue
                if move.move_type in ('in_invoice', 'in_refund') and not trigger_file:
                    continue
                try:
                    move._auto_generate_edi_pdf()
                except Exception as e:
                    _logger.warning(
                        "Generazione automatica PDF EDI fallita per account.move id=%s: %s",
                        move.id, e,
                    )
        return res

    @api.model
    def _get_xsl_path(self):
        """Ritorna il path assoluto del foglio XSL incluso nel modulo."""
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(module_path, 'data', 'FoglioStileAssoSoftware.xsl')

    def _xml_to_html(self, xml_bytes):
        """Trasforma l'XML in HTML usando il foglio XSLT di AssoSoftware."""
        xsl_path = self._get_xsl_path()
        if not os.path.exists(xsl_path):
            raise UserError(_(
                "Foglio XSL non trovato: %(path)s\n"
                "Assicurati che 'FoglioStileAssoSoftware.xsl' sia nella "
                "cartella 'data' del modulo.",
                path=xsl_path,
            ))
        try:
            dom = ET.fromstring(xml_bytes)
            xslt = ET.parse(xsl_path)
            transform = ET.XSLT(xslt)
            newdom = transform(dom)
            return ET.tostring(newdom, pretty_print=True).decode('utf-8')
        except ET.XSLTError as e:
            raise UserError(_("Errore nella trasformazione XSLT: %(error)s", error=str(e)))
        except ET.XMLSyntaxError as e:
            raise UserError(_("XML della fattura non valido: %(error)s", error=str(e)))

    def _html_to_pdf(self, html_content):
        """Converte HTML in PDF. Ritorna i bytes del PDF."""
        tmp_html = None
        tmp_pdf = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix='.html', mode='w', encoding='utf-8', delete=False
            ) as f:
                f.write(html_content)
                tmp_html = f.name
            tmp_pdf = tmp_html.replace('.html', '.pdf')

            # Tentativo 1: metodo interno Odoo
            IrReport = self.env['ir.actions.report']
            if hasattr(IrReport, '_run_wkhtmltopdf'):
                try:
                    pdf_bytes = IrReport._run_wkhtmltopdf(
                        [tmp_html],
                        header_b64=None,
                        footer_b64=None,
                        landscape=False,
                        specific_paperformat_args=None,
                        set_viewport_size=False,
                    )
                    if pdf_bytes:
                        return pdf_bytes
                except Exception as e:
                    _logger.warning("_run_wkhtmltopdf non utilizzabile (%s), uso subprocess.", e)

            # Tentativo 2: subprocess diretto
            wkhtmltopdf_bin = self._find_wkhtmltopdf()
            result = subprocess.run(
                [wkhtmltopdf_bin, '--encoding', 'utf-8',
                 '--enable-local-file-access', '--quiet', tmp_html, tmp_pdf],
                capture_output=True, timeout=60,
            )
            if result.returncode != 0:
                raise UserError(_(
                    "wkhtmltopdf ha restituito un errore:\n%(stderr)s",
                    stderr=result.stderr.decode('utf-8', errors='replace'),
                ))
            with open(tmp_pdf, 'rb') as f:
                return f.read()
        finally:
            if tmp_html and os.path.exists(tmp_html):
                os.unlink(tmp_html)
            if tmp_pdf and os.path.exists(tmp_pdf):
                os.unlink(tmp_pdf)

    @api.model
    def _find_wkhtmltopdf(self):
        """Cerca il binario wkhtmltopdf nel sistema."""
        for path in ['/usr/local/bin/wkhtmltopdf', '/usr/bin/wkhtmltopdf',
                     '/usr/local/lib/wkhtmltopdf', 'wkhtmltopdf']:
            try:
                r = subprocess.run([path, '--version'], capture_output=True, timeout=5)
                if r.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        raise UserError(_(
            "wkhtmltopdf non trovato nel sistema.\n"
            "Su Odoo.sh dovrebbe essere gia' installato."
        ))

    def _get_edi_xml_bytes(self):
        """
        Restituisce i bytes dell'XML della fattura elettronica.

        Strategia (in ordine di priorità):
          1. l10n_it_edi_attachment_id  → Many2one diretto a ir.attachment
          2. l10n_it_edi_attachment_file → campo Binary (attive e passive)
          3. Cerca ir.attachment per l10n_it_edi_attachment_name (fatture attive)
          4. Fallback: qualsiasi ir.attachment .xml collegato alla fattura
        """
        self.ensure_one()

        # 1. Tentativo diretto tramite Many2one l10n_it_edi_attachment_id
        att = getattr(self, 'l10n_it_edi_attachment_id', None)
        if att and att.datas:
            _logger.info(
                "XML trovato via l10n_it_edi_attachment_id: %s (account.move id=%s)",
                att.name, self.id,
            )
            return base64.b64decode(att.datas)

        # 2. Tentativo tramite campo Binary l10n_it_edi_attachment_file
        xml_file = getattr(self, 'l10n_it_edi_attachment_file', None)
        if xml_file:
            try:
                raw = base64.b64decode(xml_file)
            except Exception:
                raw = xml_file if isinstance(xml_file, bytes) else xml_file.encode('utf-8')
            if raw.strip().startswith(b'<'):
                _logger.info("XML trovato via l10n_it_edi_attachment_file (id=%s)", self.id)
                return raw

        # 3. Per fatture attive: cerca ir.attachment tramite nome
        if self.move_type in ('out_invoice', 'out_refund'):
            xml_name = getattr(self, 'l10n_it_edi_attachment_name', None)
            if xml_name:
                att = self.env['ir.attachment'].search([
                    ('name', '=', xml_name),
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', self.id),
                ], limit=1)
                if not att:
                    att = self.env['ir.attachment'].search([
                        ('name', '=', xml_name),
                    ], limit=1, order='id desc')
                if att and att.datas:
                    _logger.info("XML attivo trovato via l10n_it_edi_attachment_name: %s", xml_name)
                    return base64.b64decode(att.datas)

        # 4. Fallback: qualsiasi ir.attachment .xml sulla fattura
        att = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('name', 'ilike', '.xml'),
        ], limit=1, order='id desc')
        if att and att.datas:
            raw = base64.b64decode(att.datas)
            if raw.strip().startswith(b'<'):
                _logger.info("XML trovato via ir.attachment su account.move: %s", att.name)
                return raw

        _logger.warning(
            "Nessun XML EDI trovato per account.move id=%s (move_type=%s). "
            "Allegati presenti: %s",
            self.id, self.move_type,
            self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
            ]).mapped('name'),
        )
        return None

    def _generate_and_attach_edi_pdf(self):
        """
        Logica core: genera il PDF dall'XML EDI e lo allega alla fattura.
        Ritorna il nome del file PDF generato, oppure None se non disponibile.
        Non solleva UserError (usato sia dal pulsante che dall'automatismo).
        """
        self.ensure_one()

        xml_bytes = self._get_edi_xml_bytes()
        if not xml_bytes:
            return None

        html_content = self._xml_to_html(xml_bytes)
        pdf_bytes = self._html_to_pdf(html_content)

        # Nome file
        if self.move_type in ('out_invoice', 'out_refund'):
            xml_name = getattr(self, 'l10n_it_edi_attachment_name', None)
            if xml_name:
                pdf_filename = os.path.splitext(xml_name)[0] + '_visualizzazione.pdf'
            else:
                safe_name = (self.name or 'fattura').replace('/', '_').replace(' ', '_')
                pdf_filename = safe_name + '_fattura_elettronica.pdf'
        else:
            ref = self.ref or self.name or 'fattura_passiva'
            safe_name = ref.replace('/', '_').replace(' ', '_').replace('\\', '_')
            pdf_filename = safe_name + '_fattura_elettronica.pdf'

        # Rimuovi eventuale PDF precedente con lo stesso nome
        self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('name', '=', pdf_filename),
        ]).unlink()

        # Salva il nuovo PDF come allegato
        self.env['ir.attachment'].create({
            'name': pdf_filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_bytes),
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/pdf',
            'description': "PDF visivo generato dall'XML della fattura elettronica",
        })

        _logger.info("PDF FE generato: %s (account.move id=%s)", pdf_filename, self.id)
        return pdf_filename

    def _auto_generate_edi_pdf(self):
        """Genera automaticamente il PDF EDI se l'XML è disponibile (nessun errore UI)."""
        self.ensure_one()
        pdf_filename = self._generate_and_attach_edi_pdf()
        if pdf_filename:
            _logger.info(
                "PDF EDI generato automaticamente: %s (account.move id=%s)",
                pdf_filename, self.id,
            )
        else:
            _logger.info(
                "Generazione automatica PDF EDI saltata: XML non disponibile (account.move id=%s)",
                self.id,
            )

    def action_generate_edi_pdf(self):
        """
        Genera il PDF ufficiale della fattura elettronica dall'XML EDI
        e lo salva come allegato sulla fattura.
        Funziona per fatture attive e passive.
        """
        self.ensure_one()

        pdf_filename = self._generate_and_attach_edi_pdf()
        if not pdf_filename:
            raise UserError(_(
                "Impossibile ottenere l'XML della fattura elettronica.\n\n"
                "Per le fatture attive: verifica che la fattura sia stata inviata allo SdI.\n"
                "Per le fatture passive: verifica che l'XML sia stato importato."
            ))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('PDF Generato'),
                'message': _(
                    'Il PDF e\' stato salvato negli allegati come "%(filename)s".',
                    filename=pdf_filename,
                ),
                'type': 'success',
                'sticky': False,
            }
        }
