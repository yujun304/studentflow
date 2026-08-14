import { FormEvent, useMemo, useState } from "react";

import { api, jsonBody } from "./api";
import type { CalendarItem } from "./types";
import { useApiData } from "./useApiData";

const colors = ["#356ae6", "#7c3aed", "#db2777", "#d97706", "#059669", "#0891b2"];
const sourceNames: Record<CalendarItem["source"], string> = {
  EVENT: "행사",
  CAMPAIGN: "캠페인",
  TASK_DEADLINE: "업무 마감",
  SUBMISSION_DEADLINE: "제출 마감",
  TEAM_FORMATION_DEADLINE: "조 편성 마감",
  TEAM_REMINDER: "조 일정",
  PERSONAL: "개인 일정",
};

const dateKey = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const localDateTimeValue = (value?: string) => {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
};

function CalendarEditor({ item, onClose }: { item?: CalendarItem; onClose: () => void }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const data = new FormData(event.currentTarget); const startsAt = String(data.get("starts_at"));
    try {
      await api(item ? `/calendar/items/${item.id}` : "/calendar/items", { method: item ? "PATCH" : "POST", ...jsonBody({ title: data.get("title"), content: data.get("content") || null, starts_at: new Date(startsAt).toISOString(), color: data.get("color") }) });
      window.location.reload();
    } catch (value) { setError(value instanceof Error ? value.message : "일정을 저장하지 못했습니다."); }
  }
  async function remove() {
    if (!item) return;
    try { await api(`/calendar/items/${item.id}`, { method: "DELETE" }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "일정을 삭제하지 못했습니다."); }
  }
  return <form className="panel calendar-editor" onSubmit={submit}><div className="panel-head"><h2>{item ? "개인 일정 수정" : "개인 일정 추가"}</h2><button className="link-button" type="button" onClick={onClose}>닫기</button></div><div className="form-grid"><label>제목<input name="title" required maxLength={200} defaultValue={item?.title} /></label><label>일시<input name="starts_at" type="datetime-local" required defaultValue={localDateTimeValue(item?.starts_at)} /></label><label className="full">메모<textarea name="content" rows={2} defaultValue={item?.description} /></label><label>색상<select name="color" defaultValue={item?.color ?? colors[0]}>{colors.map(color => <option key={color} value={color}>{color}</option>)}</select></label></div>{error && <p className="error">{error}</p>}<div className="actions"><button type="submit">저장</button>{item && <button className="danger" type="button" onClick={remove}>삭제</button>}</div></form>;
}

function Month({ month, items, onEdit }: { month: Date; items: CalendarItem[]; onEdit: (item: CalendarItem) => void }) {
  const year = month.getFullYear(); const monthIndex = month.getMonth(); const firstDay = new Date(year, monthIndex, 1).getDay(); const days = new Date(year, monthIndex + 1, 0).getDate();
  const cells = [...Array(firstDay).fill(null), ...Array.from({ length: days }, (_, index) => index + 1)];
  return <section className="month"><h2>{year}년 {monthIndex + 1}월</h2><div className="weekdays">{["일", "월", "화", "수", "목", "금", "토"].map(day => <span key={day}>{day}</span>)}</div><div className="month-grid">{cells.map((day, index) => day === null ? <div className="day empty-day" key={`blank-${index}`} /> : <div className="day" key={day}><b>{day}</b><div className="day-items">{items.filter(item => dateKey(new Date(item.starts_at)) === dateKey(new Date(year, monthIndex, day))).map(item => item.editable ? <button type="button" className="calendar-item" style={{ borderLeftColor: item.color }} key={item.id} onClick={() => onEdit(item)}><span>{new Date(item.starts_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</span>{item.title}</button> : <div className="calendar-item" style={{ borderLeftColor: item.color }} key={item.id}><span>{item.source === "EVENT" || item.source === "CAMPAIGN" ? "" : new Date(item.starts_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</span>{item.title}</div>)}</div></div>)}</div></section>;
}

export default function TwoMonthCalendar() {
  const now = new Date(); const current = new Date(now.getFullYear(), now.getMonth(), 1); const next = new Date(now.getFullYear(), now.getMonth() + 1, 1); const start = dateKey(current); const end = dateKey(new Date(now.getFullYear(), now.getMonth() + 2, 0));
  const { data: items, isLoading } = useApiData<CalendarItem[]>(`/calendar?start=${start}&end=${end}`, []); const [editor, setEditor] = useState<CalendarItem | "new" | null>(null);
  const legend = useMemo(() => Array.from(new Map(items.map(item => [item.source, item.color])).entries()), [items]);
  return <section className="calendar-section"><div className="calendar-heading"><div><p className="eyebrow">일정</p><h2>이번 달과 다음 달</h2></div><button type="button" onClick={() => setEditor("new")}>개인 일정 추가</button></div>{editor && <CalendarEditor item={editor === "new" ? undefined : editor} onClose={() => setEditor(null)} />}{isLoading ? <div className="empty">달력을 불러오는 중…</div> : <div className="calendar-pair"><Month month={current} items={items} onEdit={setEditor} /><Month month={next} items={items} onEdit={setEditor} /></div>}<div className="calendar-legend">{legend.map(([source, color]) => <span key={source}><i style={{ background: color }} />{sourceNames[source]}</span>)}</div></section>;
}
