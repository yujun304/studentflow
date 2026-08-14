import { api, jsonBody } from "@/lib/api";
import type { Announcement, Archive, AttendanceRecord, AttendanceStatus, EventItem, Meeting, Notice, Role, Submission, SubmissionStatus, Task, TaskStatus, Team, User } from "@/types";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type ApiUser = { id: string; email: string; name: string; role: Role; department_id: string | null; term_id: string; grade: number | null; is_active: boolean };
type ApiDepartment = { id: string; name: string };
type ApiTask = { id: string; title: string; description?: string | null; type: string; status: "TODO" | "IN_PROGRESS" | "REVIEW" | "DONE" | "REJECTED"; due_at?: string | null; assigned_to_me: boolean; assignee_ids: string[] };
type ApiEvent = { id: string; title: string; description?: string | null; location?: string | null; event_date: string; starts_at?: string | null; ends_at?: string | null; status: string; manager_id?: string | null; participant_ids: string[] };
type ApiNotice = { id: string; title: string; content: string; type: "GENERAL" | "EVENT" | "SURVEY" | "FIRST_COME"; pinned: boolean; capacity?: number | null; waiting_enabled: boolean; created_at: string; recipient_ids: string[] };
type ApiSubmission = { id: string; task_id: string; task_title: string; submitted_by: string; submitted_by_name: string; status: "SUBMITTED" | "APPROVED" | "REJECTED"; version_id: string; submitted_at: string; files: Array<{ original_name: string }>; content?: string | null };
type ApiTeam = { id: string; name: string; description?: string | null; role_description?: string | null; leader_id?: string | null; member_ids: string[]; schedule_at?: string | null };
type ApiNotification = { id: string; title: string; content?: string | null; target_type?: string | null; target_id?: string | null; read_at?: string | null; created_at: string };

type AppContextValue = {
  authReady: boolean;
  signedIn: boolean;
  currentRole: Role;
  currentUser: User;
  users: User[];
  tasks: Task[];
  submissions: Submission[];
  events: EventItem[];
  announcements: Announcement[];
  attendance: AttendanceRecord[];
  teams: Team[];
  meetings: Meeting[];
  notices: Notice[];
  archives: Archive[];
  signIn: (email: string, password: string) => Promise<boolean>;
  signOut: () => Promise<void>;
  setRole: (role: Role) => void;
  createTask: (input: Pick<Task, "title" | "description" | "department" | "dueDate" | "priority">) => Promise<void>;
  updateTask: (taskId: string, input: Pick<Task, "title" | "description">) => Promise<void>;
  updateTaskStatus: (taskId: string, status: TaskStatus) => Promise<void>;
  submitTask: (taskId: string, fileName: string) => Promise<void>;
  reviewSubmission: (submissionId: string, status: Extract<SubmissionStatus, "APPROVED" | "REJECTED">, feedback?: string) => Promise<void>;
  publishAnnouncement: (input: Pick<Announcement, "title" | "body" | "target">) => Promise<void>;
  toggleEventJoin: (eventId: string) => Promise<void>;
  setAttendanceStatus: (userId: string, status: AttendanceStatus) => void;
  saveAttendance: () => Promise<void>;
  moveTeamMember: (fromTeamId: string, toTeamId: string, member: string) => Promise<void>;
  createMeeting: (input: Pick<Meeting, "title" | "date" | "summary"> & { attachment?: string }) => Promise<void>;
  markNoticeRead: (id: string) => Promise<void>;
  markAllNoticesRead: () => Promise<void>;
  sendNotification: (input: { title: string; content: string; recipientIds: string[] }) => Promise<void>;
  changeUserRole: (userId: string, role: Role) => Promise<void>;
};

const blankUser: User = { id: "", name: "", role: "MEMBER", department: "소속 미정", grade: "", initials: "" };
const AppContext = createContext<AppContextValue | null>(null);
const shortDateTime = (value?: string | null) => value ? new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "일정 미정";
const initials = (name: string) => name.slice(0, 2);
const statusToUi = (status: ApiTask["status"]): TaskStatus => status === "REVIEW" ? "IN_REVIEW" : status;
const statusToApi = (status: TaskStatus) => status === "IN_REVIEW" ? "REVIEW" : status;

