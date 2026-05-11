/** @odoo-module **/

/**
 * 1) multi_edit sul one2many: archInfo.multiEdit senza allowSelectors → niente checkbox.
 * 2) Con allowSelectors, ListRenderer usa list.selection.length ma StaticList non espone
 *    selection né toggleSelection → OwlError alla bacheca / ovunque si apra quella lista.
 * 3) Nel form account.move il modello non ha multiEdit e Record non ha _multiSave: la modifica
 *    non si propaga alle righe selezionate. Si forza multiEdit sul RelationalModel e si
 *    implementa _multiSave sulla registrazione (come DynamicList).
 */
import { toRaw } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { unique } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { Record } from "@web/model/relational_model/record";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { StaticList } from "@web/model/relational_model/static_list";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

patch(X2ManyField.prototype, {
    get rendererProps() {
        const props = super.rendererProps;
        if (this.props.viewMode === "list" && this.archInfo.multiEdit) {
            props.allowSelectors = true;
        }
        return props;
    },
});

patch(StaticList.prototype, {
    get selection() {
        return this.records.filter((record) => record.selected);
    },
    toggleSelection() {
        return this.model.mutex.exec(() => this._toggleSelection());
    },
    async _toggleSelection() {
        if (this.selection.length === this.records.length) {
            for (const record of this.records) {
                record._toggleSelection(false);
            }
        } else {
            for (const record of this.records) {
                record._toggleSelection(true);
            }
        }
    },
});

patch(RelationalModel.prototype, {
    setup(params, services) {
        super.setup(params, services);
        if (params.config?.isMonoRecord && params.config?.resModel === "account.move") {
            this.multiEdit = true;
        }
    },
});

patch(Record.prototype, {
    async _multiSave(lineRecord) {
        if (this.resModel !== "account.move" || lineRecord.resModel !== "account.move.line") {
            return false;
        }
        const changes = lineRecord._getChanges();
        if (!Object.keys(changes).length) {
            return false;
        }
        const staticList = this._sabacoFindAmlStaticList(lineRecord);
        if (!staticList) {
            return false;
        }
        // Solo readonly: il controllo _isRequired sulle altre righe escludeva righe valide
        // (changes contiene solo i campi modificati sulla riga corrente).
        const validSelection = staticList.selection.filter(
            (rec) =>
                typeof rec.resId === "number" &&
                Object.keys(changes).every((fieldName) => !rec._isReadonly(fieldName))
        );
        const canProceed = await this.model.hooks.onWillSaveMulti(lineRecord, changes, validSelection);
        if (canProceed === false) {
            return false;
        }
        if (!validSelection.length) {
            this.model.dialog.add(AlertDialog, {
                body: _t("No valid record to save"),
                confirm: () => staticList.leaveEditMode({ discard: true }),
                dismiss: () => staticList.leaveEditMode({ discard: true }),
            });
            return false;
        }
        const resIds = unique(
            validSelection.map((r) => r.resId).filter((id) => typeof id === "number")
        );
        if (!resIds.length) {
            this.model.dialog.add(AlertDialog, {
                body: _t("No valid record to save"),
                confirm: () => staticList.leaveEditMode({ discard: true }),
                dismiss: () => staticList.leaveEditMode({ discard: true }),
            });
            return false;
        }
        try {
            await this.model.orm.write("account.move.line", resIds, changes, {
                context: staticList.context,
            });
        } catch (e) {
            lineRecord._discard();
            this.model._updateConfig(lineRecord.config, { mode: "readonly" }, { reload: false });
            throw e;
        }
        const records = await this.model._loadRecords({
            resModel: "account.move.line",
            resIds,
            activeFields: staticList.activeFields,
            fields: staticList.fields,
            context: staticList.context,
        });
        for (const rec of validSelection) {
            if (typeof rec.resId !== "number") {
                continue;
            }
            const serverValues = records.find((r) => r.id === rec.resId);
            if (serverValues) {
                rec._applyValues(serverValues);
                this.model._updateSimilarRecords(rec, serverValues);
            }
        }
        lineRecord._discard();
        this.model._updateConfig(lineRecord.config, { mode: "readonly" }, { reload: false });
        this.model.hooks.onSavedMulti(validSelection);
        return true;
    },

    _sabacoFindAmlStaticList(lineRecord) {
        const parent = lineRecord._parentRecord;
        if (parent?.resModel !== "account.move") {
            return null;
        }
        const data = parent.data;
        const raw = toRaw(data);
        const sources = [data, raw].filter(Boolean);
        const rid = lineRecord.resId;
        for (const src of sources) {
            for (const fname of ["invoice_line_ids", "line_ids"]) {
                const list = src[fname];
                if (!list?.records?.length) {
                    continue;
                }
                if (typeof rid === "number" && list.records.some((r) => r.resId === rid)) {
                    return list;
                }
                if (list.records.includes(lineRecord)) {
                    return list;
                }
            }
        }
        return null;
    },
});
