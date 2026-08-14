import { FormEvent, ReactNode, useEffect, useState } from "react";
import {
  Bell,
  CalendarDays,
  CheckSquare2,
  ClipboardCheck,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  MoreHorizontal,
  UsersRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { api, jsonBody } from "./api";
import { activeSection, PAGE_PATHS, readPageId, type PageId } from "./navigation";
import type { Dashboard, Department, EventItem, Notice, SubmissionReview, SubmissionVersion, Task, TaskStatus, User } from "./types";
import { useApiData } from "./useApiData";
import TwoMonthCalendar from "./Calendar";
import TeamFormationForm from "./TeamFormationForm";
import UserAudienceSelect from "./UserAudienceSelect";
import OperationsCenter from "./OperationsCenter";

const roleName = { MEMBER: "일반 임원", DEPARTMENT_HEAD: "부장단", EXECUTIVE_BOARD: "회장단", TEACHER: "담당 선생님" };
const roleLabel = (user: User) => user.email === "test@example.com" ? "테스트 관리자" : roleName[user.role];
const statusName: Record<TaskStatus, string> = { TODO: "해야 할 일", IN_PROGRESS: "진행 중", REVIEW: "검토 중", DONE: "완료", REJECTED: "반려" };
const localDateTimeValue = (value?: string) => {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
};

function Login() {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try {
      await api<User>("/auth/login", { method: "POST", ...jsonBody({ email: form.get("email"), password: form.get("password") }) });
      window.location.replace(PAGE_PATHS.dashboard);
    }
    catch (e) { setError(e instanceof Error ? e.message : "로그인하지 못했습니다."); }
  }
  return <main className="login"><section className="login-intro"><div className="brand brand-static"><span className="brand-mark">S</span><span><b>StudentFlow</b><small>학생회 운영 플랫폼</small></span></div><div><p className="eyebrow">학생회 운영을 한곳에서</p><h1>오늘 해야 할 일을<br />바로 확인하세요.</h1><p>공지, 업무, 제출과 행사 일정을 놓치지 않도록 정리합니다.</p></div></section><form className="panel login-card" onSubmit={submit}><div className="login-heading"><span className="mobile-login-logo brand-mark">S</span><div><h2>로그인</h2><p className="muted">학교에서 안내받은 계정으로 시작하세요.</p></div></div><div className="demo-account"><strong>체험용 관리자 계정</strong><span>아이디 <code>test</code></span><span>비밀번호 <code>test</code></span></div><div className="demo-account"><strong>체험용 학생 계정</strong><span>아이디 <code>student1</code></span><span>비밀번호 <code>student1</code></span></div><label>아이디 또는 이메일<input name="email" type="text" required autoComplete="username" defaultValue="test" /></label><label>비밀번호<input name="password" type="password" required autoComplete="current-password" defaultValue="test" /></label>{error && <p className="error" role="alert">{error}</p>}<button className="login-button">StudentFlow 시작하기</button></form></main>;
}

