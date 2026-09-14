import { api, jsonBody } from "@/lib/api";
import type {
  Announcement,
  Archive,
  AttendanceRecord,
  AttendanceStatus,
  EventItem,
  Meeting,
  Notice,
  Role,
  Task,
  TaskStatus,
  TaskType,
  Team,
  User,
} from "@/types";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type ApiUser = {
  id: string;
  email: string;
  name: string;
  role: Role;
  department_id: string | null;
  term_id: string;
  grade: number | null;
  is_active: boolean;
};
type ApiDepartment = { id: string; name: string };
type ApiTask = {
  id: string;
  title: string;
  description?: string | null;
  type: TaskType;
  status: "TODO" | "IN_PROGRESS" | "REVIEW" | "DONE" | "REJECTED";
  due_at?: string | null;
  assigned_to_me: boolean;
  assignee_ids: string[];
  can_edit: boolean;
  event_id?: string | null;
  operation_days?: number | null;
  operation_dates?: string[] | null;
  teams_per_day?: number | null;
  people_per_team?: number | null;
  team_role_description?: string | null;
  team_requirements?: Array<{ name: string; people_count: number; role_description: string; start_time?: string | null; end_time?: string | null }> | null;
};
type ApiEvent = {
  id: string;
  title: string;
  description?: string | null;
  location?: string | null;
  event_date: string;
  starts_at?: string | null;
  ends_at?: string | null;
  status: string;
  manager_id?: string | null;
  participant_ids: string[];
  can_manage: boolean;
};
type ApiNotice = {
  id: string;
  title: string;
  content: string;
  type: "GENERAL" | "EVENT" | "SURVEY" | "FIRST_COME";
  pinned: boolean;
  capacity?: number | null;
  waiting_enabled: boolean;
  created_at: string;
  recipient_ids: string[];
  can_edit: boolean;
};
type ApiNotification = {
  id: string;
  title: string;
  content?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  read_at?: string | null;
  created_at: string;
};
type ApiTeam = {
  id: string;
  event_id?: string | null;
  task_id?: string | null;
  name: string;
  description?: string | null;
  role_description?: string | null;
  leader_id?: string | null;
  member_ids: string[];
  schedule_at?: string | null;
};

type AppContextValue = {
  authReady: boolean;
  signedIn: boolean;
  currentRole: Role;
  currentUser: User;
  testAccounts: User[];
  users: User[];
  tasks: Task[];
  events: EventItem[];
  announcements: Announcement[];
  attendance: AttendanceRecord[];
  teams: Team[];
  meetings: Meeting[];
  notices: Notice[];
  archives: Archive[];
  signIn: (email: string, password: string) => Promise<boolean>;
  signOut: () => Promise<void>;
  switchTestAccount: (userId: string) => Promise<void>;
  setRole: (role: Role) => void;
  createTask: (
    input: Pick<
      Task,
      "title" | "description" | "type" | "department" | "dueDate" | "priority"
    >
  ) => Promise<void>;
  updateTask: (
    taskId: string,
    input: Pick<Task, "title" | "description">
  ) => Promise<void>;
  updateTaskStatus: (taskId: string, status: TaskStatus) => Promise<void>;
  deleteTask: (taskId: string) => Promise<void>;
  submitTask: (taskId: string, file: File) => Promise<void>;
  publishAnnouncement: (
    input: Pick<Announcement, "title" | "body" | "target">
  ) => Promise<void>;
  deleteAnnouncement: (announcementId: string) => Promise<void>;
  toggleEventJoin: (eventId: string) => Promise<void>;
  updateEvent: (
    eventId: string,
    input: {
      title: string;
      description: string;
      location: string;
      eventDate: string;
      startsAt: string;
      endsAt: string;
    }
  ) => Promise<void>;
  deleteEvent: (eventId: string) => Promise<void>;
  setAttendanceStatus: (userId: string, status: AttendanceStatus) => void;
  saveAttendance: () => Promise<void>;
  createMeeting: (
    input: Pick<Meeting, "title" | "date" | "summary"> & { attachment?: string }
  ) => Promise<void>;
  markNoticeRead: (id: string) => Promise<void>;
  markAllNoticesRead: () => Promise<void>;
  sendNotification: (input: {
    title: string;
    content: string;
    recipientIds: string[];
  }) => Promise<void>;
  changeUserRole: (userId: string, role: Role) => Promise<void>;
};

