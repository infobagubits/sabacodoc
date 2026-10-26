# -*- coding: utf-8 -*-
"""MELHORIA-027 — PDF fattura elettronica automatico sulle fatture di VENDITA.

Il PDF visivo deve nascere appena un XML/p7m di fattura elettronica viene
collegato a una fattura/nota di credito di vendita (ir.attachment create/write),
senza passare dal pulsante. Le fatture di acquisto non devono cambiare flusso.

Gira sul DB reale del cliente: TransactionCase sulla company corrente
(le basi del core che creano una nuova company danno AccessError).
"""
import base64
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_it_edi_pdf.models.account_move import AccountMove

# FatturaPA minima ma strutturalmente valida per il foglio XSL AssoSoftware.
XML_FE = b"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12"
    xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>01234567890</IdCodice></IdTrasmittente>
      <ProgressivoInvio>00001</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>0000000</CodiceDestinatario>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>01234567890</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>Sabaco d'oc Srl</Denominazione></Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
      <Sede><Indirizzo>Via Test 1</Indirizzo><CAP>12100</CAP><Comune>Cuneo</Comune><Provincia>CN</Provincia><Nazione>IT</Nazione></Sede>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <CodiceFiscale>RSSMRA80A01H501U</CodiceFiscale>
        <Anagrafica><Denominazione>Cliente Test</Denominazione></Anagrafica>
      </DatiAnagrafici>
      <Sede><Indirizzo>Via Cliente 2</Indirizzo><CAP>10100</CAP><Comune>Torino</Comune><Provincia>TO</Provincia><Nazione>IT</Nazione></Sede>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa>
        <Data>2026-01-15</Data><Numero>1/9999</Numero>
        <ImportoTotaleDocumento>122.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea><Descrizione>Riga test</Descrizione>
        <Quantita>1.00</Quantita><PrezzoUnitario>100.00</PrezzoUnitario>
        <PrezzoTotale>100.00</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>100.00</ImponibileImporto>
        <Imposta>22.00</Imposta><EsigibilitaIVA>I</EsigibilitaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>
