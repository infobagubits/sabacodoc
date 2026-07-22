# -*- coding: utf-8 -*-
"""Testes [BUG-002] — Mojibake dos acentos no PDF (correção definitiva).

Cobre:
- Override de ir.actions.report._build_wkhtmltopdf_args injeta '--encoding utf-8'.
- Idempotência: não duplica '--encoding' se já presente.
- report_date_label monta 'Dia(it) - DD/MM/AAAA' como str simples (sem Markup/entidade).
"""
import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBug002(TransactionCase):

    def setUp(self):
        super().setUp()
        self.report = self.env.ref('web.action_report_internalpreview', raise_if_not_found=False)
        if not self.report:
            # fallback: qualquer relatório qweb-pdf serve — o método independe do report
            self.report = self.env['ir.actions.report'].search(
                [('report_type', '=', 'qweb-pdf')], limit=1)
        self.paperformat = self.env.ref('base.paperformat_euro')

    # ---- override _build_wkhtmltopdf_args -------------------------------

    def test_encoding_injected(self):
        args = self.report._build_wkhtmltopdf_args(self.paperformat, False)
        self.assertIn('--encoding', args)
        idx = args.index('--encoding')
        self.assertEqual(args[idx + 1], 'utf-8',
                         "valor de --encoding deve ser utf-8")

    def test_encoding_at_front(self):
        # o override prependa ['--encoding','utf-8'] — deve vir antes dos args do core
        args = self.report._build_wkhtmltopdf_args(self.paperformat, False)
        self.assertEqual(args[0], '--encoding')
        self.assertEqual(args[1], 'utf-8')

    def test_encoding_not_duplicated(self):
        args = self.report._build_wkhtmltopdf_args(self.paperformat, False)
        self.assertEqual(args.count('--encoding'), 1,
                         "--encoding não pode ser duplicado")

    def test_super_chain_preserved(self):
        # os args base do core continuam presentes (não substituímos, só prependamos)
        args = self.report._build_wkhtmltopdf_args(self.paperformat, False)
        self.assertIn('--disable-local-file-access', args)
        self.assertIn('--quiet', args)

    # ---- report_date_label ---------------------------------------------

    def test_date_label_friday_accent(self):
        # 2026-07-17 é sexta-feira → "Venerdì"
        model = self.env['planning.slot']
        friday = datetime.date(2026, 7, 17)
        vals = model._sabaco_get_schedule_by_role_report_values(friday)
        label = vals['report_date_label']
        self.assertEqual(label, "Venerdì - 17/07/2026")

    def test_date_label_is_plain_str(self):
        model = self.env['planning.slot']
        friday = datetime.date(2026, 7, 17)
        label = model._sabaco_get_schedule_by_role_report_values(friday)['report_date_label']
        # tipo str puro — sem markupsafe.Markup e sem entidade HTML numérica
        self.assertEqual(type(label), str,
                         "report_date_label deve ser str simples (sem Markup)")
        self.assertNotIn('&#', label,
                         "não deve conter entidade HTML numérica (ex &#236;)")
        self.assertIn('ì', label,
                      "acento deve estar cru em UTF-8, não escapado")

    def test_date_label_zero_padded(self):
        model = self.env['planning.slot']
        # 2026-03-02 é segunda → "Lunedì - 02/03/2026" (zero-padded)
        monday = datetime.date(2026, 3, 2)
        label = model._sabaco_get_schedule_by_role_report_values(monday)['report_date_label']
        self.assertEqual(label, "Lunedì - 02/03/2026")