function Shell({ user, page, children }: { user: User; page: PageId; children: ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  type NavLink = { page: ReturnType<typeof activeSection>; href: string; label: string; icon: LucideIcon };
  const links: NavLink[] = [
    { page: "dashboard" as const, href: PAGE_PATHS.dashboard, label: "대시보드", icon: LayoutDashboard },
    { page: "events" as const, href: PAGE_PATHS.events, label: "행사", icon: CalendarDays },
    { page: "tasks" as const, href: PAGE_PATHS.tasks, label: "업무", icon: CheckSquare2 },
    { page: "notices" as const, href: PAGE_PATHS.notices, label: "공지", icon: Megaphone },
    { page: "more" as const, href: PAGE_PATHS.more, label: "운영 센터", icon: MoreHorizontal },
  ];
  if (user.role !== "MEMBER") links.splice(4, 0, { page: "reviews", href: PAGE_PATHS.reviews, label: "제출 검토", icon: ClipboardCheck });
  if (user.role === "TEACHER") links.push({ page: "admin", href: PAGE_PATHS.admin, label: "사용자 관리", icon: UsersRound });
  const section = activeSection(page);
  const currentLabel = links.find(link => link.page === section)?.label ?? "StudentFlow";
  const logout = async () => { await api("/auth/logout", { method: "POST" }); window.location.replace(PAGE_PATHS.login); };
  const navigation = (compact = false) => links.map(link => { const Icon = link.icon; return <a className={section === link.page ? "active" : undefined} key={link.href} href={link.href} onClick={() => setMobileMenuOpen(false)}><Icon aria-hidden="true" size={compact ? 19 : 18} /><span>{link.label}</span></a>; });
  return <div className="app">
    <aside className="sidebar">
      <div className="sidebar-brand"><a className="brand" href={PAGE_PATHS.dashboard}><span className="brand-mark">S</span><span><b>StudentFlow</b><small>학생회 운영 플랫폼</small></span></a></div>
      <div className="term-card"><small>현재 운영</small><b>학생회 활동 기수</b></div>
      <p className="nav-label">운영 메뉴</p><nav>{navigation()}</nav>
      <div className="profile"><span className="avatar">{user.name.slice(0, 1)}</span><span><b>{user.name}</b><small>{roleLabel(user)}</small></span><button className="icon-button" type="button" onClick={logout} aria-label="로그아웃" title="로그아웃"><LogOut size={17} /></button></div>
    </aside>
    <header className="topbar"><div className="mobile-brand"><button className="icon-button" type="button" onClick={() => setMobileMenuOpen(true)} aria-label="메뉴 열기"><Menu size={22} /></button><a className="brand" href={PAGE_PATHS.dashboard}><span className="brand-mark">S</span><b>StudentFlow</b></a></div><div className="topbar-title"><small>StudentFlow · 학생회 운영</small><b>{currentLabel}</b></div><div className="topbar-actions"><span className="role-pill">{roleLabel(user)}</span><a className="icon-button" href={PAGE_PATHS.notices} aria-label="공지 확인"><Bell size={19} /></a><span className="avatar">{user.name.slice(0, 1)}</span></div></header>
    <main className="content">{children}</main>
    <nav className="mobile-nav">{navigation(true).slice(0, 5)}</nav>
    {mobileMenuOpen && <div className="mobile-drawer-backdrop" onMouseDown={() => setMobileMenuOpen(false)}><aside className="mobile-drawer" onMouseDown={event => event.stopPropagation()}><div className="drawer-head"><a className="brand" href={PAGE_PATHS.dashboard}><span className="brand-mark">S</span><b>StudentFlow</b></a><button className="icon-button" type="button" onClick={() => setMobileMenuOpen(false)} aria-label="메뉴 닫기"><X size={21} /></button></div><div className="term-card"><small>현재 운영</small><b>학생회 활동 기수</b></div><p className="nav-label">전체 메뉴</p><nav>{navigation()}</nav><button className="drawer-logout" type="button" onClick={logout}><LogOut size={17} />로그아웃</button></aside></div>}
  </div>;
}

function State({ title }: { title: string }) { return <div className="empty">{title}</div>; }
function DashboardPage({ user }: { user: User }) {
  const { data, isLoading, error } = useApiData<Dashboard | null>("/dashboard", null);
  if (isLoading) return <State title="대시보드를 불러오는 중…" />; if (error || !data) return <State title="대시보드를 불러오지 못했습니다." />;
  return <><header className="page-header"><div><p className="eyebrow">오늘의 흐름</p><h1>해야 할 일을 확인하세요</h1><p className="muted">마감이 가까운 업무와 새 공지를 먼저 모았습니다.</p></div><a className="button-link" href={PAGE_PATHS.tasks}>내 업무 보기</a></header><div className={`stats ${user.role === "MEMBER" ? "stats-three" : ""}`}><a href={PAGE_PATHS.events}><strong>{data.upcoming_events.length}</strong><span>다가오는 행사</span><small>일정 확인하기</small></a><a href={PAGE_PATHS.tasks}><strong>{data.due_tasks.length}</strong><span>마감 임박 업무</span><small>처리할 업무 보기</small></a><a href={PAGE_PATHS.notices}><strong>{data.unread_notices.length}</strong><span>읽지 않은 공지</span><small>새 공지 확인하기</small></a>{user.role !== "MEMBER" && <a href={PAGE_PATHS.reviews}><strong>{data.review_count}</strong><span>검토 대기</span><small>제출물 확인하기</small></a>}</div><TwoMonthCalendar /><div className="grid"><Panel title="다가오는 행사" link={PAGE_PATHS.events}>{data.upcoming_events.map(x => <Row key={x.id} title={x.title} meta={`${x.event_date} · ${x.location ?? "장소 미정"}`} />)}</Panel><Panel title="마감 임박 업무" link={PAGE_PATHS.tasks}>{data.due_tasks.map(x => <Row key={x.id} title={x.title} meta={x.due_at ? new Date(x.due_at).toLocaleString("ko-KR") : "마감일 없음"} />)}</Panel><Panel title="읽지 않은 공지" link={PAGE_PATHS.notices}>{data.unread_notices.map(x => <Row key={x.id} title={x.title} meta={x.pinned ? "중요 공지" : "새 공지"} />)}</Panel></div></>;
}
function Panel({ title, link, children }: { title: string; link: string; children: ReactNode }) { return <article className="panel"><div className="panel-head"><h2>{title}</h2><a href={link}>전체 보기</a></div><div>{children || <State title="표시할 항목이 없습니다." />}</div></article>; }
function Row({ title, meta }: { title: string; meta: string }) { return <div className="row"><b>{title}</b><small>{meta}</small></div>; }

function EventsPage() { const { data, isLoading } = useApiData<EventItem[]>("/events", []); return <ListPage title="행사와 캠페인" intro="참여 일정과 준비 업무를 확인하세요.">{isLoading ? <State title="불러오는 중…" /> : data.map(x => <article className="card" key={x.id}><span className="badge">{x.type === "EVENT" ? "행사" : "캠페인"}</span><h3>{x.title}</h3><p>{x.description || "설명이 없습니다."}</p><small>{x.event_date} · {x.location || "장소 미정"}</small></article>)}</ListPage>; }

function TaskEditorForm({ task }: { task?: Task }) {
  const [result, setResult] = useState("");
  const { data: users } = useApiData<User[]>("/users", []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setResult(""); const form = event.currentTarget; const data = new FormData(form);
    const dueAt = String(data.get("due_at") || "");
    try {
      await api(task ? `/tasks/${task.id}` : "/tasks", { method: task ? "PATCH" : "POST", ...jsonBody({ title: data.get("title"), description: data.get("description") || null, type: data.get("type"), due_at: dueAt ? new Date(dueAt).toISOString() : null, assignee_ids: data.getAll("assignee_ids") }) });
      window.location.replace(PAGE_PATHS.tasks);
    } catch (error) { setResult(error instanceof Error ? error.message : `업무를 ${task ? "수정" : "등록"}하지 못했습니다.`); }
  }
  const dueAt = localDateTimeValue(task?.due_at);
  return <form className="panel editor" onSubmit={submit}><div className="panel-head"><h2>{task ? "업무 수정" : "새 업무 등록"}</h2><span className="badge">관리자</span></div><div className="form-grid"><label>제목<input name="title" required maxLength={200} defaultValue={task?.title} /></label><label>유형<select name="type" defaultValue={task?.type ?? "SIMPLE"}><option value="SIMPLE">간단 업무</option><option value="SUBMISSION">제출 업무</option><option value="TEAM_FORMATION">조 편성</option></select></label><label className="full">설명<textarea name="description" rows={3} defaultValue={task?.description} /></label><label>마감일<input name="due_at" type="datetime-local" defaultValue={dueAt} /></label><UserAudienceSelect users={users} name="assignee_ids" label="담당자" defaultValue={task?.assignee_ids} required /></div>{result && <p className="error">{result}</p>}<div className="actions"><button type="submit">{task ? "수정 저장" : "업무 등록"}</button><a className="button-link secondary" href={PAGE_PATHS.tasks}>취소</a></div></form>;
}

function TaskEditorPage() {
  const taskId = new URLSearchParams(window.location.search).get("id"); const { data, isLoading } = useApiData<Task[]>("/tasks", []); const task = taskId ? data.find(item => item.id === taskId) : undefined;
  if (taskId && isLoading) return <State title="업무를 불러오는 중…" />;
  if (taskId && !task) return <State title="수정할 업무를 찾을 수 없습니다." />;
  if (task && !task.can_edit) return <Redirect to={PAGE_PATHS.tasks} />;
  return <ListPage title={task ? "업무 수정" : "업무 등록"} intro="업무 내용, 유형, 마감일과 담당자를 설정합니다."><TaskEditorForm task={task} /></ListPage>;
}

function SubmissionForm({ task }: { task: Task }) {
  const [open, setOpen] = useState(false); const [result, setResult] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setResult(""); const form = event.currentTarget; const data = new FormData(form); const file = data.get("file"); const content = String(data.get("content") || "").trim();
    if (!content && (!(file instanceof File) || file.size === 0)) { setResult("제출 내용이나 파일을 추가해 주세요."); return; }
    try {
      const version = await api<SubmissionVersion>(`/tasks/${task.id}/submissions`, { method: "POST", ...jsonBody({ content: content || null }) });
      if (file instanceof File && file.size > 0) { const upload = new FormData(); upload.append("upload", file); await api(`/tasks/submission-versions/${version.id}/files`, { method: "POST", body: upload }); }
      form.reset(); window.location.reload();
    } catch (error) { setResult(error instanceof Error ? error.message : "제출하지 못했습니다."); }
  }
  if (!open) return <button className="secondary" type="button" onClick={() => setOpen(true)}>내용·파일 제출</button>;
  return <form className="submission-form" onSubmit={submit}><label>제출 내용<textarea name="content" rows={3} /></label><label>첨부 파일<input name="file" type="file" /></label>{result && <p className="form-message">{result}</p>}<div className="actions"><button type="submit">제출</button><button className="secondary" type="button" onClick={() => setOpen(false)}>닫기</button></div></form>;
}

