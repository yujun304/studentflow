/** StudentFlow | 학기 운영 보드: 업무 우선, 문장형 상태, 조용한 파란 신호색 */
export type Role = "MEMBER" | "DEPARTMENT_HEAD" | "EXECUTIVE_BOARD" | "TEACHER";
export type TaskStatus = "TODO" | "IN_PROGRESS" | "IN_REVIEW" | "DONE" | "REJECTED";
export type SubmissionStatus = "DRAFT" | "PENDING" | "APPROVED" | "REJECTED";
export type AttendanceStatus = "ATTEND" | "LATE" | "ABSENT" | "EXCUSED";
export interface User { id: string; name: string; role: Role; department: string; grade: string; initials: string; }
export interface Task { id: string; title: string; description: string; department: string; assigneeId: string; dueDate: string; priority: "높음" | "보통" | "낮음"; status: TaskStatus; submitted: boolean; attachmentHint?: string; }
export interface Submission { id: string; taskId: string; studentName: string; taskTitle: string; fileName: string; submittedAt: string; status: SubmissionStatus; reviewer?: string; feedback?: string; }
export interface EventItem { id: string; title: string; date: string; time: string; location: string; department: string; description: string; capacity: number; participants: string[]; owner: string; status: "모집 중" | "마감" | "예정"; }
export interface Announcement { id: string; title: string; body: string; author: string; createdAt: string; target: string; pinned: boolean; read: boolean; application?: { capacity: number; applied: number; deadline: string }; }
export interface AttendanceRecord { userId: string; name: string; department: string; status: AttendanceStatus; }
export interface Team { id: string; name: string; purpose: string; members: string[]; leader: string; }
export interface Meeting { id: string; title: string; date: string; author: string; summary: string; attachments: string[]; }
export interface Notice { id: string; title: string; body: string; time: string; read: boolean; link: string; }
export interface Archive { id: string; semester: string; name: string; members: number; note: string; locked: boolean; }
