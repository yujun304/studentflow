/** StudentFlow | 학기 운영 보드: 업무 우선, 문장형 상태, 조용한 파란 신호색 */
export type Role = "MEMBER" | "DEPARTMENT_HEAD" | "EXECUTIVE_BOARD" | "TEACHER";
export type TaskStatus = "TODO" | "IN_PROGRESS" | "DONE";
export type TaskType = "SIMPLE" | "SUBMISSION" | "TEAM_FORMATION";
export type AttendanceStatus = "ATTEND" | "LATE" | "ABSENT" | "EXCUSED";
export interface User {
  id: string;
  name: string;
  role: Role;
  department: string;
  grade: string;
  initials: string;
}
export type TeamRequirement = {
  name: string;
  peopleCount: number;
  roleDescription: string;
  startTime?: string;
  endTime?: string;
  operationDates?: string[];
};
export type TeamFormationDraft = {
  name: string;
  scheduleAt: string;
  leaderId?: string;
  memberIds: string[];
  requiredPeople: number;
  roleDescription?: string;
};
export interface Task {
  id: string;
  title: string;
  description: string;
  type: TaskType;
  department: string;
  assigneeId: string;
  assignedToMe?: boolean;
  canEdit?: boolean;
  dueDate: string;
  priority: "높음" | "보통" | "낮음";
  status: TaskStatus;
  submitted: boolean;
  attachmentHint?: string;
  eventId?: string;
  operationDays?: number;
  operationDates?: string[];
  teamsPerDay?: number;
  peoplePerTeam?: number;
  teamRoleDescription?: string;
  teamRequirements?: TeamRequirement[];
  formationDraft?: TeamFormationDraft[];
}
export interface EventItem {
  id: string;
  title: string;
  date: string;
  dateKey?: string;
  time: string;
  location: string;
  department: string;
  description: string;
  capacity?: number;
  participants: string[];
  participantIds?: string[];
  owner: string;
  status: "모집 중" | "마감" | "예정";
  canManage?: boolean;
}
export interface Announcement {
  id: string;
  title: string;
  body: string;
  author: string;
  createdAt: string;
  target: string;
  pinned: boolean;
  read: boolean;
  canEdit?: boolean;
  application?: {
    capacity: number;
    applied: number;
    deadline: string;
    status?: "ACCEPTED" | "WAITING";
  };
}
export interface AttendanceRecord {
  userId: string;
  name: string;
  department: string;
  status: AttendanceStatus;
}
export interface Team {
  id: string;
  name: string;
  purpose: string;
  members: string[];
  memberIds: string[];
  leader: string;
  leaderId?: string;
  roleDescription?: string;
  scheduleAt?: string;
  eventId?: string;
  taskId?: string;
}
export interface Meeting {
  id: string;
  title: string;
  date: string;
  author: string;
  summary: string;
  attachments: string[];
}
export interface Notice {
  id: string;
  title: string;
  body: string;
  time: string;
  read: boolean;
  link: string;
}
export interface Archive {
  id: string;
  semester: string;
  name: string;
  members: number;
  note: string;
  locked: boolean;
}
