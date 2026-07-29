import datetime
from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = "account.asset"

    # Aggiunge 'percentage' alle opzioni esistenti senza riscrivere l'intera selection.
    # ondelete: se il modulo viene disinstallato, i cespiti con questo metodo
    # tornano al valore di default ('linear').
    method = fields.Selection(
        selection_add=[('percentage', 'Percentuale Fiscale IT')],
        ondelete={'percentage': 'set default'},
    )

    # Scala 0-1 (coerente con widget="percentage" di Odoo 18 e con method_progress_factor).
    # Esempio: 20% → 0.2.
    method_percentage = fields.Float(
        string="Percentuale annua (%)",
        default=0.2,
        help=(
            "Percentuale annua di ammortamento (regola art. 102 TUIR):\n"
            "• Anno 1: 50% della percentuale indicata\n"
            "• Anni successivi: percentuale intera\n"
            "• Anno finale extra: il restante 50% del primo anno\n"
            "• Eccezione: se il conto cespite inizia per 03, l'anno 1 usa la "
            "percentuale intera (nessun dimezzamento)\n"
            "Inserire il valore come percentuale (es. 20 per 20%)."
        ),
    )

    # ------------------------------------------------------------------
    # Validazione
    # ------------------------------------------------------------------

    @api.constrains('method', 'method_percentage')
    def _check_method_percentage(self):
        for asset in self:
            if asset.method == 'percentage':
                if not (0.0 < asset.method_percentage <= 1.0):
                    raise ValidationError(
                        _("La percentuale annua deve essere compresa tra 0 (escluso) e 100.")
                    )

    # ------------------------------------------------------------------
    # Onchange — reset del piano quando la percentuale cambia
    # ------------------------------------------------------------------

    @api.onchange('method_percentage')
    def _onchange_method_percentage(self):
        """
        Cancella le righe in bozza quando la percentuale cambia,
        coerentemente con onchange_consistent_board del modulo standard.
        """
        if self.method == 'percentage':
            self.write({'depreciation_move_ids': [Command.set([])]})

    # ------------------------------------------------------------------
    # Calcolo del piano di ammortamento
    # ------------------------------------------------------------------

    def _get_percentage_schedule(self):
        """
        Restituisce la lista degli importi annuali secondo la regola fiscale italiana.

        Regola generale (art. 102 TUIR):
          - Anno 1  : base × (rate / 2)
          - Anno 2..N : base × rate   (finché il residuo è ≥ importo pieno)
          - Anno N+1 : residuo (pari a base × rate / 2)

        Eccezione — conto cespite che inizia per 03:
          l'anno 1 usa la rata piena (base × rate), senza dimezzamento. Il piano
          prosegue negli anni successivi fino a esaurire la base.

        La base è total_depreciable_value (original_value - salvage_value).

        Esempio con base 9.000 € e rate 20%:
          Anno 1 →    900 € (10%)
          Anno 2 →  1.800 € (20%)
          ...
          Anno 6 →    900 € (10% residuo)
          Totale  → 9.000 € in 6 anni

        Stesso esempio con conto cespite 03xxxx:
          Anno 1..5 → 1.800 € (20%) — totale 9.000 € in 5 anni
        """
        self.ensure_one()

        base = self.total_depreciable_value
        if not base or not self.method_percentage:
            return []

        # method_percentage è in scala 0-1 (widget percentage di Odoo 18)
        annual_amount = round(base * self.method_percentage, 2)

        # Conti cespite che iniziano per 03: rata piena già dal primo anno.
        conto_cespite = self.account_asset_id.code or ''
        if conto_cespite.startswith('03'):
            first_year_amount = annual_amount
        else:
            # art. 102 TUIR: 50% nel primo anno
            first_year_amount = round(annual_amount / 2.0, 2)

        schedule = []
        remaining = base
        year_idx = 0

        while remaining > 0.005:
            year_idx += 1

            if year_idx == 1:
                amount = first_year_amount
            else:
                amount = annual_amount

            # Ultima rata: non superare mai il residuo
            if amount >= remaining - 0.005:
                amount = round(remaining, 2)

            schedule.append(round(amount, 2))
            remaining = round(remaining - amount, 2)

        return schedule

    # ------------------------------------------------------------------
    # Override compute_depreciation_board (allineato a Odoo 18)
    # ------------------------------------------------------------------

    def compute_depreciation_board(self, date=False):
        """
        Per i cespiti con metodo 'percentage' usa la logica personalizzata;
        per tutti gli altri delega al metodo standard di Odoo 18.
        """
        percentage_assets = self.filtered(lambda a: a.method == 'percentage')
        other_assets = self - percentage_assets

        if other_assets:
            super(AccountAsset, other_assets).compute_depreciation_board(date)

        for asset in percentage_assets:
            asset._compute_percentage_board(date)

    def _compute_percentage_board(self, date=False):
        """
        Genera le mosse di ammortamento per il metodo percentuale fiscale.

        Strategia (allineata a compute_depreciation_board di Odoo 18):
        1. Le mosse già registrate (state='posted') vengono conservate.
        2. Le mosse in bozza (state='draft') con data >= date vengono cancellate e rigenerate.
        3. Il piano viene calcolato sulla base depreciable totale; le prime N rate
           (corrispondenti alle N mosse già registrate) vengono saltate.
        4. I movimenti con data nel passato (cespite 'open') vengono postati
           automaticamente, coerentemente con il flusso standard di Odoo 18.
        """
        self.ensure_one()

        # Cancella solo le bozze successive alla data di taglio
        drafts = self.depreciation_move_ids.filtered(
            lambda m: m.state == 'draft' and (m.date >= date if date else True)
        )
        drafts.unlink()

        posted_moves = self.depreciation_move_ids.filtered(
            lambda m: m.state == 'posted'
        ).sorted('date')

        schedule = self._get_percentage_schedule()
        if not schedule:
            _logger.warning(
                "Cespite %s (id=%s): piano di ammortamento vuoto "
                "(verificare valore depreciable e percentuale).",
                self.name, self.id
            )
            return

        start_date = self.acquisition_date or fields.Date.today()
        n_posted = len(posted_moves)

        move_vals_list = []
        for i, amount in enumerate(schedule):
            if i < n_posted:
                continue

            year = start_date.year + i

            # Data fine anno fiscale (31/12) — regola TUIR
            dep_date = datetime.date(year, 12, 31)

            # Inizio del periodo: primo gennaio dell'anno (o acquisition_date se anno di acquisto)
            if i == 0:
                dep_beginning_date = start_date
            else:
                dep_beginning_date = datetime.date(year, 1, 1)

            days_in_period = (dep_date - dep_beginning_date).days + 1

            move_vals_list.append(
                self.env['account.move']._prepare_move_for_asset_depreciation({
                    'amount': amount,
                    'asset_id': self,
                    'depreciation_beginning_date': dep_beginning_date,
                    'date': dep_date,
                    'asset_number_days': days_in_period,
                    'asset_move_type': 'depreciation',
                })
            )

        if move_vals_list:
            new_moves = self.env['account.move'].create(move_vals_list)
            # Posta automaticamente i movimenti passati per i cespiti in esercizio,
            # coerentemente con il comportamento standard di Odoo 18.
            if self.state == 'open':
                new_moves._post()
