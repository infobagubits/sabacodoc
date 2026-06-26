/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { useEffect } from "@odoo/owl";

patch(GanttRenderer.prototype, {
    setup() {
        super.setup();
        // A ogni render marca il contenitore del gantt con una classe
        // quando la scala attiva e' "day". Il CSS usa questa classe per
        // nascondere i totali di gruppo SOLO in scala giorno.
        useEffect(() => {
            const md = this.model.metaData;
            const isDay = !!(md.scale && md.scale.id === "day");
            const roots = document.querySelectorAll(
                ".o_gantt_renderer, .o_gantt_view"
            );
            for (const root of roots) {
                root.classList.toggle("o_pill_hide_group_totals", isDay);
            }
        });
    },

    enrichPill(pill) {
        const result = super.enrichPill(pill);
        const md = this.model.metaData;
        const scaleId = md.scale && md.scale.id;
        if (scaleId === "day") {
            const start = pill.record[md.dateStartField];
            const stop = pill.record[md.dateStopField];
            if (start && stop && start.toFormat) {
                const times = `${start.toFormat("HH:mm")} - ${stop.toFormat("HH:mm")}`;
                if (result) {
                    const base = (result.displayName || "").toString();
                    result.displayName = base && !base.includes(times) ? `${times} · ${base}` : times;
                }
                if ("displayName" in pill) {
                    const base2 = (pill.displayName || "").toString();;
                    pill.displayName = base2 && !base2.includes(times) ? `${times} · ${base2}` : times;
                }
            }
        }
        return result;
    },
});