export function AppProvider({ children }: { children: ReactNode }) {
  const [authReady, setAuthReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [apiUser, setApiUser] = useState<ApiUser | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [archives] = useState<Archive[]>([]);

  const loadData = useCallback(async (actor: ApiUser) => {
    const [apiUsers, departments, apiTasks, apiEvents, apiNotices, apiTeams, pending, apiNotifications] = await Promise.all([
      api<ApiUser[]>("/directory/users"),
      api<ApiDepartment[]>("/departments"),
      api<ApiTask[]>("/tasks"),
      api<ApiEvent[]>("/events"),
      api<ApiNotice[]>("/notices"),
      api<ApiTeam[]>("/teams").catch(() => []),
      actor.role === "MEMBER" ? Promise.resolve([] as ApiSubmission[]) : api<ApiSubmission[]>("/tasks/submissions/pending").catch(() => []),
      api<ApiNotification[]>("/notifications").catch(() => []),
    ]);
    const departmentMap = new Map(departments.map((item) => [item.id, item.name]));
    const mappedUsers = apiUsers.map<User>((user) => ({ id: user.id, name: user.name, role: user.role, department: user.department_id ? departmentMap.get(user.department_id) ?? "소속 미정" : "소속 미정", grade: user.grade ? `${user.grade}학년` : "", initials: initials(user.name) }));
    const userMap = new Map(mappedUsers.map((user) => [user.id, user]));
    setUsers(mappedUsers);
    setTasks(apiTasks.map<Task>((task) => ({ id: task.id, title: task.title, description: task.description ?? "설명이 없습니다.", department: task.assignee_ids.map((id) => userMap.get(id)?.department).find(Boolean) ?? "공통", assigneeId: task.assignee_ids[0] ?? actor.id, dueDate: task.due_at ? new Date(task.due_at).toISOString().slice(0, 16).replace("T", " ") : "마감일 없음", priority: "보통", status: statusToUi(task.status), submitted: task.status === "REVIEW" || task.status === "DONE" })));
    setEvents(apiEvents.map<EventItem>((event) => ({ id: event.id, title: event.title, date: new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric" }).format(new Date(`${event.event_date}T00:00:00`)), dateKey: event.event_date, time: event.starts_at ? event.starts_at.slice(0, 5) : "시간 미정", location: event.location ?? "장소 미정", department: "학생회", description: event.description ?? "행사 설명이 없습니다.", participants: event.participant_ids.map((id) => userMap.get(id)?.name).filter((name): name is string => Boolean(name)), participantIds: event.participant_ids, owner: event.manager_id ? userMap.get(event.manager_id)?.name ?? "담당자" : "담당자", status: event.status === "CLOSED" ? "마감" : "예정" })));
    setAnnouncements(apiNotices.map<Announcement>((notice) => ({ id: notice.id, title: notice.title, body: notice.content, author: "StudentFlow", createdAt: shortDateTime(notice.created_at), target: notice.recipient_ids.length ? `${notice.recipient_ids.length}명` : "학생회 전체", pinned: notice.pinned, read: false, application: notice.type === "FIRST_COME" && notice.capacity ? { capacity: notice.capacity, applied: 0, deadline: "공지에서 확인" } : undefined })));
    setSubmissions(pending.map<Submission>((item) => ({ id: item.id, taskId: item.task_id, studentName: item.submitted_by_name, taskTitle: item.task_title, fileName: item.files[0]?.original_name ?? item.content ?? "제출 내용", submittedAt: shortDateTime(item.submitted_at), status: item.status === "SUBMITTED" ? "PENDING" : item.status })));
    setTeams(apiTeams.map<Team>((team) => ({ id: team.id, name: team.name, purpose: team.description ?? team.role_description ?? "담당 업무 미정", members: team.member_ids.map((id) => userMap.get(id)?.name).filter((name): name is string => Boolean(name)), leader: team.leader_id ? userMap.get(team.leader_id)?.name ?? "" : "" })));
    const notificationLink = (notice: ApiNotification) => notice.target_type === "task" && notice.target_id ? `/tasks/${notice.target_id}` : notice.target_type === "event" && notice.target_id ? `/events/${notice.target_id}` : notice.target_type === "notice" && notice.target_id ? `/announcements/${notice.target_id}` : notice.target_type === "submission" ? "/submissions" : "/notifications";
    setNotices(apiNotifications.map<Notice>((notice) => ({ id: notice.id, title: notice.title, body: notice.content ?? "", time: shortDateTime(notice.created_at), read: Boolean(notice.read_at), link: notificationLink(notice) })));
    setMeetings([]);
    setAttendance([]);
  }, []);

  useEffect(() => {
    api<ApiUser>("/auth/me")
      .then(async (user) => { setApiUser(user); setSignedIn(true); await loadData(user); })
      .catch(() => setSignedIn(false))
      .finally(() => setAuthReady(true));
  }, [loadData]);

  const currentUser = useMemo(() => {
    if (!apiUser) return blankUser;
    return users.find((user) => user.id === apiUser.id) ?? { id: apiUser.id, name: apiUser.name, role: apiUser.role, department: "소속 미정", grade: apiUser.grade ? `${apiUser.grade}학년` : "", initials: initials(apiUser.name) };
  }, [apiUser, users]);

  const refresh = useCallback(async () => { if (apiUser) await loadData(apiUser); }, [apiUser, loadData]);
  const value: AppContextValue = {
    authReady, signedIn, currentRole: apiUser?.role ?? "MEMBER", currentUser, users, tasks, submissions, events, announcements, attendance, teams, meetings, notices, archives,
    async signIn(email, password) { try { const user = await api<ApiUser>("/auth/login", { method: "POST", ...jsonBody({ email, password }) }); setApiUser(user); setSignedIn(true); await loadData(user); return true; } catch { return false; } },
    async signOut() { await api("/auth/logout", { method: "POST" }).catch(() => undefined); setSignedIn(false); setApiUser(null); },
    setRole() {},
    async createTask(input) { await api("/tasks", { method: "POST", ...jsonBody({ title: input.title, description: input.description || null, type: "SIMPLE", due_at: input.dueDate ? new Date(input.dueDate.replace(" ", "T")).toISOString() : null, assignee_ids: [currentUser.id] }) }); await refresh(); },
    async updateTask(taskId, input) { await api(`/tasks/${taskId}`, { method: "PATCH", ...jsonBody(input) }); await refresh(); },
    async updateTaskStatus(taskId, status) { await api(`/tasks/${taskId}/status`, { method: "PATCH", ...jsonBody({ status: statusToApi(status) }) }); await refresh(); },
    async submitTask(taskId, fileName) { await api(`/tasks/${taskId}/submissions`, { method: "POST", ...jsonBody({ content: fileName ? `제출 파일: ${fileName}` : null }) }); await refresh(); },
    async reviewSubmission(submissionId, status, feedback) { await api(`/tasks/submissions/${submissionId}/review`, { method: "POST", ...jsonBody({ status, reason: feedback || null }) }); await refresh(); },
    async publishAnnouncement(input) { await api("/notices", { method: "POST", ...jsonBody({ title: input.title, content: input.body, type: "GENERAL", pinned: false, waiting_enabled: false, recipient_ids: users.map((user) => user.id) }) }); await refresh(); },
    async toggleEventJoin(eventId) { const event = events.find((item) => item.id === eventId); if (!event) return; const joined = event.participantIds?.includes(currentUser.id) ?? false; const ids = joined ? (event.participantIds ?? []).filter((id) => id !== currentUser.id) : [...(event.participantIds ?? []), currentUser.id]; await api(`/events/${eventId}/participants`, { method: "PUT", ...jsonBody(ids) }); await refresh(); },
    setAttendanceStatus(userId, status) { setAttendance((previous) => previous.map((item) => item.userId === userId ? { ...item, status } : item)); },
    async saveAttendance() {},
    async moveTeamMember(fromTeamId, toTeamId, member) { const fromTeam = teams.find((item) => item.id === fromTeamId); const toTeam = teams.find((item) => item.id === toTeamId); const person = users.find((item) => item.name === member); if (!fromTeam || !toTeam || !person) return; const ids = (team: Team) => team.members.map((name) => users.find((user) => user.name === name)?.id).filter((id): id is string => Boolean(id)); await Promise.all([api(`/teams/${fromTeam.id}`, { method: "PATCH", ...jsonBody({ name: fromTeam.name, description: fromTeam.purpose, member_ids: ids(fromTeam).filter((id) => id !== person.id) }) }), api(`/teams/${toTeam.id}`, { method: "PATCH", ...jsonBody({ name: toTeam.name, description: toTeam.purpose, member_ids: [...ids(toTeam), person.id] }) })]); await refresh(); },
    async createMeeting(input) { await api("/meeting-records", { method: "POST", ...jsonBody({ title: input.title, held_at: new Date(input.date).toISOString(), summary: input.summary, attendee_ids: [] }) }); await refresh(); },
    async markNoticeRead(id) { await api(`/notifications/${id}/read`, { method: "POST" }); setNotices((previous) => previous.map((item) => item.id === id ? { ...item, read: true } : item)); },
    async markAllNoticesRead() { await api("/notifications/read-all", { method: "POST" }); setNotices((previous) => previous.map((item) => ({ ...item, read: true }))); },
    async sendNotification(input) { await api("/notifications", { method: "POST", ...jsonBody({ title: input.title, content: input.content || null, recipient_ids: input.recipientIds }) }); await refresh(); },
    async changeUserRole(userId, role) { await api(`/users/${userId}`, { method: "PATCH", ...jsonBody({ role }) }); await refresh(); },
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp은 AppProvider 안에서 사용해야 합니다.");
  return context;
}
