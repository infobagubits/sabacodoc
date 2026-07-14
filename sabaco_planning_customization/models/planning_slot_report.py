# -*- coding: utf-8 -*-
import math
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.tools.misc import format_date
from odoo.tools import float_utils

# Palette Odoo Gantt ($o-colors)
ODOO_GANTT_COLORS = [
    '#a2a2a2', '#ee2d2d', '#dc8534', '#e8bb1d', '#5794dd', '#9f628f', '#db8865',
    '#41a9a2', '#304be0', '#ee2f8a', '#61c36e', '#9872e6',
]
DAY_MINUTES = 24 * 60
# Eixo de horas visível no relatório: madrugada 00–05 removida (pedido cliente).
DISPLAY_START_HOUR = 6
VISIBLE_HOURS = list(range(DISPLAY_START_HOUR, 24))      # 06..23 → 18 colunas
VISIBLE_START_MIN = DISPLAY_START_HOUR * 60              # 360
VISIBLE_TOTAL_MIN = (24 - DISPLAY_START_HOUR) * 60       # 1080
PILL_HEIGHT_PX = 22
PILL_LEVEL_STEP_PX = 24
ROW_PADDING_PX = 4


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    @api.model
    def _sabaco_gantt_color_hex(self, color_index):
        if color_index is None:
            color_index = 0
        return ODOO_GANTT_COLORS[int(color_index) % len(ODOO_GANTT_COLORS)]

    @api.model
    def _sabaco_mix_with_white(self, hex_color, ratio=0.4):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r * ratio + 255 * (1 - ratio))
        g = int(g * ratio + 255 * (1 - ratio))
        b = int(b * ratio + 255 * (1 - ratio))
        return f'#{r:02x}{g:02x}{b:02x}'

    @api.model
    def _sabaco_report_timezone(self):
        tz_name = (
            self.env.user.tz
            or self.env.company.resource_calendar_id.tz
            or 'UTC'
        )
        return pytz.timezone(tz_name)

    @api.model
    def _sabaco_day_bounds(self, report_date):
        tz = self._sabaco_report_timezone()
        day_start = tz.localize(datetime.combine(report_date, time.min))
        day_end = day_start + timedelta(days=1)
        return day_start, day_end, tz

    @api.model
    def _sabaco_format_duration_label(self, hours):
        if not hours:
            return ''
        total_minutes = int(round(float_utils.float_round(hours * 60, precision_digits=0)))
        total_minutes = max(total_minutes, 0)
        hours_part, minutes_part = divmod(total_minutes, 60)
        return f'{hours_part:02d}:{minutes_part:02d}'

    @api.model
    def _sabaco_format_time_label(self, minutes):
        """Converte minutos-do-dia (0–1440) em rótulo HH:MM."""
        total_minutes = int(round(minutes))
        total_minutes = min(max(total_minutes, 0), DAY_MINUTES)
        hours_part, minutes_part = divmod(total_minutes, 60)
        return f'{hours_part:02d}:{minutes_part:02d}'

    @api.model
    def _sabaco_slot_display_name(self, slot):
        if slot.employee_id:
            return slot.employee_id.name
        if slot.resource_id:
            return slot.resource_id.name
        return ''

    @api.model
    def _sabaco_normalize_resource_key(self, key):
        if key in (False, None, 'false'):
            return False
        return int(key)

    @api.model
    def _sabaco_interval_to_local(self, interval, tz):
        utc = pytz.UTC

        def to_local(dt):
            if dt.tzinfo is None:
                dt = utc.localize(dt)
            else:
                dt = dt.astimezone(utc)
            return dt.astimezone(tz)

        return to_local(interval[0]), to_local(interval[1])

    @api.model
    def _sabaco_fetch_gantt_work_context(self, slots, day_start, day_end):
        if not slots:
            return {}, {}
        ctx = dict(
            self.env.context,
            default_start_datetime=fields.Datetime.to_string(
                day_start.astimezone(pytz.UTC).replace(tzinfo=None)
            ),
            default_end_datetime=fields.Datetime.to_string(
                day_end.astimezone(pytz.UTC).replace(tzinfo=None)
            ),
            current_scale='day',
        )
        raw = self.with_context(ctx).gantt_resource_work_interval(slots.ids)
        if not raw or raw == [{}]:
            return {}, {}
        work_raw, flexible_raw = raw[0], raw[1]
        tz = self._sabaco_report_timezone()
        work_intervals = {}
        for res_key, intervals in work_raw.items():
            res_id = self._sabaco_normalize_resource_key(res_key)
            work_intervals[res_id] = [
                self._sabaco_interval_to_local(interval, tz)
                for interval in intervals
            ]
        flexible_hours = {
            self._sabaco_normalize_resource_key(key): value
            for key, value in flexible_raw.items()
        }
        return work_intervals, flexible_hours

    @api.model
    def _sabaco_visible_hour_bounds(self, visible_start, visible_end, day_start):
        start_minutes = (visible_start - day_start).total_seconds() / 60
        end_minutes = (visible_end - day_start).total_seconds() / 60
        first_hour = max(0, int(start_minutes // 60))
        last_hour_excl = min(24, max(first_hour + 1, math.ceil(end_minutes / 60)))
        return first_hour, last_hour_excl

    @api.model
    def _sabaco_intersection_duration_ms(self, interval, intervals):
        start, end = interval
        total_ms = 0.0
        for other_start, other_end in intervals:
            overlap_start = max(start, other_start)
            overlap_end = min(end, other_end)
            if overlap_end > overlap_start:
                total_ms += (overlap_end - overlap_start).total_seconds() * 1000
        return total_ms

    @api.model
    def _sabaco_get_record_work_intervals(self, visible_start, visible_end, work_intervals):
        result = []
        for interval_start, interval_end in work_intervals:
            overlap_start = max(visible_start, interval_start)
            overlap_end = min(visible_end, interval_end)
            if overlap_end > overlap_start:
                result.append((overlap_start, overlap_end))
        return result

    @api.model
    def _sabaco_round_minutes_to_five(self, minutes):
        return round(minutes / 5) * 5

    def _sabaco_compute_slot_hourly_allocation(
        self, slot, day_start, day_end, tz, work_intervals, flexible_hours
    ):
        """Replica planning_gantt_renderer.enrichPill allocatedHours per colonna."""
        utc = pytz.UTC
        slot_start = utc.localize(slot.start_datetime).astimezone(tz)
        slot_end = utc.localize(slot.end_datetime).astimezone(tz)
        visible_start = max(slot_start, day_start)
        visible_end = min(slot_end, day_end)
        if visible_end <= visible_start:
            return {}

        first_hour, last_hour_excl = self._sabaco_visible_hour_bounds(
            visible_start, visible_end, day_start
        )
        span = last_hour_excl - first_hour
        if span <= 0:
            return {}

        resource_id = slot.resource_id.id if slot.resource_id else False
        is_open_shift = not slot.resource_id
        is_flexible = flexible_hours.get(resource_id, False)
        hourly = {}

        if is_open_shift or is_flexible:
            allocated_hours = slot.allocated_hours or 0.0
            if not allocated_hours:
                return {}
            for hour_index in range(first_hour, last_hour_excl):
                hour_start = day_start + timedelta(hours=hour_index)
                hour_end = hour_start + timedelta(hours=1)
                max_duration_ms = (hour_end - hour_start).total_seconds() * 1000
                daily_alloc_ms = min(
                    allocated_hours * 3600000 / span,
                    max_duration_ms,
                )
                if daily_alloc_ms > 0:
                    minutes = self._sabaco_round_minutes_to_five(daily_alloc_ms / 60000)
                    if minutes > 0:
                        hourly[hour_index] = minutes / 60.0
            return hourly

        allocation_ratio = (slot.allocated_percentage or 0.0) / 100.0
        if allocation_ratio == 0:
            return {}

        resource_work = work_intervals.get(resource_id, [])
        record_intervals = self._sabaco_get_record_work_intervals(
            visible_start, visible_end, resource_work
        )
        if not record_intervals:
            record_intervals = [(visible_start, visible_end)]
            duration_ms = (visible_end - visible_start).total_seconds() * 1000
            if duration_ms > 0:
                allocation_ratio = (slot.allocated_hours or 0.0) * 3600000 / duration_ms

        loop_start = max(0, first_hour - 1)
        for hour_index in range(loop_start, last_hour_excl):
            hour_start = day_start + timedelta(hours=hour_index)
            hour_end = hour_start + timedelta(hours=1)
            interval = (hour_start, hour_end + timedelta(seconds=1))
            duration_ms = self._sabaco_intersection_duration_ms(interval, record_intervals)
            if duration_ms > 0:
                minutes = self._sabaco_round_minutes_to_five(
                    duration_ms * allocation_ratio / 60000
                )
                if minutes > 0:
                    hourly[hour_index] = minutes / 60.0
        return hourly

    def _sabaco_slot_bar_values(self, slot, day_start, day_end, tz, color_index=None):
        utc = pytz.UTC
        slot_start = utc.localize(slot.start_datetime).astimezone(tz)
        slot_end = utc.localize(slot.end_datetime).astimezone(tz)
        visible_start = max(slot_start, day_start)
        visible_end = min(slot_end, day_end)
        if visible_end <= visible_start:
            return None

        start_minutes = (visible_start - day_start).total_seconds() / 60
        end_minutes = (visible_end - day_start).total_seconds() / 60
        # Recorta para a faixa visível (06:00–24:00); turno inteiro na madrugada → não exibe
        start_minutes = max(start_minutes, VISIBLE_START_MIN)
        end_minutes = max(end_minutes, VISIBLE_START_MIN)
        if end_minutes <= start_minutes:
            return None
        left = ((start_minutes - VISIBLE_START_MIN) / VISIBLE_TOTAL_MIN) * 100
        width = ((end_minutes - start_minutes) / VISIBLE_TOTAL_MIN) * 100
        first_hour, last_hour_excl = self._sabaco_visible_hour_bounds(
            visible_start, visible_end, day_start
        )
        if color_index is None:
            color_index = slot.color or slot.role_id.color or 0
        color_hex = self._sabaco_gantt_color_hex(color_index)
        duration_hours = slot.allocated_hours or (end_minutes - start_minutes) / 60

        return {
            'left': left,
            'width': max(width, 0.5),
            'first_grid_col': first_hour + 1,
            'last_grid_col_excl': last_hour_excl + 1,
            'color_hex': color_hex,
            'color_subtle': self._sabaco_mix_with_white(color_hex),
            'color_strong': color_hex,
            'is_draft': slot.state == 'draft',
            'duration_label': self._sabaco_format_duration_label(duration_hours),
            'employee_name': self._sabaco_slot_display_name(slot),
            'time_range_label': '%s - %s' % (
                self._sabaco_format_time_label(start_minutes),
                self._sabaco_format_time_label(end_minutes),
            ),
            'top_px': ROW_PADDING_PX,
        }

    @api.model
    def _sabaco_prepare_row_slots(self, bars):
        if not bars:
            return bars, 30
        sorted_bars = sorted(
            bars,
            key=lambda bar: (bar['first_grid_col'], bar['last_grid_col_excl']),
        )
        levels = []
        for bar in sorted_bars:
            max_col = bar['last_grid_col_excl'] - 1
            placed = False
            for level_idx, level in enumerate(levels):
                if bar['first_grid_col'] > level['max_col']:
                    bar['top_px'] = ROW_PADDING_PX + level_idx * PILL_LEVEL_STEP_PX
                    level['bars'].append(bar)
                    level['max_col'] = max(level['max_col'], max_col)
                    placed = True
                    break
            if not placed:
                level_idx = len(levels)
                bar['top_px'] = ROW_PADDING_PX + level_idx * PILL_LEVEL_STEP_PX
                levels.append({'max_col': max_col, 'bars': [bar]})
        if len(levels) <= 1:
            row_height = 30
        else:
            row_height = ROW_PADDING_PX + len(levels) * PILL_LEVEL_STEP_PX + PILL_HEIGHT_PX
        return sorted_bars, row_height

    @api.model
    def _sabaco_build_role_summary_slots(
        self, role_slots, day_start, day_end, tz, work_intervals, flexible_hours, color_hex
    ):
        hour_totals = [0.0] * 24
        for slot in role_slots:
            hourly = slot._sabaco_compute_slot_hourly_allocation(
                slot, day_start, day_end, tz, work_intervals, flexible_hours
            )
            for hour_index, hours in hourly.items():
                hour_totals[hour_index] += hours

        hour_width = 100 / len(VISIBLE_HOURS)
        color_subtle = self._sabaco_mix_with_white(color_hex, ratio=0.55)
        summary_slots = []
        for col_index, hour_index in enumerate(VISIBLE_HOURS):
            value = hour_totals[hour_index]
            if value <= 0:
                continue
            summary_slots.append({
                'left': col_index * hour_width,
                'width': hour_width,
                'first_grid_col': col_index + 1,
                'last_grid_col_excl': col_index + 2,
                'color_hex': color_hex,
                'color_subtle': color_subtle,
                'color_strong': color_hex,
                'is_draft': False,
                'duration_label': self._sabaco_format_duration_label(value),
                'employee_name': '',
                'top_px': ROW_PADDING_PX,
                'is_summary': True,
            })
        return summary_slots

    @api.model
    def _sabaco_build_total_row(
        self, slots, day_start, day_end, tz, work_intervals, flexible_hours
    ):
        hour_totals = [0.0] * 24
        for slot in slots:
            hourly = slot._sabaco_compute_slot_hourly_allocation(
                slot, day_start, day_end, tz, work_intervals, flexible_hours
            )
            for hour_index, hours in hourly.items():
                hour_totals[hour_index] += hours

        visible_totals = [hour_totals[h] for h in VISIBLE_HOURS]
        max_total = max(visible_totals) if any(visible_totals) else 0
        total_color = '#9f628f'
        max_bar_height = 44
        hours_data = []
        for hour_index in VISIBLE_HOURS:
            value = hour_totals[hour_index]
            bar_height = (
                int(round(value / max_total * max_bar_height))
                if max_total > 0 and value > 0
                else 0
            )
            hours_data.append({
                'hour': hour_index,
                'label': self._sabaco_format_duration_label(value) if value > 0 else '',
                'value': value,
                'bar_height_px': bar_height,
                'has_value': value > 0,
            })

        return {
            'name': _('Total'),
            'color_hex': total_color,
            'color_subtle': self._sabaco_mix_with_white(total_color, ratio=0.55),
            'hours': hours_data,
        }

    @api.model
    def _sabaco_get_schedule_by_role_report_values(self, report_date):
        day_start, day_end, tz = self._sabaco_day_bounds(report_date)
        start_utc = day_start.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = day_end.astimezone(pytz.UTC).replace(tzinfo=None)

        slots = self.search([
            ('start_datetime', '<', end_utc),
            ('end_datetime', '>', start_utc),
        ], order='role_id, resource_id, start_datetime')

        work_intervals, flexible_hours = self._sabaco_fetch_gantt_work_context(
            slots, day_start, day_end
        )

        roles = self.env['planning.role'].search([], order='sequence, name')
        role_ids_in_slots = slots.mapped('role_id').ids
        ordered_roles = roles.filtered(lambda r: r.id in role_ids_in_slots)
        unordered_roles = slots.mapped('role_id').filtered(
            lambda r: r not in ordered_roles
        )
        undefined_slots = slots.filtered(lambda s: not s.role_id)

        role_groups = []
        open_shifts_label = _('Open Shifts')
        undefined_role_label = _('Undefined Role')

        def build_role_group(role, role_slots):
            color_index = role.color if role else 0
            color_hex = self._sabaco_gantt_color_hex(color_index)
            rows = []

            def append_row(name, row_slots):
                bars = [
                    bar for slot in row_slots.sorted(key=lambda s: s.start_datetime or '')
                    for bar in [
                        slot._sabaco_slot_bar_values(
                            slot, day_start, day_end, tz, color_index=color_index
                        )
                    ]
                    if bar
                ]
                bars, row_height = self._sabaco_prepare_row_slots(bars)
                rows.append({
                    'name': name,
                    'slots': bars,
                    'row_height': row_height,
                })

            open_slots = role_slots.filtered(lambda s: not s.resource_id)
            if open_slots:
                append_row(open_shifts_label, open_slots)

            assigned_slots = role_slots.filtered(lambda s: s.resource_id)
            for resource in assigned_slots.mapped('resource_id').sorted(key=lambda r: r.name or ''):
                resource_slots = assigned_slots.filtered(lambda s: s.resource_id == resource)
                append_row(resource.name, resource_slots)

            if not rows and role_slots:
                append_row(open_shifts_label, role_slots)

            return {
                'name': role.name if role else undefined_role_label,
                'color_hex': color_hex,
                'color_subtle': self._sabaco_mix_with_white(color_hex, ratio=0.55),
                'color_row_bg': self._sabaco_mix_with_white(color_hex, ratio=0.75),
                'rows': rows,
            }

        for role in ordered_roles:
            role_slots = slots.filtered(lambda s: s.role_id == role)
            if role_slots:
                role_groups.append(build_role_group(role, role_slots))

        for role in unordered_roles:
            role_slots = slots.filtered(lambda s: s.role_id == role)
            if role_slots:
                role_groups.append(build_role_group(role, role_slots))

        if undefined_slots:
            role_groups.append(build_role_group(None, undefined_slots))

        return {
            'report_date': report_date,
            'report_date_label': format_date(self.env, report_date),
            'hours': list(VISIBLE_HOURS),
            'role_groups': role_groups,
            'company': self.env.company,
        }
