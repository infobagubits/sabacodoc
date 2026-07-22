/** @odoo-module **/

// Previene la duplicazione di conti analitici nello stesso piano nella distribuzione analitica.
// Il campo `analytic_distribution` è un JSON {account_id: percentuale}: chiavi duplicate
// vengono silenziosamente deduplicate dal browser prima di arrivare al server, causando
// perdita di dati senza alcun avviso. Questo patch blocca la chiusura del popup se
// viene rilevato un duplicato, mostrando una notifica di errore.

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";

patch(AnalyticDistribution.prototype, {
    // Inietta il servizio di notifica durante il setup del componente
    setup() {
        super.setup();
        this._sabacoNotification = useService("notification");
    },

    // Verifica se esiste un conto analitico duplicato nello stesso piano
    // Ritorna true se lo stesso accountId appare in due righe dello stesso planId
    _sabacoDuplicateExists() {
        const seen = {};
        for (const line of this.state.formattedData) {
            for (const acc of line.analyticAccounts) {
                if (!acc.accountId) {
                    continue;
                }
                const planId = acc.planId;
                if (!seen[planId]) {
                    seen[planId] = new Set();
                }
                if (seen[planId].has(acc.accountId)) {
                    return true;
                }
                seen[planId].add(acc.accountId);
            }
        }
        return false;
    },

    // Blocca la chiusura dell'editor analitico se esistono duplicati
    closeAnalyticEditor() {
        if (this._sabacoDuplicateExists()) {
            this._sabacoNotification.add(
                _t("Conto analitico duplicato: ogni conto può apparire una sola volta per piano."),
                { type: "danger" }
            );
            return;
        }
        super.closeAnalyticEditor();
    },
});
