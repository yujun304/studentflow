export type ProposalStatus = "DISCUSSING" | "RE_REVIEW" | "CONFIRMED";
export type FeedbackCategory = "STRENGTH" | "CONCERN" | "CHANGE" | "NEW_IDEA";

export interface ProposalAttachment {
  id: string;
  original_name: string;
  mime_type: string;
  size: number;
  download_path: string;
  purpose: "GENERAL" | "IDEA_FILE" | "MEETING_AUDIO";
}

export interface ProposalVersion {
  id: string;
  version_number: number;
  title: string;
  description: string;
  topic?: string;
  change_summary?: string;
  author_id: string;
  author_name: string;
  created_at: string;
  attachments: ProposalAttachment[];
}

export interface ProposalFeedback {
  id: string;
  version_number: number;
  author_id: string;
  author_name: string;
  category: FeedbackCategory;
  content: string;
  is_mine: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProposalSummary {
  strengths: string[];
  concerns: string[];
  changes: string[];
  new_ideas: string[];
  open_questions: string[];
  provider: "ai" | "fallback";
  generated_at: string;
}

export interface ProposalListItem {
  id: string;
  title: string;
  description: string;
  topic?: string;
  status: ProposalStatus;
  planning_stage: ProposalPlanningStage;
  current_version: number;
  author_name: string;
  feedback_count: number;
  has_current_user_feedback: boolean;
  recommendation_count: number;
  recommended_by_me: boolean;
  feedback_required: boolean;
  required_feedback_recommendation_threshold: number;
  is_current_user_feedback_required: boolean;
  required_feedback_count: number;
  completed_required_feedback_count: number;
  updated_at: string;
}

export interface ProposalDetail extends ProposalListItem {
  current: ProposalVersion;
  versions: ProposalVersion[];
  feedback: ProposalFeedback[];
  summary: ProposalSummary | null;
  can_confirm: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export type ProposalPlanningStage =
  | "DISCUSSING"
  | "MEETING_AGENDA"
  | "MEETING_COMPLETED"
  | "FINAL_PLAN_DRAFT"
  | "PENDING_TEACHER_REVIEW"
  | "REVISION_REQUESTED"
  | "REJECTED"
  | "APPROVED"
  | "ASSIGNING_TEAMS"
  | "SCHEDULED";

export interface ProposalExecutionPlan {
  id: string;
  author_id: string;
  status: "DRAFT" | "IN_REVIEW" | "CHANGES_REQUESTED" | "REJECTED" | "APPROVED";
  version: number;
  review_note?: string | null;
  can_submit: boolean;
  can_review: boolean;
  can_convert: boolean;
  team_task_id?: string | null;
  team_manager_id?: string | null;
}

export interface ProposalWorkflow {
  stage: ProposalPlanningStage;
  brief_plan: Record<string, unknown> | null;
  meeting_audio: ProposalAttachment | null;
  meeting_transcript: string | null;
  meeting_notes: Record<string, unknown> | null;
  final_plan: Record<string, unknown> | null;
  plan: ProposalExecutionPlan | null;
  can_manage: boolean;
  can_promote: boolean;
  audio_extensions: string[];
  audio_max_bytes: number;
  can_transcribe: boolean;
  can_auto_process: boolean;
  can_generate_brief: boolean;
}

export const planningStageLabel: Record<ProposalPlanningStage, string> = {
  DISCUSSING: "의견 수렴",
  MEETING_AGENDA: "부장 회의 안건",
  MEETING_COMPLETED: "회의 정리 완료",
  FINAL_PLAN_DRAFT: "최종 기획서 작성",
  PENDING_TEACHER_REVIEW: "교사 검토 중",
  REVISION_REQUESTED: "수정 요청",
  REJECTED: "반려",
  APPROVED: "승인 완료",
  ASSIGNING_TEAMS: "조 편성 중",
  SCHEDULED: "일정 반영 완료",
};

export function isProposalCompleted(item: Pick<ProposalListItem, "planning_stage">) {
  return item.planning_stage === "SCHEDULED" || item.planning_stage === "REJECTED";
}

export const statusLabel: Record<ProposalStatus, string> = {
  DISCUSSING: "의견 수렴 중",
  RE_REVIEW: "재검토 중",
  CONFIRMED: "확정",
};

export const categoryLabel: Record<FeedbackCategory, string> = {
  STRENGTH: "좋은 점",
  CONCERN: "걱정되는 점",
  CHANGE: "바꾸고 싶은 점",
  NEW_IDEA: "새로운 아이디어",
};

export function proposalIdFromPath(
  pathname = window.location.pathname
): string | null {
  return pathname.match(/^\/proposals\/([^/]+)\/?$/)?.[1] ?? null;
}
