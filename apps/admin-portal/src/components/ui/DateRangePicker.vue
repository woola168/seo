<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AppIcon from "./AppIcon.vue";

const props = defineProps<{
  start: string;
  end: string;
}>();

const emit = defineEmits<{
  apply: [range: { start: string; end: string }];
  cancel: [];
}>();

const draftStart = ref(props.start);
const draftEnd = ref(props.end);
const viewDate = ref(startOfMonth(props.start ? parseDate(props.start) : new Date()));

watch(
  () => [props.start, props.end] as const,
  ([start, end]) => {
    draftStart.value = start;
    draftEnd.value = end;
    if (start) viewDate.value = startOfMonth(parseDate(start));
  },
);

const year = computed(() => viewDate.value.getFullYear());
const month = computed(() => viewDate.value.getMonth());
const calendarCells = computed(() => {
  const cells: Array<Date | null> = [];
  const firstWeekday = new Date(year.value, month.value, 1).getDay();
  const daysInMonth = new Date(year.value, month.value + 1, 0).getDate();
  for (let index = 0; index < firstWeekday; index += 1) cells.push(null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(new Date(year.value, month.value, day));
  }
  return cells;
});

function selectDate(date: Date): void {
  const value = formatDate(date);
  if (!draftStart.value || draftEnd.value) {
    draftStart.value = value;
    draftEnd.value = "";
    return;
  }
  if (value < draftStart.value) {
    draftEnd.value = draftStart.value;
    draftStart.value = value;
    return;
  }
  draftEnd.value = value;
}

function moveMonth(offset: number): void {
  viewDate.value = new Date(year.value, month.value + offset, 1);
}

function isRangeEdge(date: Date): boolean {
  const value = formatDate(date);
  return value === draftStart.value || value === draftEnd.value;
}

function isInRange(date: Date): boolean {
  if (!draftStart.value || !draftEnd.value) return false;
  const value = formatDate(date);
  return value > draftStart.value && value < draftEnd.value;
}

function isToday(date: Date): boolean {
  return formatDate(date) === formatDate(new Date());
}

function applyRange(): void {
  if (!draftStart.value || !draftEnd.value) return;
  emit("apply", { start: draftStart.value, end: draftEnd.value });
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function parseDate(value: string): Date {
  const [yearValue, monthValue, dayValue] = value.split("-").map(Number);
  return new Date(yearValue, monthValue - 1, dayValue);
}

function formatDate(date: Date): string {
  const yearValue = date.getFullYear();
  const monthValue = String(date.getMonth() + 1).padStart(2, "0");
  const dayValue = String(date.getDate()).padStart(2, "0");
  return `${yearValue}-${monthValue}-${dayValue}`;
}
</script>

<template>
  <div class="date-range-picker" role="dialog" aria-label="選擇自訂日期區間">
    <div class="range-fields">
      <div :class="{ selected: draftStart }">{{ draftStart || "開始日期" }}</div>
      <span>至</span>
      <div :class="{ selected: draftEnd }">{{ draftEnd || "結束日期" }}</div>
    </div>

    <section class="calendar-panel">
      <header>
        <button type="button" title="上個月" @click="moveMonth(-1)">
          <AppIcon name="chevron-left" :size="14" />
        </button>
        <strong>{{ year }} 年 {{ month + 1 }} 月</strong>
        <button type="button" title="下個月" @click="moveMonth(1)">
          <AppIcon name="chevron-right" :size="14" />
        </button>
      </header>

      <div class="weekdays">
        <span v-for="weekday in ['日', '一', '二', '三', '四', '五', '六']" :key="weekday">{{ weekday }}</span>
      </div>
      <div class="calendar-grid">
        <span v-for="(date, index) in calendarCells" :key="date ? formatDate(date) : `empty-${index}`" class="calendar-cell">
          <button
            v-if="date"
            :class="{ edge: isRangeEdge(date), range: isInRange(date), today: isToday(date) }"
            type="button"
            @click="selectDate(date)"
          >
            {{ date.getDate() }}
          </button>
        </span>
      </div>
    </section>

    <footer>
      <button class="cancel-button" type="button" @click="emit('cancel')">取消</button>
      <button class="apply-button" type="button" :disabled="!draftStart || !draftEnd" @click="applyRange">套用</button>
    </footer>
  </div>
</template>

<style scoped>
.date-range-picker{position:absolute;z-index:130;top:40px;left:0;width:306px;box-sizing:border-box;padding:12px;border:1px solid #d9d9d9;border-radius:12px;background:#fff;box-shadow:0 4px 16px rgba(0,0,0,.08)}
.range-fields{display:flex;align-items:center;gap:8px;margin-bottom:10px;color:#8c8c8c;font-size:13px}.range-fields>div{min-width:0;flex:1;height:36px;box-sizing:border-box;display:flex;align-items:center;padding:0 10px;border:1px solid #d9d9d9;border-radius:8px;color:#bfbfbf;white-space:nowrap}.range-fields>div.selected{color:#1f1f1f}.range-fields>span{flex:0 0 auto}
.calendar-panel{padding:12px;border:1px solid #d9d9d9;border-radius:12px;background:#fff;box-shadow:0 4px 16px rgba(0,0,0,.08)}.calendar-panel header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}.calendar-panel header button{width:28px;height:28px;display:grid;place-items:center;border:1px solid #e7eaec;border-radius:6px;background:#fff;color:#595959;cursor:pointer}.calendar-panel header strong{color:#1f1f1f;font-size:14px;font-weight:600}
.weekdays,.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}.weekdays{margin-bottom:4px}.weekdays span{height:24px;display:grid;place-items:center;color:#bfbfbf;font-size:11px}.calendar-cell{height:32px}.calendar-cell button{width:100%;height:32px;border:1px solid transparent;border-radius:6px;background:transparent;color:#1f1f1f;font-size:13px;cursor:pointer}.calendar-cell button:hover{background:#fafafa}.calendar-cell button.range{border-radius:6px;background:#e7eaec}.calendar-cell button.edge{background:#0a2b41;color:#fff;font-weight:600}.calendar-cell button.today:not(.edge){border-color:#0a2b41;font-weight:600}
.date-range-picker footer{display:flex;justify-content:flex-end;gap:8px;margin-top:10px}.date-range-picker footer button{height:32px;padding:0 12px;border-radius:6px;font-size:13px;cursor:pointer}.cancel-button{border:1px solid #d9d9d9;background:#fff;color:#434343}.apply-button{border:1px solid #0a2b41;background:#0a2b41;color:#fff}.apply-button:disabled{border-color:#d9d9d9;background:#d9d9d9;cursor:not-allowed}
@media(max-width:639px){.date-range-picker{position:fixed;top:50%;left:50%;width:min(306px,calc(100vw - 32px));transform:translate(-50%,-50%)}}
</style>
