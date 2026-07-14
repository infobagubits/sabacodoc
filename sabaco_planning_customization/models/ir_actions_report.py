# -*- coding: utf-8 -*-
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, *args, **kwargs):
        """Força a codificação UTF-8 na chamada do wkhtmltopdf.

        O Odoo sempre grava os arquivos HTML temporários em UTF-8, mas alguns
        builds do wkhtmltopdf ignoram o `<meta charset="utf-8"/>` do documento e
        assumem latin-1, corrompendo acentos (ex.: "Venerdì" → "VenerdÃ¬") nos
        relatórios PDF. Passar `--encoding utf-8` explicitamente elimina essa
        ambiguidade. Vale para todos os relatórios — é a codificação correta que
        o Odoo já produz. Ver [BUG-002].
        """
        command_args = super()._build_wkhtmltopdf_args(*args, **kwargs)
        if '--encoding' not in command_args:
            command_args = ['--encoding', 'utf-8'] + command_args
        return command_args