const blankUser: User = {
  id: "",
  name: "",
  role: "MEMBER",
  department: "소속 미정",
  grade: "",
  initials: "",
};
const AppContext = createContext<AppContextValue | null>(null);
const shortDateTime = (value?: string | null) =>
  value
    ? new Intl.DateTimeFormat("ko-KR", {
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value))
    : "일정 미정";
const initials = (name: string) => name.slice(0, 2);
const statusToUi = (status: ApiTask["status"]): TaskStatus =>
  status === "REVIEW" ? "DONE" : status === "REJECTED" ? "TODO" : status;

export function AppProvider({ children }: { children: ReactNode }) {
  const [authReady, setAuthReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [apiUser, setApiUser] = useState<ApiUser | null>(null);
  const [testAccountIds, setTestAccountIds] = useState<string[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [archives] = useState<Archive[]>([]);

  const loadData = useCallback(async (actor: ApiUser) => {
    const [
      apiUsers,
      departments,
      apiTasks,
      apiEvents,
      apiNotices,
      apiNotifications,
      apiTestAccounts,
      apiTeams,
    ] = await Promise.all([
      api<ApiUser[]>("/directory/users"),
      api<ApiDepartment[]>("/departments"),
      api<ApiTask[]>("/tasks"),
      api<ApiEvent[]>("/events"),
      api<ApiNotice[]>("/notices"),
      api<ApiNotification[]>("/notifications").catch(() => []),
      api<ApiUser[]>("/auth/test-accounts").catch(() => []),
      api<ApiTeam[]>("/teams").catch(() => []),
    ]);
    const departmentMap = new Map(
      departments.map(item => [item.id, item.name])
    );
    const mappedUsers = apiUsers.map<User>(user => ({
      id: user.id,
      name: user.name,
      role: user.role,
      department: user.department_id
        ? (departmentMap.get(user.department_id) ?? "소속 미정")
        : "소속 미정",
      grade: user.grade ? `${user.grade}학년` : "",
      initials: initials(user.name),
    }));
    const userMap = new Map(mappedUsers.map(user => [user.id, user]));
    setUsers(mappedUsers);
    setTestAccountIds(apiTestAccounts.map(user => user.id));
    setTasks(
      apiTasks.map<Task>(task => ({
        id: task.id,
        title: task.title,
        description: task.description ?? "설명이 없습니다.",
        type: task.type,
        department:
          task.assignee_ids
            .map(id => userMap.get(id)?.department)
            .find(Boolean) ?? "공통",
        assigneeId: task.assignee_ids[0] ?? actor.id,
        assignedToMe: task.assigned_to_me,
        canEdit: task.can_edit,
        dueDate: task.due_at
          ? new Date(task.due_at).toISOString().slice(0, 16).replace("T", " ")
          : "마감일 없음",
        priority: "보통",
        status: statusToUi(task.status),
        submitted: task.status === "REVIEW" || task.status === "DONE",
        eventId: task.event_id ?? undefined,
        operationDays: task.operation_days ?? undefined,
        operationDates: task.operation_dates ?? undefined,
        teamsPerDay: task.teams_per_day ?? undefined,
        peoplePerTeam: task.people_per_team ?? undefined,
        teamRoleDescription: task.team_role_description ?? undefined,
        teamRequirements: task.team_requirements?.map(item => ({
          name: item.name,
          peopleCount: item.people_count,
          roleDescription: item.role_description,
          startTime: item.start_time ?? undefined,
          endTime: item.end_time ?? undefined,
        })),
      }))
    );
    setEvents(
      apiEvents.map<EventItem>(event => {
        const startsAt = event.starts_at?.slice(0, 5);
        const endsAt = event.ends_at?.slice(0, 5);
        return {
          id: event.id,
          title: event.title,
          date: new Intl.DateTimeFormat("ko-KR", {
            month: "long",
            day: "numeric",
          }).format(new Date(`${event.event_date}T00:00:00`)),
          dateKey: event.event_date,
          time: startsAt
            ? endsAt
              ? `${startsAt} - ${endsAt}`
              : startsAt
            : "시간 미정",
          location: event.location ?? "장소 미정",
          department: "학생회 전체",
          description: event.description ?? "행사 설명이 없습니다.",
          participants: event.participant_ids
            .map(id => userMap.get(id)?.name)
            .filter((name): name is string => Boolean(name)),
          participantIds: event.participant_ids,
          owner: event.manager_id
            ? (userMap.get(event.manager_id)?.name ?? "담당자 확인 중")
            : "담당자 미정",
          status:
            event.status === "DONE"
              ? "마감"
              : event.status === "OPEN"
                ? "모집 중"
                : "예정",
          canManage: event.can_manage,
        };
      })
    );
    setAnnouncements(
      apiNotices.map<Announcement>(notice => ({
        id: notice.id,
        title: notice.title,
        body: notice.content,
        author: "StudentFlow",
        createdAt: shortDateTime(notice.created_at),
        target: notice.recipient_ids.length
          ? `${notice.recipient_ids.length}명`
          : "학생회 전체",
        pinned: notice.pinned,
        read: false,
        canEdit: notice.can_edit,
        application:
          notice.type === "FIRST_COME" && notice.capacity
            ? {
                capacity: notice.capacity,
                applied: 0,
                deadline: "공지에서 확인",
              }
            : undefined,
      }))
    );
    const notificationLink = (notice: ApiNotification) =>
      notice.target_type === "task" && notice.target_id
        ? `/tasks/${notice.target_id}`
        : notice.target_type === "proposal" && notice.target_id
          ? `/proposals/${notice.target_id}`
        : notice.target_type === "notice" && notice.target_id
            ? `/announcements/${notice.target_id}`
            : "/notifications";
    setNotices(
      apiNotifications.map<Notice>(notice => ({
        id: notice.id,
        title: notice.title,
        body: notice.content ?? "",
        time: shortDateTime(notice.created_at),
        read: Boolean(notice.read_at),
        link: notificationLink(notice),
      }))
    );
    setTeams(
      apiTeams.map<Team>(team => ({
        id: team.id,
        name: team.name,
        purpose: team.description ?? "공동 활동",
        members: team.member_ids.map(id => userMap.get(id)?.name ?? "알 수 없음"),
        memberIds: team.member_ids,
        leader: team.leader_id
          ? (userMap.get(team.leader_id)?.name ?? "확인 중")
          : "미지정",
        leaderId: team.leader_id ?? undefined,
        roleDescription: team.role_description ?? undefined,
        scheduleAt: team.schedule_at ?? undefined,
        eventId: team.event_id ?? undefined,
        taskId: team.task_id ?? undefined,
      }))
    );
    setMeetings([]);
    setAttendance([]);
  }, []);

  useEffect(() => {
    api<ApiUser>("/auth/me")
      .then(async user => {
        setApiUser(user);
        setSignedIn(true);
        await loadData(user);
      })
      .catch(() => setSignedIn(false))
      .finally(() => setAuthReady(true));
  }, [loadData]);

  const currentUser = useMemo(() => {
    if (!apiUser) return blankUser;
    return (
      users.find(user => user.id === apiUser.id) ?? {
        id: apiUser.id,
        name: apiUser.name,
        role: apiUser.role,
        department: "소속 미정",
        grade: apiUser.grade ? `${apiUser.grade}학년` : "",
        initials: initials(apiUser.name),
      }
    );
  }, [apiUser, users]);
  const testAccounts = useMemo(
    () => users.filter(user => testAccountIds.includes(user.id)),
    [testAccountIds, users]
  );

  const refresh = useCallback(async () => {
    if (apiUser) await loadData(apiUser);
  }, [apiUser, loadData]);
  const value: AppContextValue = {
    authReady,
    signedIn,
    currentRole: apiUser?.role ?? "MEMBER",
    currentUser,
    testAccounts,
    users,
    tasks,
    events,
    announcements,
    attendance,
    teams,
    meetings,
    notices,
    archives,
    async signIn(email, password) {
      try {
        const user = await api<ApiUser>("/auth/login", {
          method: "POST",
          ...jsonBody({ email, password }),
        });
        setApiUser(user);
        setSignedIn(true);
        await loadData(user);
        return true;
      } catch {
        return false;
      }
    },
    async signOut() {
      await api("/auth/logout", { method: "POST" }).catch(() => undefined);
      setSignedIn(false);
      setApiUser(null);
    },
    async switchTestAccount(userId) {
      const user = await api<ApiUser>(`/auth/test-switch/${userId}`, {
        method: "POST",
      });
      setApiUser(user);
      setSignedIn(true);
      await loadData(user);
    },
    setRole() {},
    async createTask(input) {
      await api("/tasks", {
        method: "POST",
        ...jsonBody({
          title: input.title,
          description: input.description || null,
          type: input.type,
          due_at: input.dueDate
            ? new Date(input.dueDate.replace(" ", "T")).toISOString()
            : null,
          assignee_ids: [currentUser.id],
        }),
      });
      await refresh();
    },
    async updateTask(taskId, input) {
      await api(`/tasks/${taskId}`, { method: "PATCH", ...jsonBody(input) });
      await refresh();
    },
    async updateTaskStatus(taskId, status) {
      await api(`/tasks/${taskId}/status`, {
        method: "PATCH",
        ...jsonBody({ status }),
      });
      await refresh();
    },
    async deleteTask(taskId) {
      await api(`/tasks/${taskId}`, { method: "DELETE" });
      await refresh();
    },
    async submitTask(taskId, file) {
      const version = await api<{ id: string }>(`/tasks/${taskId}/submissions`, {
        method: "POST",
        ...jsonBody({ content: `제출 파일: ${file.name}` }),
      });
      const formData = new FormData();
      formData.append("upload", file);
      await api(`/tasks/submission-versions/${version.id}/files`, {
        method: "POST",
        body: formData,
      });
      await refresh();
    },
    async publishAnnouncement(input) {
      await api("/notices", {
        method: "POST",
        ...jsonBody({
          title: input.title,
          content: input.body,
          type: "GENERAL",
          pinned: false,
          waiting_enabled: false,
          recipient_ids: users.map(user => user.id),
        }),
      });
      await refresh();
    },
    async deleteAnnouncement(announcementId) {
      await api(`/notices/${announcementId}`, { method: "DELETE" });
      await refresh();
    },
    async toggleEventJoin(eventId) {
      const event = events.find(item => item.id === eventId);
      if (!event) return;
      const joined = event.participantIds?.includes(currentUser.id) ?? false;
      const ids = joined
        ? (event.participantIds ?? []).filter(id => id !== currentUser.id)
        : [...(event.participantIds ?? []), currentUser.id];
      await api(`/events/${eventId}/participants`, {
        method: "PUT",
        ...jsonBody(ids),
      });
      await refresh();
    },
    async updateEvent(eventId, input) {
      await api(`/events/${eventId}`, {
        method: "PATCH",
        ...jsonBody({
          title: input.title,
          description: input.description || null,
          location: input.location || null,
          event_date: input.eventDate,
          starts_at: input.startsAt || null,
          ends_at: input.endsAt || null,
        }),
      });
      await refresh();
    },
    async deleteEvent(eventId) {
      await api(`/events/${eventId}`, { method: "DELETE" });
      await refresh();
    },
    setAttendanceStatus(userId, status) {
      setAttendance(previous =>
        previous.map(item =>
          item.userId === userId ? { ...item, status } : item
        )
      );
    },
    async saveAttendance() {},
    async createMeeting(input) {
      await api("/meeting-records", {
        method: "POST",
        ...jsonBody({
          title: input.title,
          held_at: new Date(input.date).toISOString(),
          summary: input.summary,
          attendee_ids: [],
        }),
      });
      await refresh();
    },
    async markNoticeRead(id) {
      await api(`/notifications/${id}/read`, { method: "POST" });
      setNotices(previous =>
        previous.map(item => (item.id === id ? { ...item, read: true } : item))
      );
    },
    async markAllNoticesRead() {
      await api("/notifications/read-all", { method: "POST" });
      setNotices(previous => previous.map(item => ({ ...item, read: true })));
    },
    async sendNotification(input) {
      await api("/notifications", {
        method: "POST",
        ...jsonBody({
          title: input.title,
          content: input.content || null,
          recipient_ids: input.recipientIds,
        }),
      });
      await refresh();
    },
    async changeUserRole(userId, role) {
      await api(`/users/${userId}`, { method: "PATCH", ...jsonBody({ role }) });
      await refresh();
    },
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp은 AppProvider 안에서 사용해야 합니다.");
  return context;
}
