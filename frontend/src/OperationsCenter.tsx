import { FormEvent, MouseEvent as ReactMouseEvent, useEffect, useState } from "react";
import { CheckCircle2, ClipboardList, MapPinned, PlayCircle } from "lucide-react";

import { api, jsonBody } from "./api";
import type {
  DecisionCard,
  DecisionStatus,
  EventItem,
  EventRunItem,
  HandoverGuide,
  MapAssignment,
  MeetingRecord,
  RunItemStatus,
  SchoolMap,
  User,
} from "./types";
import { useApiData } from "./useApiData";

const decisionLabels: Record<DecisionStatus, string> = {
  OPEN: "진행 중",
  DONE: "완료",
  CANCELLED: "취소",
};
const runLabels: Record<RunItemStatus, string> = {
  PLANNED: "예정",
  READY: "준비 완료",
  IN_PROGRESS: "진행 중",
  DONE: "완료",
  ISSUE: "문제 발생",
};

function ErrorMessage({ value }: { value: string }) {
  return value ? <p className="error" role="alert">{value}</p> : null;
}

function DecisionSection({ user, users, events }: { user: User; users: User[]; events: EventItem[] }) {
  const { data } = useApiData<DecisionCard[]>("/operations/decisions", []);
  const { data: meetings } = useApiData<MeetingRecord[]>("/meeting-records", []);
  const [error, setError] = useState("");
  const canCreate = user.role !== "MEMBER";

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = event.currentTarget; const values = new FormData(form);
    const dueAt = String(values.get("due_at") || "");
    try {
      await api("/operations/decisions", { method: "POST", ...jsonBody({
        title: values.get("title"), detail: values.get("detail") || null,
        owner_id: values.get("owner_id"), event_id: values.get("event_id") || null,
        meeting_record_id: values.get("meeting_record_id") || null,
        due_at: dueAt ? new Date(dueAt).toISOString() : null, create_task: true,
      }) });
      window.location.reload();
    } catch (value) { setError(value instanceof Error ? value.message : "결정 카드를 만들지 못했습니다."); }
  }

  async function changeStatus(id: string, status: DecisionStatus) {
    try { await api(`/operations/decisions/${id}/status`, { method: "PATCH", ...jsonBody({ status }) }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "결정 상태를 변경하지 못했습니다."); }
  }

  return <section className="operations-section"><div className="section-heading"><span className="section-icon"><CheckCircle2 size={20} /></span><div><h2>결정 카드</h2><p>결정사항을 실제 업무·담당자·마감일에 연결합니다.</p></div></div>
    {canCreate && <form className="panel compact-form" onSubmit={create}><div className="form-grid"><label>결정사항<input name="title" required maxLength={200} placeholder="예: 정문 안내판을 설치한다" /></label><label>담당자<select name="owner_id" required><option value="">선택</option>{users.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>출처 회의록<select name="meeting_record_id"><option value="">회의록 없이 등록</option>{meetings.map(item => <option key={item.id} value={item.id}>{new Date(item.held_at).toLocaleDateString("ko-KR")} · {item.title}</option>)}</select></label><label>관련 행사<select name="event_id"><option value="">없음</option>{events.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label>마감일<input name="due_at" type="datetime-local" /></label><label className="full">세부 내용<textarea name="detail" rows={2} /></label></div><button type="submit">결정과 업무 함께 등록</button></form>}
    <ErrorMessage value={error} />
    <div className="decision-list">{data.length === 0 && <div className="empty">등록된 결정 카드가 없습니다.</div>}{data.map(item => <article className="panel decision-card" key={item.id}><div className="panel-head"><div><span className={`status-dot status-${item.status.toLowerCase()}`} /> <b>{item.title}</b></div><span className="badge">{decisionLabels[item.status]}</span></div>{item.detail && <p>{item.detail}</p>}<div className="meta-line"><span>담당 {item.owner_name}</span><span>{item.due_at ? `${new Date(item.due_at).toLocaleString("ko-KR")}까지` : "마감 미정"}</span><span>{item.task_id ? "업무 연결됨" : "기록 전용"}</span></div>{item.status === "OPEN" && <div className="actions"><button type="button" onClick={() => changeStatus(item.id, "DONE")}>완료 처리</button>{item.can_manage && <button type="button" className="secondary" onClick={() => changeStatus(item.id, "CANCELLED")}>취소</button>}</div>}</article>)}</div>
  </section>;
}

function HandoverSection({ user, events }: { user: User; events: EventItem[] }) {
  const { data } = useApiData<HandoverGuide[]>("/operations/handovers", []);
  const [error, setError] = useState("");
  const canCreate = user.role !== "MEMBER";

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const values = new FormData(event.currentTarget);
    try {
      await api("/operations/handovers", { method: "POST", ...jsonBody({
        title: values.get("title"), event_id: values.get("event_id") || null,
        summary: values.get("summary"), what_worked: values.get("what_worked") || null,
        pitfalls: values.get("pitfalls") || null, checklist: values.get("checklist") || null,
        publish: values.get("publish") === "on",
      }) });
      window.location.reload();
    } catch (value) { setError(value instanceof Error ? value.message : "인수인계 문서를 저장하지 못했습니다."); }
  }

  async function publish(id: string) {
    try { await api(`/operations/handovers/${id}/publish`, { method: "POST" }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "문서를 공개하지 못했습니다."); }
  }

  return <section className="operations-section"><div className="section-heading"><span className="section-icon"><ClipboardList size={20} /></span><div><h2>기수 인수인계</h2><p>다음 기수가 준비 순서와 시행착오를 그대로 이어받습니다.</p></div></div>
    {canCreate && <form className="panel compact-form" onSubmit={create}><div className="form-grid"><label>문서 제목<input name="title" required maxLength={200} /></label><label>관련 행사<select name="event_id"><option value="">공통 운영</option>{events.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label className="full">핵심 요약<textarea name="summary" required rows={3} /></label><label>잘된 점<textarea name="what_worked" rows={3} /></label><label>주의할 점<textarea name="pitfalls" rows={3} /></label><label className="full">다음 기수 체크리스트<textarea name="checklist" rows={4} placeholder="한 줄에 한 항목씩 작성하세요." /></label><label className="check"><input name="publish" type="checkbox" /> 바로 공개</label></div><button type="submit">인수인계 저장</button></form>}
    <ErrorMessage value={error} />
    <div className="handover-grid">{data.length === 0 && <div className="empty">공개된 인수인계 문서가 없습니다.</div>}{data.map(item => <article className="panel handover-card" key={item.id}><div className="panel-head"><div><small>{item.term_name}</small><h3>{item.title}</h3></div><span className="badge">{item.published_at ? "공개" : "초안"}</span></div><p>{item.summary}</p>{item.what_worked && <details><summary>잘된 점</summary><p>{item.what_worked}</p></details>}{item.pitfalls && <details><summary>주의할 점</summary><p>{item.pitfalls}</p></details>}{item.checklist && <details><summary>체크리스트</summary><ul>{item.checklist.split("\n").filter(Boolean).map((line, index) => <li key={index}>{line}</li>)}</ul></details>}{!item.published_at && item.can_manage && <button type="button" onClick={() => publish(item.id)}>다음 기수에 공개</button>}</article>)}</div>
  </section>;
}

function RunbookSection({ user, users, events }: { user: User; users: User[]; events: EventItem[] }) {
  const [eventId, setEventId] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { if (!eventId && events[0]) setEventId(events[0].id); }, [eventId, events]);
  const { data } = useApiData<EventRunItem[]>(eventId ? `/operations/events/${eventId}/run-items` : "", [], Boolean(eventId));
  const canCreate = user.role !== "MEMBER";

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const values = new FormData(event.currentTarget); const plannedAt = String(values.get("planned_at") || "");
    try { await api(`/operations/events/${eventId}/run-items`, { method: "POST", ...jsonBody({ title: values.get("title"), planned_at: new Date(plannedAt).toISOString(), location_label: values.get("location_label") || null, assignee_id: values.get("assignee_id") || null, note: values.get("note") || null }) }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "운영 항목을 등록하지 못했습니다."); }
  }

  async function changeStatus(id: string, status: RunItemStatus) {
    try { await api(`/operations/run-items/${id}/status`, { method: "PATCH", ...jsonBody({ status }) }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "현장 상태를 변경하지 못했습니다."); }
  }

  return <section className="operations-section"><div className="section-heading"><span className="section-icon"><PlayCircle size={20} /></span><div><h2>행사 당일 운영</h2><p>시간순 진행표와 담당자의 준비·진행·문제 상태를 확인합니다.</p></div></div>
    <label className="event-picker">운영할 행사<select value={eventId} onChange={event => setEventId(event.target.value)}><option value="">행사 선택</option>{events.map(item => <option key={item.id} value={item.id}>{item.event_date} · {item.title}</option>)}</select></label>
    {canCreate && eventId && <form className="panel compact-form" onSubmit={create}><div className="form-grid"><label>운영 항목<input name="title" required /></label><label>예정 시각<input name="planned_at" type="datetime-local" required /></label><label>구체 장소<input name="location_label" placeholder="예: 본관 1층 정문" /></label><label>담당자<select name="assignee_id"><option value="">미정</option>{users.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="full">현장 메모<textarea name="note" rows={2} /></label></div><button type="submit">운영표에 추가</button></form>}
    <ErrorMessage value={error} />
    <div className="runbook">{eventId && data.length === 0 && <div className="empty">운영표가 비어 있습니다.</div>}{data.map(item => <article className={`run-item run-${item.status.toLowerCase()}`} key={item.id}><time>{new Date(item.planned_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</time><div><b>{item.title}</b><small>{item.location_label || "장소 미정"} · {item.assignee_name || "담당자 미정"}</small>{item.note && <p>{item.note}</p>}</div><select aria-label={`${item.title} 상태`} value={item.status} onChange={event => changeStatus(item.id, event.target.value as RunItemStatus)}>{Object.entries(runLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></article>)}</div>
  </section>;
}

function MapSection({ user, users, events }: { user: User; users: User[]; events: EventItem[] }) {
  const { data: maps } = useApiData<SchoolMap[]>("/operations/maps", []);
  const [mapId, setMapId] = useState(""); const [point, setPoint] = useState<{ x: number; y: number } | null>(null); const [error, setError] = useState("");
  useEffect(() => { if (!mapId && maps[0]) setMapId(maps[0].id); }, [mapId, maps]);
  const selected = maps.find(item => item.id === mapId);
  const { data: assignments } = useApiData<MapAssignment[]>(mapId ? `/operations/maps/${mapId}/assignments` : "", [], Boolean(mapId));
  const canCreate = user.role !== "MEMBER";

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = event.currentTarget; const values = new FormData(form);
    try { await api("/operations/maps", { method: "POST", body: values }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "학교 지도를 업로드하지 못했습니다."); }
  }

  function choosePoint(event: ReactMouseEvent<HTMLDivElement>) {
    if (!selected?.can_manage) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    setPoint({ x: (event.clientX - bounds.left) / bounds.width, y: (event.clientY - bounds.top) / bounds.height });
  }

  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!point) { setError("지도에서 활동 지점을 먼저 눌러 주세요."); return; } setError(""); const values = new FormData(event.currentTarget);
    const startsAt = String(values.get("starts_at") || ""); const endsAt = String(values.get("ends_at") || "");
    try { await api(`/operations/maps/${mapId}/assignments`, { method: "POST", ...jsonBody({ user_id: values.get("user_id"), label: values.get("label"), activity: values.get("activity"), x_ratio: point.x, y_ratio: point.y, starts_at: startsAt ? new Date(startsAt).toISOString() : null, ends_at: endsAt ? new Date(endsAt).toISOString() : null }) }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "활동 위치를 배정하지 못했습니다."); }
  }

  async function remove(id: string) {
    try { await api(`/operations/map-assignments/${id}`, { method: "DELETE" }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "위치 배정을 삭제하지 못했습니다."); }
  }

  return <section className="operations-section"><div className="section-heading"><span className="section-icon"><MapPinned size={20} /></span><div><h2>학교 지도 활동 위치</h2><p>지도에서 지점을 눌러 학생별 구체 장소와 역할을 배정합니다.</p></div></div>
    {canCreate && <form className="panel map-upload" onSubmit={upload}><label>지도 이름<input name="title" required placeholder="예: 축제 본관 배치도" /></label><label>관련 행사<select name="event_id" required><option value="">행사 선택</option>{events.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label>지도 이미지<input name="upload" type="file" accept="image/png,image/jpeg,image/webp" required /></label><button type="submit">비공개 지도 업로드</button></form>}
    <ErrorMessage value={error} />
    {maps.length > 0 && <label className="event-picker">표시할 지도<select value={mapId} onChange={event => { setMapId(event.target.value); setPoint(null); }}>{maps.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}
    {selected && <div className="map-workspace"><div className={`school-map ${selected.can_manage ? "editable" : ""}`} onClick={choosePoint} role={selected.can_manage ? "button" : undefined} tabIndex={selected.can_manage ? 0 : undefined} aria-label={selected.can_manage ? "활동 위치 선택" : "내 활동 위치 지도"}><img src={selected.image_url} alt={selected.title} />{assignments.map((item, index) => <button type="button" className="map-pin" key={item.id} style={{ left: `${item.x_ratio * 100}%`, top: `${item.y_ratio * 100}%` }} title={`${item.user_name}: ${item.activity}`}><span>{index + 1}</span></button>)}{point && <span className="map-pin pending" style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}>+</span>}</div>
      <div className="map-side">{selected.can_manage && <form className="panel assignment-form" onSubmit={assign}><h3>선택한 지점에 배정</h3><p className="muted">{point ? `가로 ${(point.x * 100).toFixed(1)}%, 세로 ${(point.y * 100).toFixed(1)}%` : "왼쪽 지도에서 지점을 눌러 주세요."}</p><label>학생<select name="user_id" required><option value="">선택</option>{users.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>장소 이름<input name="label" required placeholder="예: 정문 A 지점" /></label><label>구체적인 활동<input name="activity" required placeholder="예: 방문객 동선 안내" /></label><label>시작<input name="starts_at" type="datetime-local" /></label><label>종료<input name="ends_at" type="datetime-local" /></label><button type="submit" disabled={!point}>위치 배정</button></form>}
      <div className="assignment-list">{assignments.length === 0 && <div className="empty">배정된 위치가 없습니다.</div>}{assignments.map((item, index) => <article className="panel" key={item.id}><span className="pin-number">{index + 1}</span><div><b>{item.label}</b><small>{item.user_name}</small><p>{item.activity}</p>{item.starts_at && <small>{new Date(item.starts_at).toLocaleString("ko-KR")}</small>}</div>{item.can_manage && <button className="icon-button" type="button" onClick={() => remove(item.id)} aria-label={`${item.label} 배정 삭제`}>×</button>}</article>)}</div></div></div>}
    {!selected && <div className="empty">{canCreate ? "먼저 학교 지도 이미지를 업로드해 주세요." : "아직 배정된 활동 위치가 없습니다."}</div>}
  </section>;
}

export default function OperationsCenter({ user }: { user: User }) {
  const { data: events } = useApiData<EventItem[]>("/events", []);
  const canManage = user.role !== "MEMBER";
  const { data: users } = useApiData<User[]>("/users", [], canManage);
  return <><header className="page-header"><div><p className="eyebrow">학생회 운영 OS</p><h1>운영 센터</h1><p className="muted">결정부터 현장 실행, 다음 기수 인수인계까지 한 흐름으로 관리합니다.</p></div></header><div className="operations-center"><DecisionSection user={user} users={users} events={events} /><RunbookSection user={user} users={users} events={events} /><MapSection user={user} users={users} events={events} /><HandoverSection user={user} events={events} /></div></>;
}
