import { api, jsonBody } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { ClipboardCheck, ClipboardList, MapPinned, PlayCircle } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";

type Decision = { id: string; title: string; detail?: string; owner_name: string; due_at?: string; task_id?: string; status: "OPEN" | "DONE" | "CANCELLED"; can_manage: boolean };
type Handover = { id: string; term_name: string; title: string; summary: string; what_worked?: string; pitfalls?: string; checklist?: string; published_at?: string; can_manage: boolean };
type RunStatus = "PLANNED" | "READY" | "IN_PROGRESS" | "DONE" | "ISSUE";
type RunItem = { id: string; title: string; planned_at: string; location_label?: string; assignee_name?: string; status: RunStatus; note?: string };
type SchoolMap = { id: string; title: string; image_url: string; can_manage: boolean };
type Assignment = { id: string; user_name: string; label: string; activity: string; x_ratio: number; y_ratio: number; starts_at?: string; can_manage: boolean };
type MeetingRecord = { id: string; title: string; held_at: string };

const runLabels: Record<RunStatus, string> = { PLANNED: "예정", READY: "준비 완료", IN_PROGRESS: "진행 중", DONE: "완료", ISSUE: "문제 발생" };
const field = "h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-[#2563a8] focus:ring-2 focus:ring-[#2563a8]/15";
const area = `${field} h-auto min-h-20 py-2`;
const button = "inline-flex min-h-10 items-center justify-center rounded-md bg-[#2563a8] px-4 text-sm font-bold text-white hover:bg-[#1f528b] disabled:cursor-not-allowed disabled:opacity-45";
const label = "grid gap-1.5 text-xs font-bold text-slate-700";

function useRemote<T>(path: string, initial: T, revision = 0, enabled = true) {
  const [data, setData] = useState<T>(initial);
  useEffect(() => { if (enabled) api<T>(path).then(setData).catch(() => setData(initial)); }, [enabled, path, revision]);
  return data;
}

