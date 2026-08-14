export type Role = "MEMBER" | "DEPARTMENT_HEAD" | "EXECUTIVE_BOARD" | "TEACHER";
export interface User { id: string; email: string; name: string; role: Role; department_id: string | null; term_id: string; grade: 1 | 2 | 3 | null; is_active: boolean }
export interface Department { id: string; name: string; description?: string }
export interface EventItem { id: string; title: string; type: "EVENT" | "CAMPAIGN"; description?: string; location?: string; event_date: string; starts_at?: string; ends_at?: string; status: string }
export type TaskStatus = "TODO" | "IN_PROGRESS" | "REVIEW" | "DONE" | "REJECTED";
export type TaskType = "SIMPLE" | "SUBMISSION" | "TEAM_FORMATION";
export interface Task { id: string; title: string; description?: string; type: TaskType; status: TaskStatus; event_id?: string; due_at?: string; assigned_to_me: boolean; assignee_ids: string[]; can_edit: boolean }
export interface Notice { id: string; title: string; content: string; type: "GENERAL" | "EVENT" | "SURVEY" | "FIRST_COME"; pinned: boolean; capacity?: number; waiting_enabled: boolean; created_at: string; recipient_ids: string[]; can_edit: boolean }
export interface SubmissionVersion { id: string; submission_id: string; version: number; content?: string; created_at: string }
export interface SubmissionFile { id: string; original_name: string; mime_type: string; size: number }
export interface TeamReview { id: string; name: string; description?: string; role_description?: string; leader_id?: string; leader_name?: string; member_ids: string[]; member_names: string[]; schedule_at: string }
export interface SubmissionReview { id: string; task_id: string; task_title: string; submitted_by: string; submitted_by_name: string; status: "SUBMITTED" | "APPROVED" | "REJECTED"; version_id: string; version: number; content?: string; submitted_at: string; files: SubmissionFile[]; teams: TeamReview[] }
export interface CalendarItem { id: string; source: "EVENT" | "CAMPAIGN" | "TASK_DEADLINE" | "SUBMISSION_DEADLINE" | "TEAM_FORMATION_DEADLINE" | "TEAM_REMINDER" | "PERSONAL"; title: string; description?: string; starts_at: string; ends_at?: string; color: string; editable: boolean }
export interface Dashboard { upcoming_events: EventItem[]; due_tasks: Task[]; unread_notices: Notice[]; review_count: number }
export type DecisionStatus = "OPEN" | "DONE" | "CANCELLED";
export interface DecisionCard { id: string; title: string; detail?: string; owner_id: string; owner_name: string; due_at?: string; event_id?: string; meeting_record_id?: string; task_id?: string; status: DecisionStatus; completed_at?: string; can_manage: boolean; created_at: string }
export interface HandoverGuide { id: string; term_id: string; term_name: string; event_id?: string; title: string; summary: string; what_worked?: string; pitfalls?: string; checklist?: string; published_at?: string; can_manage: boolean; created_at: string }
export type RunItemStatus = "PLANNED" | "READY" | "IN_PROGRESS" | "DONE" | "ISSUE";
export interface EventRunItem { id: string; event_id: string; title: string; planned_at: string; location_label?: string; assignee_id?: string; assignee_name?: string; status: RunItemStatus; note?: string; sequence: number; can_manage: boolean }
export interface SchoolMap { id: string; term_id: string; event_id?: string; title: string; image_url: string; can_manage: boolean; created_at: string }
export interface MapAssignment { id: string; map_id: string; user_id: string; user_name: string; label: string; activity: string; x_ratio: number; y_ratio: number; starts_at?: string; ends_at?: string; can_manage: boolean }
export interface MeetingRecord { id: string; title: string; held_at: string; event_id?: string }
