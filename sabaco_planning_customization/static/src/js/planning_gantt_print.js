/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PlanningGanttController } from "@planning/views/planning_gantt/planning_gantt_controller";

patch(PlanningGanttController.prototype, {
    get sabacoShowSchedulePrint() {
        const groupByRole = Boolean(this.model.searchParams.context?.planning_groupby_role);
        const { startDate, stopDate } = this.model.metaData;
        if (!groupByRole || !startDate || !stopDate) {
            return false;
        }
        // Intervallo visibile in giorni (1 = giorno singolo, 7 = settimana). Il report
        // stampa al massimo 7 giorni; oltre (mese/anno) il pulsante resta nascosto.
        const days = stopDate.startOf("day").diff(startDate.startOf("day"), "days").days + 1;
        return days >= 1 && days <= 7;
    },

    async sabacoPrintScheduleByRole() {
        const { startDate, stopDate } = this.model.metaData;
        const action = await this.orm.call(
            "planning.schedule.print.wizard",
            "action_print_pdf_from_gantt",
            [startDate.toISODate(), stopDate.toISODate()],
        );
        await this.actionService.doAction(action);
    },
});