function TasksPage({ user }: { user: User }) {
  const { data } = useApiData<Task[]>("/tasks", []); const [error, setError] = useState(""); const [activeStatus, setActiveStatus] = useState<TaskStatus>("TODO");
  async function changeStatus(id: string, status: TaskStatus) {
    try { await api(`/tasks/${id}/status`, { method: "PATCH", ...jsonBody({ status }) }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "업무 상태를 바꾸지 못했습니다."); }
  }
  return <ListPage title="업무 보드" intro="상태별 업무를 확인하고 제출과 진행 상태를 처리합니다." action={user.role !== "MEMBER" ? <a className="button-link" href={PAGE_PATHS.taskEditor}>새 업무 등록</a> : undefined}>{error && <p className="error">{error}</p>}<div className="status-tabs" role="tablist" aria-label="업무 상태">{(Object.keys(statusName) as TaskStatus[]).map(status => <button type="button" role="tab" aria-selected={activeStatus === status} className={activeStatus === status ? "active" : ""} key={status} onClick={() => setActiveStatus(status)}>{statusName[status]} <span>{data.filter(x => x.status === status).length}</span></button>)}</div><div className="kanban">{(Object.keys(statusName) as TaskStatus[]).map(status => <section key={status} className={activeStatus === status ? "mobile-active" : ""}><h2>{statusName[status]} <span>{data.filter(x => x.status === status).length}</span></h2>{data.filter(x => x.status === status).length === 0 && <State title="이 상태의 업무가 없습니다." />}{data.filter(x => x.status === status).map(task => <article className="task-card" key={task.id}><div className="task-title"><b>{task.title}</b>{task.type !== "SIMPLE" && <span className="badge">{task.type === "SUBMISSION" ? "제출" : "조 편성"}</span>}</div><p>{task.description || "설명 없음"}</p>{task.due_at && <small>{new Date(task.due_at).toLocaleString("ko-KR")} 마감</small>}<label className="status-select">상태 변경<select value={task.status} onChange={event => changeStatus(task.id, event.target.value as TaskStatus)}>{Object.entries(statusName).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><div className="actions">{task.can_edit && <a className="button-link secondary" href={`${PAGE_PATHS.taskEditor}?id=${task.id}`}>업무 수정</a>}</div>{task.type === "SUBMISSION" && task.assigned_to_me && <SubmissionForm task={task} />}{task.type === "TEAM_FORMATION" && task.assigned_to_me && <TeamFormationForm task={task} />}</article>)}</section>)}</div></ListPage>;
}

function NoticeEditorForm({ notice }: { notice?: Notice }) {
  const [noticeType, setNoticeType] = useState<Notice["type"]>(notice?.type ?? "GENERAL"); const [result, setResult] = useState("");
  const { data: users } = useApiData<User[]>("/users", []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setResult(""); const form = event.currentTarget; const data = new FormData(form); const recipients = data.getAll("recipient_ids");
    if (!recipients.length) { setResult("공지 수신자를 한 명 이상 선택해 주세요."); return; }
    try {
      await api(notice ? `/notices/${notice.id}` : "/notices", { method: notice ? "PATCH" : "POST", ...jsonBody({ title: data.get("title"), content: data.get("content"), type: data.get("type"), pinned: data.get("pinned") === "on", capacity: noticeType === "FIRST_COME" ? Number(data.get("capacity")) : null, waiting_enabled: data.get("waiting_enabled") === "on", recipient_ids: recipients }) });
      window.location.replace(PAGE_PATHS.notices);
    } catch (error) { setResult(error instanceof Error ? error.message : `공지를 ${notice ? "수정" : "등록"}하지 못했습니다.`); }
  }
  return <form className="panel editor" onSubmit={submit}><div className="panel-head"><h2>{notice ? "공지 수정" : "새 공지 등록"}</h2><span className="badge">관리자</span></div><div className="form-grid"><label>제목<input name="title" required maxLength={200} defaultValue={notice?.title} /></label><label>유형<select name="type" value={noticeType} onChange={event => setNoticeType(event.target.value as Notice["type"])}><option value="GENERAL">일반</option><option value="EVENT">행사</option><option value="SURVEY">참여 조사</option><option value="FIRST_COME">선착순</option></select></label><label className="full">내용<textarea name="content" required rows={5} defaultValue={notice?.content} /></label>{noticeType === "FIRST_COME" && <><label>정원<input name="capacity" type="number" min={1} required defaultValue={notice?.capacity} /></label><label className="check"><input name="waiting_enabled" type="checkbox" defaultChecked={notice?.waiting_enabled} /> 대기 신청 허용</label></>}<UserAudienceSelect users={users} name="recipient_ids" label="수신자" defaultValue={notice?.recipient_ids} required /><label className="check"><input name="pinned" type="checkbox" defaultChecked={notice?.pinned} /> 중요 공지로 고정</label></div>{result && <p className="error">{result}</p>}<div className="actions"><button type="submit">{notice ? "수정 저장" : "공지 등록"}</button><a className="button-link secondary" href={PAGE_PATHS.notices}>취소</a></div></form>;
}

function NoticeEditorPage() {
  const noticeId = new URLSearchParams(window.location.search).get("id"); const { data, isLoading } = useApiData<Notice[]>("/notices", []); const notice = noticeId ? data.find(item => item.id === noticeId) : undefined;
  if (noticeId && isLoading) return <State title="공지를 불러오는 중…" />;
  if (noticeId && !notice) return <State title="수정할 공지를 찾을 수 없습니다." />;
  if (notice && !notice.can_edit) return <Redirect to={PAGE_PATHS.notices} />;
  return <ListPage title={notice ? "공지 수정" : "공지 등록"} intro="공지 내용, 유형과 수신자를 설정합니다."><NoticeEditorForm notice={notice} /></ListPage>;
}

function NoticesPage({ user }: { user: User }) {
  const { data } = useApiData<Notice[]>("/notices", []); const [error, setError] = useState("");
  async function apply(id: string) {
    try { await api(`/notices/${id}/apply`, { method: "POST" }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "신청하지 못했습니다."); }
  }
  return <ListPage title="공지사항" intro="등록된 공지를 확인하고 필요한 응답을 처리합니다.">{error && <p className="error">{error}</p>}{user.role !== "MEMBER" && <div className="page-actions"><a className="button-link" href={PAGE_PATHS.noticeEditor}>새 공지 등록</a></div>}{data.map(notice => <article className="panel notice" key={notice.id}>{notice.pinned && <span className="badge">고정</span>}<h2>{notice.title}</h2><p>{notice.content}</p><div className="actions">{notice.type === "FIRST_COME" && <button onClick={() => apply(notice.id)}>선착순 신청</button>}{notice.can_edit && <a className="button-link secondary" href={`${PAGE_PATHS.noticeEditor}?id=${notice.id}`}>수정</a>}</div></article>)}</ListPage>;
}

function ReviewsPage() {
  const { data, isLoading } = useApiData<SubmissionReview[]>("/tasks/submissions/pending", []); const [error, setError] = useState("");
  async function review(id: string, status: "APPROVED" | "REJECTED", reason?: string) {
    try { await api(`/tasks/submissions/${id}/review`, { method: "POST", ...jsonBody({ status, reason: reason || null }) }); window.location.reload(); }
    catch (value) { setError(value instanceof Error ? value.message : "검토 결과를 저장하지 못했습니다."); }
  }
  if (isLoading) return <ListPage title="검토할 사항" intro="제출된 업무를 확인하고 승인하거나 반려합니다."><State title="검토 목록을 불러오는 중…" /></ListPage>;
  return <ListPage title="검토할 사항" intro="제출된 내용과 파일을 확인하고 승인하거나 반려합니다.">{error && <p className="error">{error}</p>}{data.length === 0 ? <State title="검토 대기 제출물이 없습니다." /> : data.map(item => <ReviewCard key={item.id} item={item} onReview={(status, reason) => review(item.id, status, reason)} />)}</ListPage>;
}

function ReviewCard({ item, onReview }: { item: SubmissionReview; onReview: (status: "APPROVED" | "REJECTED", reason?: string) => void }) {
  const [reason, setReason] = useState("");
  return <article className="panel review-card"><div className="panel-head"><div><h2>{item.task_title}</h2><small>{item.submitted_by_name} · {item.version}차 제출 · {new Date(item.submitted_at).toLocaleString("ko-KR")}</small></div><span className="badge">검토 대기</span></div>{item.content && <p className="submission-content">{item.content}</p>}{item.files.length > 0 && <div className="file-list">{item.files.map(file => <a key={file.id} href={`/api/v1/tasks/files/${file.id}`}>{file.original_name} <small>{Math.ceil(file.size / 1024)}KB</small></a>)}</div>}{item.teams.length > 0 && <div className="review-teams">{item.teams.map(team => <section key={team.id}><div><b>{team.name}</b><span>{team.role_description || "담당 역할 미정"}</span></div><small>조장: {team.leader_name || "미정"} · 조원: {team.member_names.join(", ")}</small><small>일정: {new Date(team.schedule_at).toLocaleString("ko-KR")}</small>{team.description && <p>{team.description}</p>}</section>)}</div>}<label>반려 사유<textarea value={reason} onChange={event => setReason(event.target.value)} rows={2} placeholder="반려할 때 반드시 입력하세요." /></label><div className="actions"><button type="button" onClick={() => onReview("APPROVED")}>승인</button><button className="danger" type="button" onClick={() => onReview("REJECTED", reason)}>반려</button></div></article>;
}

function UserCreateForm({ termId }: { termId: string }) {
  const [role, setRole] = useState<User["role"]>("MEMBER");
  const [result, setResult] = useState("");
  const { data: departments } = useApiData<Department[]>("/departments", []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResult("");
    const form = event.currentTarget;
    const data = new FormData(form);
    const grade = String(data.get("grade") || "");
    try {
      await api("/users", {
        method: "POST",
        ...jsonBody({
          email: data.get("email"),
          name: data.get("name"),
          password: data.get("password"),
          role,
          department_id: data.get("department_id") || null,
          term_id: termId,
          grade: grade ? Number(grade) : null,
        }),
      });
      form.reset();
      setRole("MEMBER");
      window.location.reload();
    } catch (error) {
      setResult(error instanceof Error ? error.message : "계정을 등록하지 못했습니다.");
    }
  }

  return (
    <form className="panel editor" onSubmit={submit}>
      <div className="panel-head"><h2>새 계정 등록</h2><span className="badge">담당 선생님</span></div>
      <div className="form-grid">
        <label>이름<input name="name" required maxLength={100} /></label>
        <label>이메일<input name="email" type="email" required /></label>
        <label>초기 비밀번호<input name="password" type="password" minLength={8} required /></label>
        <label>권한<select name="role" value={role} onChange={(event) => setRole(event.target.value as User["role"])}><option value="MEMBER">일반 임원</option><option value="DEPARTMENT_HEAD">부장단</option><option value="EXECUTIVE_BOARD">회장단</option><option value="TEACHER">담당 선생님</option></select></label>
        <label>학년<select name="grade" required={role !== "TEACHER"}><option value="">{role === "TEACHER" ? "해당 없음" : "학년 선택"}</option><option value="1">1학년</option><option value="2">2학년</option><option value="3">3학년</option></select></label>
        <label>부서<select name="department_id"><option value="">소속 없음</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
      </div>
      {result && <p className="form-message">{result}</p>}
      <div className="actions"><button type="submit">계정 등록</button></div>
    </form>
  );
}

function AdminPage({ currentUser }: { currentUser: User }) {
  const { data } = useApiData<User[]>("/users", []);
  return <ListPage title="사용자 관리" intro="계정을 등록하고 역할, 학년과 소속 상태를 확인합니다."><UserCreateForm termId={currentUser.term_id} /><div className="panel table">{data.map(user => <div className="user-row" key={user.id}><div><b>{user.name}</b><small>{user.email}</small></div><span>{user.grade ? `${user.grade}학년` : "학년 없음"}</span><span>{roleLabel(user)}</span><span className={user.is_active ? "active" : "inactive"}>{user.is_active ? "활성" : "비활성"}</span></div>)}</div></ListPage>;
}
function ListPage({ title, intro, action, children }: { title: string; intro: string; action?: ReactNode; children: ReactNode }) { return <><header className="page-header"><div><h1>{title}</h1><p className="muted">{intro}</p></div>{action}</header><div className="list">{children}</div></>; }

function Redirect({ to }: { to: string }) {
  useEffect(() => window.location.replace(to), [to]);
  return <main className="center">페이지를 이동하는 중…</main>;
}

export default function App() {
  const page = readPageId();
  const { data: user, isLoading, error } = useApiData<User | null>("/auth/me", null);
  if (page === "login") return user ? <Redirect to={PAGE_PATHS.dashboard} /> : <Login />;
  if (isLoading) return <main className="center">StudentFlow를 여는 중…</main>;
  if (error || !user) return <Redirect to={PAGE_PATHS.login} />;
  if ((page === "task-editor" || page === "notice-editor" || page === "reviews") && user.role === "MEMBER") return <Redirect to={PAGE_PATHS.dashboard} />;
  if (page === "admin" && user.role !== "TEACHER") return <Redirect to={PAGE_PATHS.dashboard} />;
  const content: Record<Exclude<PageId, "login">, ReactNode> = {
    dashboard: <DashboardPage user={user} />,
    events: <EventsPage />,
    tasks: <TasksPage user={user} />,
    "task-editor": <TaskEditorPage />,
    notices: <NoticesPage user={user} />,
    "notice-editor": <NoticeEditorPage />,
    reviews: <ReviewsPage />,
    more: <OperationsCenter user={user} />,
    admin: <AdminPage currentUser={user} />,
  };
  return <Shell user={user} page={page}>{content[page]}</Shell>;
}