"""


@tagged('post_install', '-at_install')
class TestEdiPdfVendite(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        recv = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'), ('deprecated', '=', False),
        ], limit=1)
        pay = cls.env['account.account'].search([
            ('account_type', '=', 'liability_payable'), ('deprecated', '=', False),
        ], limit=1)
        partner_vals = {'name': 'Cliente PDF FE Test'}
        if recv:
            partner_vals['property_account_receivable_id'] = recv.id
        if pay:
            partner_vals['property_account_payable_id'] = pay.id
        cls.partner = cls.env['res.partner'].create(partner_vals)
        cls.tax_sale = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'), ('amount', '>', 0), ('company_id', '=', company.id),
        ], limit=1)
        cls.tax_purchase = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'), ('amount', '>', 0), ('company_id', '=', company.id),
        ], limit=1)
        cls.product = cls.env['product.product'].search([
            ('property_account_income_id', '!=', False),
        ], limit=1) or cls.env['product.product'].create({'name': 'Prodotto Test', 'type': 'consu'})

    # ------------------------------------------------------------------ helpers
    def _invoice(self, move_type):
        tax = self.tax_sale if move_type.startswith('out_') else self.tax_purchase
        return self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner.id,
            'invoice_date': '2026-01-15',
            'invoice_line_ids': [(0, 0, {
                'name': 'Riga', 'quantity': 1, 'price_unit': 100.0,
                'product_id': self.product.id,
                'tax_ids': [(6, 0, tax.ids)] if tax else [(5, 0, 0)],
            })],
        })

    def _force_posted(self, move):
        """Evita il vincolo di sequenza del DB: forza lo stato in SQL."""
        self.env.cr.execute("UPDATE account_move SET state = 'posted' WHERE id = %s", (move.id,))
        move.invalidate_recordset(['state'])

    def _attach_xml(self, move, name='IT01234567890_00001.xml', raw=XML_FE, **extra):
        vals = {
            'name': name, 'raw': raw, 'res_model': 'account.move', 'res_id': move.id,
        }
        vals.update(extra)
        return self.env['ir.attachment'].create(vals)

    def _pdf_fe(self, move):
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'), ('res_id', '=', move.id),
            ('name', '=like', '%_fattura_elettronica.pdf'),
        ])

    def _assert_pdf(self, move, count=1):
        pdfs = self._pdf_fe(move)
        self.assertEqual(len(pdfs), count, pdfs.mapped('name'))
        for pdf in pdfs:
            self.assertEqual(pdf.mimetype, 'application/pdf')
            self.assertTrue(base64.b64decode(pdf.datas).startswith(b'%PDF'))
        return pdfs

    # ------------------------------------------------------------------ vendite
    def test_01_upload_diretto_out_invoice(self):
        """Casella allegati / API: create già collegata alla fattura → PDF subito."""
        move = self._invoice('out_invoice')
        self.assertFalse(self._pdf_fe(move))
        self._attach_xml(move)
        self._assert_pdf(move)

    def test_02_composer_chatter_ricollegamento(self):
        """Composer: nasce come mail.compose.message/0, poi write res_model/res_id → PDF."""
        move = self._invoice('out_invoice')
        att = self.env['ir.attachment'].create({
            'name': 'IT01234567890_00002.xml', 'raw': XML_FE,
            'res_model': 'mail.compose.message', 'res_id': 0,
        })
        self.assertFalse(self._pdf_fe(move))
        att.write({'res_model': 'account.move', 'res_id': move.id})
        self._assert_pdf(move)

    def test_03_out_refund(self):
        move = self._invoice('out_refund')
        self._attach_xml(move, name='IT01234567890_00003.xml')
        self._assert_pdf(move)

    def test_04_message_post_su_fattura_confermata(self):
        """Percorso reale del chatter su fattura confermata: il core annota
        'not a draft' e il PDF esiste comunque."""
        move = self._invoice('out_invoice')
        self._force_posted(move)
        att = self.env['ir.attachment'].create({
            'name': 'IT01234567890_00004.xml', 'raw': XML_FE,
            'res_model': 'mail.compose.message', 'res_id': 0,
        })
        move.message_post(body='XML fattura', attachment_ids=att.ids, message_type='comment')
        self.assertEqual(att.res_model, 'account.move')
        self.assertEqual(att.res_id, move.id)
        self._assert_pdf(move)

    def test_05_p7m_firmato_non_decodificabile_non_blocca(self):
        """Un .p7m con contenuto non valido non deve far fallire l'upload."""
        move = self._invoice('out_invoice')
        with self.assertLogs('odoo.addons.l10n_it_edi_pdf', level='WARNING'):
            att = self._attach_xml(move, name='IT01234567890_00005.xml.p7m', raw=b'\x30\x82garbage')
        self.assertTrue(att.exists())
        self.assertFalse(self._pdf_fe(move))

    def test_06_xml_invalido_non_blocca(self):
        move = self._invoice('out_invoice')
        with self.assertLogs('odoo.addons.l10n_it_edi_pdf', level='WARNING'):
            att = self._attach_xml(move, name='rotto.xml', raw=b'<FatturaElettronica><aperto>')
        self.assertTrue(att.exists())
        self.assertFalse(self._pdf_fe(move))

    def test_07_allegato_non_xml_ignorato(self):
        move = self._invoice('out_invoice')
        with patch.object(AccountMove, '_auto_generate_edi_pdf', autospec=True) as gen:
            self._attach_xml(move, name='scontrino.pdf', raw=b'%PDF-1.4 fake', mimetype='application/pdf')
            self._attach_xml(move, name='foto.png', raw=b'\x89PNG fake', mimetype='image/png')
            gen.assert_not_called()
        self.assertFalse(self._pdf_fe(move))

    def test_08_idempotente_secondo_xml(self):
        """Un secondo XML sulla stessa fattura sostituisce il PDF, non lo duplica."""
        move = self._invoice('out_invoice')
        self._attach_xml(move, name='IT01234567890_00008.xml')
        first = self._assert_pdf(move)
        first_name, first_id = first.name, first.id
        self._attach_xml(move, name='IT01234567890_00008b.xml')
        second = self._assert_pdf(move)
        self.assertEqual(first_name, second.name)
        self.assertNotEqual(first_id, second.id)
        self.assertFalse(first.exists())

    def test_09_lotto_piu_fatture_in_una_create(self):
        """Caricamento in lotto: una sola create con più allegati su fatture diverse."""
        m1, m2 = self._invoice('out_invoice'), self._invoice('out_refund')
        self.env['ir.attachment'].create([
            {'name': 'IT01234567890_00009a.xml', 'raw': XML_FE, 'res_model': 'account.move', 'res_id': m1.id},
            {'name': 'IT01234567890_00009b.xml', 'raw': XML_FE, 'res_model': 'account.move', 'res_id': m2.id},
        ])
        self._assert_pdf(m1)
        self._assert_pdf(m2)

    def test_10_contesto_skip(self):
        move = self._invoice('out_invoice')
        self.env['ir.attachment'].with_context(skip_edi_pdf_auto=True).create({
            'name': 'IT01234567890_00010.xml', 'raw': XML_FE,
            'res_model': 'account.move', 'res_id': move.id,
        })
        self.assertFalse(self._pdf_fe(move))

    def test_11_write_raw_non_rigenera(self):
        """Aggiornare il contenuto (es. XML firmato dopo lo SdI) non rigenera il PDF."""
        move = self._invoice('out_invoice')
        att = self._attach_xml(move, name='IT01234567890_00011.xml')
        pdf = self._assert_pdf(move)
        with patch.object(AccountMove, '_auto_generate_edi_pdf', autospec=True) as gen:
            att.write({'raw': XML_FE.replace(b'1/9999', b'1/9998')})
            gen.assert_not_called()
        self.assertEqual(self._pdf_fe(move), pdf)

    def test_12_pulsante_continua_a_funzionare(self):
        move = self._invoice('out_invoice')
        self._attach_xml(move, name='IT01234567890_00012.xml')
        self._assert_pdf(move)
        res = move.action_generate_edi_pdf()
        self.assertEqual(res['params']['type'], 'success')
        self._assert_pdf(move)

    # ------------------------------------------------------------------ acquisti (regressione)
    def test_20_in_invoice_non_passa_dal_hook_attachment(self):
        """Le fatture passive restano sul flusso di import: il nuovo hook non le tocca."""
        move = self._invoice('in_invoice')
        with patch.object(AccountMove, '_auto_generate_edi_pdf', autospec=True) as gen:
            self._attach_xml(move, name='ITFORNITORE_00020.xml')
            gen.assert_not_called()

    def test_21_in_invoice_flusso_esistente_invariato(self):
        """Con l'XML allegato, il flusso esistente (fallback su ir.attachment) genera ancora il PDF."""
        move = self._invoice('in_invoice')
        self._attach_xml(move, name='ITFORNITORE_00021.xml')
        self.assertFalse(self._pdf_fe(move))
        move._auto_generate_edi_pdf()
        self._assert_pdf(move)
