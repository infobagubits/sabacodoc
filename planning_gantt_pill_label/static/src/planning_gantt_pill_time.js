/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";

/*
 * pill_label nativo mostra l'orario sulle barre SOLO nelle scale "week" e
 * "month". Nella scala "day" (zoom con le ore come colonne) gli orari non
 * vengono mai scritti. Questo patch aggiunge "HH:mm - HH:mm" all'etichetta
 * della pill quando la scala attiva e' "day".
 */
patch(PlanningGanttRenderer.prototype, {
    getDisplayName(pill) {
        // Recupera l'etichetta standard (nome del turno, ecc.).
        const baseName =
            typeof super.getDisplayName === "function"
                ? super.getDisplayName(pill)
                : pill.displayName || "";

        const md = this.model.metaData;
        const scaleId = md.scale && md.scale.id;
        if (scaleId !== "day") {
            return baseName;
        }

        const start = pill.record[md.dateStartField];
        const stop = pill.record[md.dateStopField];
        if (!start || !stop) {
            return baseName;
        }

        const fmt = "HH:mm"; // usa "h:mm a" se preferisci il formato 12h
        const times = `${start.toFormat(fmt)} - ${stop.toFormat(fmt)}`;

        return baseName ? `${times} · ${baseName}` : times;
    },
});