function Section({ icon, title, description, children }: { icon: ReactNode; title: string; description: string; children: ReactNode }) {
  return <section className="grid gap-4"><header className="flex items-center gap-3"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-[#cbd8e6] bg-[#f3f7fb] text-[#2563a8]">{icon}</span><div><h2 className="text-lg font-bold tracking-[-.02em] text-slate-900">{title}</h2><p className="mt-0.5 text-sm text-slate-500">{description}</p></div></header>{children}</section>;
}

export default function OperationsPage() {
  const { currentRole, users, events } = useApp();
  const canManage = currentRole !== "MEMBER";
  const [revision, setRevision] = useState(0);
  const [message, setMessage] = useState("");
  const [eventId, setEventId] = useState("");
  const [mapId, setMapId] = useState("");
  const [point, setPoint] = useState<{ x: number; y: number } | null>(null);
  const decisions = useRemote<Decision[]>("/operations/decisions", [], revision);
  const handovers = useRemote<Handover[]>("/operations/handovers", [], revision);
  const meetings = useRemote<MeetingRecord[]>("/meeting-records", [], revision);
  const maps = useRemote<SchoolMap[]>("/operations/maps", [], revision);
  const runItems = useRemote<RunItem[]>(eventId ? `/operations/events/${eventId}/run-items` : "", [], revision, Boolean(eventId));
  const assignments = useRemote<Assignment[]>(mapId ? `/operations/maps/${mapId}/assignments` : "", [], revision, Boolean(mapId));
  const selectedMap = maps.find((item) => item.id === mapId);

  useEffect(() => { if (!eventId && events[0]) setEventId(events[0].id); }, [eventId, events]);
  useEffect(() => { if (!mapId && maps[0]) setMapId(maps[0].id); }, [mapId, maps]);
  const saved = useCallback(() => { setMessage(""); setPoint(null); setRevision((value) => value + 1); }, []);
  const failed = (value: unknown, fallback: string) => setMessage(value instanceof Error ? value.message : fallback);

  async function createDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const values = new FormData(form); const due = String(values.get("due_at") || "");
    try { await api("/operations/decisions", { method: "POST", ...jsonBody({ title: values.get("title"), detail: values.get("detail") || null, owner_id: values.get("owner_id"), event_id: values.get("event_id") || null, meeting_record_id: values.get("meeting_record_id") || null, due_at: due ? new Date(due).toISOString() : null, create_task: true }) }); form.reset(); saved(); } catch (error) { failed(error, "결정 카드를 만들지 못했습니다."); }
  }
  async function decisionStatus(id: string, status: Decision["status"]) { try { await api(`/operations/decisions/${id}/status`, { method: "PATCH", ...jsonBody({ status }) }); saved(); } catch (error) { failed(error, "결정 상태를 변경하지 못했습니다."); } }
  async function createRunItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const values = new FormData(form); const planned = String(values.get("planned_at"));
    try { await api(`/operations/events/${eventId}/run-items`, { method: "POST", ...jsonBody({ title: values.get("title"), planned_at: new Date(planned).toISOString(), location_label: values.get("location_label") || null, assignee_id: values.get("assignee_id") || null, note: values.get("note") || null }) }); form.reset(); saved(); } catch (error) { failed(error, "운영 항목을 등록하지 못했습니다."); }
  }
  async function runStatus(id: string, status: RunStatus) { try { await api(`/operations/run-items/${id}/status`, { method: "PATCH", ...jsonBody({ status }) }); saved(); } catch (error) { failed(error, "현장 상태를 변경하지 못했습니다."); } }
  async function uploadMap(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; try { await api("/operations/maps", { method: "POST", body: new FormData(form) }); form.reset(); setMapId(""); saved(); } catch (error) { failed(error, "지도를 업로드하지 못했습니다."); } }
  function choosePoint(event: MouseEvent<HTMLDivElement>) { if (!selectedMap?.can_manage) return; const bounds = event.currentTarget.getBoundingClientRect(); setPoint({ x: (event.clientX - bounds.left) / bounds.width, y: (event.clientY - bounds.top) / bounds.height }); }
  async function assignMap(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!point) return setMessage("지도에서 활동 지점을 먼저 눌러 주세요."); const form = event.currentTarget; const values = new FormData(form); const starts = String(values.get("starts_at") || ""); const ends = String(values.get("ends_at") || "");
    try { await api(`/operations/maps/${mapId}/assignments`, { method: "POST", ...jsonBody({ user_id: values.get("user_id"), label: values.get("label"), activity: values.get("activity"), x_ratio: point.x, y_ratio: point.y, starts_at: starts ? new Date(starts).toISOString() : null, ends_at: ends ? new Date(ends).toISOString() : null }) }); form.reset(); saved(); } catch (error) { failed(error, "활동 위치를 배정하지 못했습니다."); }
  }
  async function removeAssignment(id: string) { try { await api(`/operations/map-assignments/${id}`, { method: "DELETE" }); saved(); } catch (error) { failed(error, "위치 배정을 삭제하지 못했습니다."); } }
  async function createHandover(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const values = new FormData(form);
    try { await api("/operations/handovers", { method: "POST", ...jsonBody({ title: values.get("title"), event_id: values.get("event_id") || null, summary: values.get("summary"), what_worked: values.get("what_worked") || null, pitfalls: values.get("pitfalls") || null, checklist: values.get("checklist") || null, publish: values.get("publish") === "on" }) }); form.reset(); saved(); } catch (error) { failed(error, "인수인계 문서를 저장하지 못했습니다."); }
  }
  async function publish(id: string) { try { await api(`/operations/handovers/${id}/publish`, { method: "POST" }); saved(); } catch (error) { failed(error, "인수인계 문서를 공개하지 못했습니다."); } }

  return <div className="mx-auto grid max-w-[1160px] gap-10 px-4 py-7 sm:px-6 lg:px-8"><header><p className="text-sm font-bold text-[#2563a8]">학생회 운영 OS</p><h1 className="mt-1 text-2xl font-bold tracking-[-.03em] text-slate-900">운영 센터</h1><p className="mt-2 text-sm leading-6 text-slate-500">결정부터 현장 실행, 다음 기수 인수인계까지 한 흐름으로 관리합니다.</p></header>
    {message && <p role="alert" className="border-l-4 border-[#b42318] bg-red-50 px-4 py-3 text-sm text-[#b42318]">{message}</p>}

    <Section icon={<ClipboardCheck size={21}/>} title="결정 카드" description="결정사항을 실제 업무·담당자·마감일에 연결합니다.">
      {canManage && <form onSubmit={createDecision} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2"><label className={label}>결정사항<input className={field} name="title" required/></label><label className={label}>담당자<select className={field} name="owner_id" required><option value="">선택</option>{users.map((user) => <option value={user.id} key={user.id}>{user.name}</option>)}</select></label><label className={label}>출처 회의록<select className={field} name="meeting_record_id"><option value="">회의록 없이 등록</option>{meetings.map((item) => <option value={item.id} key={item.id}>{new Date(item.held_at).toLocaleDateString("ko-KR")} · {item.title}</option>)}</select></label><label className={label}>관련 행사<select className={field} name="event_id"><option value="">없음</option>{events.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select></label><label className={label}>마감일<input className={field} name="due_at" type="datetime-local"/></label><label className={`${label} sm:col-span-2`}>세부 내용<textarea className={area} name="detail"/></label><button className={`${button} sm:col-span-2 sm:w-fit`}>결정과 업무 함께 등록</button></form>}
      <div className="grid gap-3 md:grid-cols-2">{decisions.map((item) => <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4"><div className="flex items-start justify-between gap-3"><h3 className="font-bold text-slate-900">{item.title}</h3><span className="shrink-0 rounded bg-[#e8f0f8] px-2 py-1 text-xs font-bold text-[#1f528b]">{item.status === "OPEN" ? "진행 중" : item.status === "DONE" ? "완료" : "취소"}</span></div>{item.detail && <p className="mt-2 text-sm leading-6 text-slate-600">{item.detail}</p>}<p className="mt-3 text-xs text-slate-500">담당 {item.owner_name} · {item.due_at ? new Date(item.due_at).toLocaleString("ko-KR") : "마감 미정"} · {item.task_id ? "업무 연결됨" : "기록 전용"}</p>{item.status === "OPEN" && <div className="mt-3 flex gap-2"><button className={button} onClick={() => decisionStatus(item.id, "DONE")}>완료</button>{item.can_manage && <button className="min-h-10 rounded-md border border-slate-300 px-3 text-sm font-bold text-slate-600" onClick={() => decisionStatus(item.id, "CANCELLED")}>취소</button>}</div>}</article>)}{!decisions.length && <p className="py-8 text-center text-sm text-slate-500">등록된 결정 카드가 없습니다.</p>}</div>
    </Section>

    <Section icon={<PlayCircle size={21}/>} title="행사 당일 운영" description="시간순 진행표와 담당자의 준비·진행·문제 상태를 확인합니다.">
      <label className={label}>운영할 행사<select className={`${field} max-w-md`} value={eventId} onChange={(event) => setEventId(event.target.value)}><option value="">행사 선택</option>{events.map((item) => <option value={item.id} key={item.id}>{item.date} · {item.title}</option>)}</select></label>
      {canManage && eventId && <form onSubmit={createRunItem} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2"><label className={label}>운영 항목<input className={field} name="title" required/></label><label className={label}>예정 시각<input className={field} name="planned_at" type="datetime-local" required/></label><label className={label}>구체 장소<input className={field} name="location_label"/></label><label className={label}>담당자<select className={field} name="assignee_id"><option value="">미정</option>{users.map((user) => <option value={user.id} key={user.id}>{user.name}</option>)}</select></label><label className={`${label} sm:col-span-2`}>현장 메모<textarea className={area} name="note"/></label><button className={`${button} sm:col-span-2 sm:w-fit`}>운영표에 추가</button></form>}
      <div className="grid gap-2">{runItems.map((item) => <article key={item.id} className={`grid gap-3 border border-l-4 bg-white p-4 sm:grid-cols-[80px_1fr_150px] sm:items-center ${item.status === "ISSUE" ? "border-l-[#b42318]" : item.status === "DONE" ? "border-l-emerald-600" : "border-l-[#2563a8]"}`}><time className="text-sm font-bold text-slate-700">{new Date(item.planned_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</time><div><h3 className="font-bold">{item.title}</h3><p className="mt-1 text-xs text-slate-500">{item.location_label || "장소 미정"} · {item.assignee_name || "담당자 미정"}</p>{item.note && <p className="mt-2 text-sm text-slate-600">{item.note}</p>}</div><select className={field} value={item.status} onChange={(event) => runStatus(item.id, event.target.value as RunStatus)}>{Object.entries(runLabels).map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></article>)}</div>
    </Section>

    <Section icon={<MapPinned size={21}/>} title="학교 지도 활동 위치" description="지도에서 지점을 눌러 학생별 구체 장소와 역할을 배정합니다.">
      {canManage && <form onSubmit={uploadMap} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-[1fr_1fr_1.2fr_auto] md:items-end"><label className={label}>지도 이름<input className={field} name="title" required/></label><label className={label}>관련 행사<select className={field} name="event_id" required><option value="">행사 선택</option>{events.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select></label><label className={label}>지도 이미지<input className={field} name="upload" type="file" accept="image/png,image/jpeg,image/webp" required/></label><button className={button}>비공개 지도 업로드</button></form>}
      {!!maps.length && <label className={label}>표시할 지도<select className={`${field} max-w-md`} value={mapId} onChange={(event) => { setMapId(event.target.value); setPoint(null); }}>{maps.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select></label>}
      {selectedMap ? <div className="grid items-start gap-4 lg:grid-cols-[1.4fr_.8fr]"><div onClick={choosePoint} className={`relative overflow-hidden rounded-lg border border-slate-200 bg-slate-100 ${selectedMap.can_manage ? "cursor-crosshair" : ""}`}><img src={selectedMap.image_url} alt={selectedMap.title} className="block h-auto max-h-[680px] w-full object-contain"/>{assignments.map((item, index) => <button onClick={(event) => event.stopPropagation()} type="button" title={`${item.user_name}: ${item.activity}`} key={item.id} style={{ left: `${item.x_ratio * 100}%`, top: `${item.y_ratio * 100}%` }} className="absolute grid h-8 w-8 -translate-x-1/2 -translate-y-full place-items-center rounded-full border-2 border-white bg-[#2563a8] text-xs font-bold text-white shadow-md">{index + 1}</button>)}{point && <span style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }} className="absolute grid h-8 w-8 -translate-x-1/2 -translate-y-full place-items-center rounded-full border-2 border-dashed border-white bg-[#b42318] font-bold text-white">+</span>}</div><div className="grid gap-3">{selectedMap.can_manage && <form onSubmit={assignMap} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4"><h3 className="font-bold">선택한 지점에 배정</h3><p className="text-xs text-slate-500">{point ? `가로 ${(point.x * 100).toFixed(1)}%, 세로 ${(point.y * 100).toFixed(1)}%` : "지도에서 지점을 눌러 주세요."}</p><label className={label}>학생<select className={field} name="user_id" required><option value="">선택</option>{users.map((user) => <option value={user.id} key={user.id}>{user.name}</option>)}</select></label><label className={label}>장소 이름<input className={field} name="label" required/></label><label className={label}>구체적인 활동<input className={field} name="activity" required/></label><label className={label}>시작<input className={field} name="starts_at" type="datetime-local"/></label><label className={label}>종료<input className={field} name="ends_at" type="datetime-local"/></label><button className={button} disabled={!point}>위치 배정</button></form>}<div className="grid gap-2">{assignments.map((item, index) => <article className="grid grid-cols-[28px_1fr_auto] gap-3 rounded-lg border border-slate-200 bg-white p-3" key={item.id}><span className="grid h-7 w-7 place-items-center rounded-full bg-[#2563a8] text-xs font-bold text-white">{index + 1}</span><div><h3 className="font-bold">{item.label}</h3><p className="text-xs text-slate-500">{item.user_name}</p><p className="mt-1 text-sm text-slate-600">{item.activity}</p></div>{item.can_manage && <button className="h-8 w-8 text-slate-500" onClick={() => removeAssignment(item.id)} aria-label="배정 삭제">×</button>}</article>)}</div></div></div> : <p className="py-10 text-center text-sm text-slate-500">{canManage ? "먼저 학교 지도 이미지를 업로드해 주세요." : "아직 배정된 활동 위치가 없습니다."}</p>}
    </Section>

    <Section icon={<ClipboardList size={21}/>} title="기수 인수인계" description="다음 기수가 준비 순서와 시행착오를 그대로 이어받습니다.">
      {canManage && <form onSubmit={createHandover} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2"><label className={label}>문서 제목<input className={field} name="title" required/></label><label className={label}>관련 행사<select className={field} name="event_id"><option value="">공통 운영</option>{events.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select></label><label className={`${label} sm:col-span-2`}>핵심 요약<textarea className={area} name="summary" required/></label><label className={label}>잘된 점<textarea className={area} name="what_worked"/></label><label className={label}>주의할 점<textarea className={area} name="pitfalls"/></label><label className={`${label} sm:col-span-2`}>체크리스트<textarea className={area} name="checklist" placeholder="한 줄에 한 항목씩 작성하세요."/></label><label className="flex items-center gap-2 text-sm font-semibold text-slate-700"><input name="publish" type="checkbox"/> 바로 공개</label><button className={`${button} sm:col-span-2 sm:w-fit`}>인수인계 저장</button></form>}
      <div className="grid gap-3 md:grid-cols-2">{handovers.map((item) => <article className="rounded-lg border border-slate-200 bg-white p-4" key={item.id}><div className="flex justify-between gap-3"><div><p className="text-xs font-bold text-slate-500">{item.term_name}</p><h3 className="mt-1 font-bold">{item.title}</h3></div><span className="h-fit rounded bg-[#e8f0f8] px-2 py-1 text-xs font-bold text-[#1f528b]">{item.published_at ? "공개" : "초안"}</span></div><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">{item.summary}</p>{item.what_worked && <details className="mt-3 border-t border-slate-100 pt-3"><summary className="cursor-pointer text-sm font-bold">잘된 점</summary><p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{item.what_worked}</p></details>}{item.pitfalls && <details className="mt-3 border-t border-slate-100 pt-3"><summary className="cursor-pointer text-sm font-bold">주의할 점</summary><p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{item.pitfalls}</p></details>}{item.checklist && <details className="mt-3 border-t border-slate-100 pt-3"><summary className="cursor-pointer text-sm font-bold">체크리스트</summary><ul className="mt-2 list-disc pl-5 text-sm leading-6 text-slate-600">{item.checklist.split("\n").filter(Boolean).map((line, index) => <li key={index}>{line}</li>)}</ul></details>}{!item.published_at && item.can_manage && <button className={`${button} mt-3`} onClick={() => publish(item.id)}>다음 기수에 공개</button>}</article>)}</div>
    </Section>
  </div>;
}
