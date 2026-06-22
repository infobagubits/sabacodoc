/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PlanningGanttController } from "@planning/views/planning_gantt/planning_gantt_controller";

patch(PlanningGanttController.prototype, {
    get sabacoShowSchedulePrint() {
        const groupByRole = Boolean(this.model.searchParams.context?.planning_groupby_role);
        const { startDate, stopDate } = this.model.metaData;
        const isSingleDay = startDate && stopDate && startDate.hasSame(stopDate, "day");
        return groupByRole && isSingleDay;
    },

    async sabacoPrintScheduleByRole() {
        const focusDate = this.getCurrentFocusDate();
        const action = await this.orm.call(
            "planning.schedule.print.wizard",
            "action_print_pdf_from_gantt",
            [focusDate.toISODate()],
        );
        await this.actionService.doAction(action);
    },
});
