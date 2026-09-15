import {
  CalendarPlus,
  CheckCircle2,
  FileText,
  MessageCircle,
  Plus,
  Pencil,
  RefreshCw,
  Send,
  ShieldCheck,
  Star,
  Trash2,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  AppModal,
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  TextArea,
  TextInput,
  SelectField,
} from "@/components/primitives";
import { useApp } from "@/contexts/AppContext";
import { api, jsonBody } from "@/lib/api";
import { Link } from "@/components/MpaLink";

type SortMode = "popular" | "recent";
type MeetingTimeSlot = "MORNING" | "LUNCH" | "AFTER_SCHOOL";
type MeetingDraft = { meetingDate: string; meetingTimeSlot: MeetingTimeSlot; meetingTime: string };
type CommunityComment = {
  id: string;
  author_id: string | null;
  author_name: string;
  content: string;
  is_anonymous: boolean;
  is_mine: boolean;
  created_at: string;
};
type EventPlanForm = {
  purpose: string;
  target_participants: string;
  schedule_plan: string;
  location_plan: string;
  program_plan: string;
  role_plan: string;
  budget_plan: string;
  safety_plan: string;
  operation_days: number;
  operation_dates: string[];
  teams_per_day: number;
  people_per_team: number;
  team_role_description: string;
  team_requirements: Array<{
    name: string;
    people_count: number;
    role_description: string;
    operation_dates?: string[];
  }>;
  team_manager_id: string;
  poster_manager_id: string;
  poster_required: boolean;
};
type PlanStatus = "DRAFT" | "IN_REVIEW" | "CHANGES_REQUESTED" | "REJECTED" | "APPROVED";
type CommunityEventPlan = {
  purpose: string | null;
  target_participants: string | null;
  schedule_plan: string | null;
  location_plan: string | null;
  program_plan: string | null;
  role_plan: string | null;
  budget_plan: string | null;
  safety_plan: string | null;
  operation_days: number | null;
  operation_dates: string[] | null;
  teams_per_day: number | null;
  people_per_team: number | null;
  team_role_description: string | null;
  team_manager_id: string | null;
  poster_manager_id: string | null;
  poster_required: boolean;
  team_requirements: EventPlanForm["team_requirements"] | null;
  id: string;
  post_id: string;
  author_id: string;
  status: PlanStatus;
  version: number;
  submitted_at: string | null;
  approved_at: string | null;
  review_note: string | null;
  can_edit: boolean;
  can_submit: boolean;
  can_review: boolean;
  can_convert: boolean;
  created_at: string;
  updated_at: string;
};
type PlanSuggestion = {
  id: string;
  section: (typeof planFields)[number]["key"];
  proposed_content: string;
  reason: string | null;
  status: "OPEN" | "ADOPTED" | "REJECTED";
  author_name: string;
  created_at: string;
};
type PlanWorkspace = {
  plan: CommunityEventPlan;
  contributors: Array<{ user_id: string; name: string }>;
  suggestions: PlanSuggestion[];
  revisions: Array<{ id: string; version: number; editor_name: string; created_at: string }>;
};
type CommunityPost = {
  id: string;
  title: string;
  content: string;
  author_id: string | null;
  author_name: string;
  is_anonymous: boolean;
  is_mine: boolean;
  created_at: string;
  comment_count: number;
  comments: CommunityComment[];
  recommendation_count: number;
  recommended_by_me: boolean;
  test_recommendation_bonus: number;
  agenda_at: string | null;
  plan_writer_id: string | null;
  plan_writer_name: string | null;
  meeting_date: string | null;
  meeting_time_slot: MeetingTimeSlot | null;
  meeting_time: string | null;
  can_assign_plan_writer: boolean;
  can_schedule_meeting: boolean;
  can_write_plan: boolean;
  plan: CommunityEventPlan | null;
  converted_event_id: string | null;
  converted_at: string | null;
};

const managerRoles = new Set(["DEPARTMENT_HEAD", "EXECUTIVE_BOARD", "TEACHER"]);
const emptyPlanForm: EventPlanForm = {
  purpose: "",
  target_participants: "",
  schedule_plan: "",
  location_plan: "",
  program_plan: "",
  role_plan: "",
  budget_plan: "",
  safety_plan: "",
  operation_days: 1,
  operation_dates: [""],
  teams_per_day: 2,
  people_per_team: 3,
  team_role_description: "",
  team_requirements: [
    { name: "1조", people_count: 3, role_description: "", operation_dates: [] },
    { name: "2조", people_count: 3, role_description: "", operation_dates: [] },
  ],
  team_manager_id: "",
  poster_manager_id: "",
  poster_required: true,
};
const planFields = [
  { key: "purpose", label: "행사 목적", placeholder: "이 행사가 필요한 이유와 기대하는 변화를 적어 주세요.", maxLength: 2000 },
  { key: "target_participants", label: "참여 대상", placeholder: "예: 전교생, 1학년 희망자 60명", maxLength: 1000 },
  { key: "schedule_plan", label: "일시와 진행 시간", placeholder: "예: 10월 16일 점심시간, 준비 20분·진행 40분", maxLength: 1000 },
  { key: "location_plan", label: "장소와 이동 동선", placeholder: "사용할 장소와 참가자 이동 방법을 적어 주세요.", maxLength: 1000 },
  { key: "program_plan", label: "세부 프로그램", placeholder: "준비부터 마무리까지 순서대로 구체적으로 적어 주세요.", maxLength: 5000 },
  { key: "role_plan", label: "역할 분담", placeholder: "기획, 조 편성, 포스터, 진행 등 필요한 역할과 할 일을 적어 주세요.", maxLength: 3000 },
  { key: "budget_plan", label: "예산과 준비물", placeholder: "필요한 물품, 수량, 예상 비용을 적어 주세요.", maxLength: 2000 },
  { key: "safety_plan", label: "안전과 돌발 상황 대처", placeholder: "안전 담당, 혼잡 방지, 우천 시 대안 등을 적어 주세요.", maxLength: 2000 },
] as const satisfies ReadonlyArray<{
  key: "purpose" | "target_participants" | "schedule_plan" | "location_plan" | "program_plan" | "role_plan" | "budget_plan" | "safety_plan";
  label: string;
  placeholder: string;
  maxLength: number;
}>;
const planStatusLabels: Record<PlanStatus, string> = {
  DRAFT: "공동 작성 중",
  IN_REVIEW: "선생님 승인 대기",
  CHANGES_REQUESTED: "수정 요청",
  REJECTED: "반려",
  APPROVED: "승인 완료",
};
const meetingTimeSlotLabels: Record<MeetingTimeSlot, string> = {
  MORNING: "아침시간",
  LUNCH: "점심시간",
  AFTER_SCHOOL: "방과후",
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function orderPosts(posts: CommunityPost[], sort: SortMode) {
  return [...posts].sort((left, right) => {
    if (Boolean(left.agenda_at) !== Boolean(right.agenda_at)) {
      return left.agenda_at ? -1 : 1;
    }
    if (sort === "popular" && left.recommendation_count !== right.recommendation_count) {
      return right.recommendation_count - left.recommendation_count;
    }
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });
}

export default function CommunityPage() {
  const { currentRole, currentUser, users } = useApp();
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [sort, setSort] = useState<SortMode>("popular");
  const [createOpen, setCreateOpen] = useState(false);
  const [conversionTarget, setConversionTarget] = useState<CommunityPost | null>(null);
  const [editPostTarget, setEditPostTarget] = useState<CommunityPost | null>(null);
  const [editPostForm, setEditPostForm] = useState({ title: "", content: "", isAnonymous: false });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyPostId, setBusyPostId] = useState<string | null>(null);
  const [writerDrafts, setWriterDrafts] = useState<Record<string, string>>({});
  const [meetingDrafts, setMeetingDrafts] = useState<Record<string, MeetingDraft>>({});
  const [busyCommentPostId, setBusyCommentPostId] = useState<string | null>(null);
  const [expandedPostIds, setExpandedPostIds] = useState<Set<string>>(new Set());
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({});
  const [commentAnonymous, setCommentAnonymous] = useState<Record<string, boolean>>({});
  const [commentErrors, setCommentErrors] = useState<Record<string, string>>({});
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editCommentContent, setEditCommentContent] = useState("");
  const [editCommentAnonymous, setEditCommentAnonymous] = useState(true);
  const [busyCommentId, setBusyCommentId] = useState<string | null>(null);
  const [planTarget, setPlanTarget] = useState<CommunityPost | null>(null);
  const [planForm, setPlanForm] = useState<EventPlanForm>(emptyPlanForm);
  const [planWorkspace, setPlanWorkspace] = useState<PlanWorkspace | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [suggestionForm, setSuggestionForm] = useState({
    section: "purpose" as PlanSuggestion["section"],
    proposedContent: "",
    reason: "",
  });
  const [planSaving, setPlanSaving] = useState(false);
  const [planError, setPlanError] = useState("");
  const [formError, setFormError] = useState("");
  const [form, setForm] = useState({
    title: "",
    content: "",
    isAnonymous: true,
  });
  const [eventForm, setEventForm] = useState({
    eventDate: "",
    location: "",
    startsAt: "",
    endsAt: "",
  });

  const canConvert = managerRoles.has(currentRole);
  const activePlan = planWorkspace?.plan ?? planTarget?.plan ?? null;
  const canEditPlan = Boolean(planTarget?.can_write_plan || activePlan?.can_edit);
  const isPlanCoordinator = activePlan
    ? activePlan.author_id === currentUser.id
    : canEditPlan && currentRole !== "TEACHER";
  const studentCouncilUsers = users.filter(user => user.role !== "TEACHER");
  const meetingWriters = users.filter(user =>
    ["DEPARTMENT_HEAD", "EXECUTIVE_BOARD"].includes(user.role)
  );
  const totalRecommendations = useMemo(
    () => posts.reduce((sum, post) => sum + post.recommendation_count, 0),
    [posts]
  );

  async function load(showSpinner = true, selectedSort = sort) {
    if (showSpinner) setLoading(true);
    setError("");
    try {
      setPosts(await api<CommunityPost[]>(`/community?sort=${selectedSort}`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "행사 아이디어를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(true, sort);
  }, [sort]);

  function resetForm() {
    setForm({ title: "", content: "", isAnonymous: true });
    setFormError("");
  }

  async function createPost() {
    if (!form.title.trim()) {
      setFormError("해보고 싶은 행사를 짧게 적어 주세요.");
      return;
    }
    if (form.content.trim().length < 10) {
      setFormError("행사 목적과 진행 모습을 알 수 있도록 전체 개요를 10자 이상 적어 주세요.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const created = await api<CommunityPost>("/community", {
        method: "POST",
        ...jsonBody({
          kind: "SUGGESTION",
          title: form.title,
          content: form.content,
          is_anonymous: form.isAnonymous,
        }),
      });
      setPosts(current => orderPosts([created, ...current], sort));
      setCreateOpen(false);
      resetForm();
      toast.success("행사 아이디어를 게시판에 올렸습니다.");
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : "아이디어를 올리지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleRecommendation(post: CommunityPost) {
    setBusyPostId(post.id);
    try {
      const updated = await api<CommunityPost>(`/community/${post.id}/recommendation`, {
        method: "PUT",
      });
      setPosts(current =>
        orderPosts(current.map(item => (item.id === updated.id ? updated : item)), sort)
      );
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : "추천을 바꾸지 못했습니다.");
    } finally {
      setBusyPostId(null);
    }
  }

  async function setTestRecommendationCount(post: CommunityPost, count: number) {
    setBusyPostId(post.id);
    try {
      const updated = await api<CommunityPost>(
        `/community/${post.id}/test-recommendation-count`,
        { method: "PUT", ...jsonBody({ count: Math.max(0, count) }) }
      );
      setPosts(current =>
        orderPosts(current.map(item => (item.id === updated.id ? updated : item)), sort)
      );
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : "테스트 추천 수를 바꾸지 못했습니다.");
    } finally {
      setBusyPostId(null);
    }
  }

  async function assignPlanWriter(post: CommunityPost, writerId: string) {
    if (!writerId) return;
    const previousWriterId = writerDrafts[post.id] ?? post.plan_writer_id ?? "";
    setWriterDrafts(current => ({ ...current, [post.id]: writerId }));
    setBusyPostId(post.id);
    try {
      const updated = await api<CommunityPost>(`/community/${post.id}/plan-writer`, {
        method: "PUT",
        ...jsonBody({ writer_id: writerId }),
      });
      setPosts(current =>
        orderPosts(current.map(item => (item.id === updated.id ? updated : item)), sort)
      );
      setWriterDrafts(current => ({ ...current, [post.id]: updated.plan_writer_id ?? "" }));
      toast.success(`${updated.plan_writer_name ?? "작성자"}님을 기획서 작성자로 지정했습니다.`);
    } catch (caught) {
      setWriterDrafts(current => ({ ...current, [post.id]: previousWriterId }));
      toast.error(caught instanceof Error ? caught.message : "기획서 작성자를 지정하지 못했습니다.");
    } finally {
      setBusyPostId(null);
    }
  }

  function meetingDraftFor(post: CommunityPost): MeetingDraft {
    return meetingDrafts[post.id] ?? {
      meetingDate: post.meeting_date ?? "",
      meetingTimeSlot: post.meeting_time_slot ?? "AFTER_SCHOOL",
      meetingTime: post.meeting_time?.slice(0, 5) ?? "",
    };
  }

  function updateMeetingDraft(post: CommunityPost, patch: Partial<MeetingDraft>) {
    setMeetingDrafts(current => ({
      ...current,
      [post.id]: { ...meetingDraftFor(post), ...patch },
    }));
  }

  async function saveMeetingSchedule(post: CommunityPost) {
    const draft = meetingDraftFor(post);
    if (!draft.meetingDate) {
      toast.error("부장회의 날짜를 선택해 주세요.");
      return;
    }
    setBusyPostId(post.id);
    try {
      const updated = await api<CommunityPost>(`/community/${post.id}/meeting-schedule`, {
        method: "PUT",
        ...jsonBody({
          meeting_date: draft.meetingDate,
          meeting_time_slot: draft.meetingTimeSlot,
          meeting_time: draft.meetingTime || null,
        }),
      });
      setPosts(current =>
        orderPosts(current.map(item => (item.id === updated.id ? updated : item)), sort)
      );
      setMeetingDrafts(current => ({
        ...current,
        [post.id]: {
          meetingDate: updated.meeting_date ?? "",
          meetingTimeSlot: updated.meeting_time_slot ?? "AFTER_SCHOOL",
          meetingTime: updated.meeting_time?.slice(0, 5) ?? "",
        },
      }));
      toast.success("부장회의 일정을 저장하고 부장단에 알렸습니다.");
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : "부장회의 일정을 저장하지 못했습니다.");
    } finally {
      setBusyPostId(null);
    }
  }

  function openPostEdit(post: CommunityPost) {
    setEditPostTarget(post);
    setEditPostForm({
      title: post.title,
      content: post.content,
      isAnonymous: post.is_anonymous,
    });
    setFormError("");
  }

  async function savePostEdit() {
    if (!editPostTarget) return;
    if (!editPostForm.title.trim() || editPostForm.content.trim().length < 10) {
      setFormError("제목과 10자 이상의 행사 전체 개요가 필요합니다.");
      return;
    }
    setSaving(true);
    try {
      const updated = await api<CommunityPost>(`/community/${editPostTarget.id}`, {
        method: "PATCH",
        ...jsonBody({
          title: editPostForm.title,
          content: editPostForm.content,
          is_anonymous: editPostForm.isAnonymous,
        }),
      });
      setPosts(current =>
        orderPosts(current.map(item => (item.id === updated.id ? updated : item)), sort)
      );
      setEditPostTarget(null);
      toast.success("게시물을 수정했습니다.");
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : "게시물을 수정하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function deletePost(post: CommunityPost) {
    if (!window.confirm(`“${post.title}” 게시물을 삭제할까요?`)) return;
    setBusyPostId(post.id);
    try {
      await api(`/community/${post.id}`, { method: "DELETE" });
      setPosts(current => current.filter(item => item.id !== post.id));
      toast.success("게시물을 삭제했습니다.");
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : "게시물을 삭제하지 못했습니다.");
    } finally {
      setBusyPostId(null);
    }
  }

  function toggleComments(postId: string) {
    setExpandedPostIds(current => {
      const next = new Set(current);
      if (next.has(postId)) next.delete(postId);
      else next.add(postId);
      return next;
    });
  }

  async function submitComment(post: CommunityPost) {
    const content = commentDrafts[post.id]?.trim() ?? "";
    if (!content) {
      setCommentErrors(current => ({ ...current, [post.id]: "의견을 입력해 주세요." }));
      return;
    }

    setBusyCommentPostId(post.id);
    setCommentErrors(current => ({ ...current, [post.id]: "" }));
    try {
      const created = await api<CommunityComment>(`/community/${post.id}/comments`, {
        method: "POST",
        ...jsonBody({
          content,
          is_anonymous: commentAnonymous[post.id] ?? true,
        }),
      });
      setPosts(current =>
        current.map(item =>
          item.id === post.id
            ? {
                ...item,
                comment_count: item.comment_count + 1,
                comments: [...item.comments, created],
              }
            : item
        )
      );
      setCommentDrafts(current => ({ ...current, [post.id]: "" }));
      setCommentAnonymous(current => ({ ...current, [post.id]: true }));
      setExpandedPostIds(current => new Set(current).add(post.id));
    } catch (caught) {
      setCommentErrors(current => ({
        ...current,
        [post.id]: caught instanceof Error ? caught.message : "의견을 남기지 못했습니다.",
      }));
    } finally {
      setBusyCommentPostId(null);
    }
  }

  function startCommentEdit(comment: CommunityComment) {
    setEditingCommentId(comment.id);
    setEditCommentContent(comment.content);
    setEditCommentAnonymous(comment.is_anonymous);
  }

  async function saveCommentEdit(post: CommunityPost, comment: CommunityComment) {
    const content = editCommentContent.trim();
    if (!content) {
      setCommentErrors(current => ({ ...current, [post.id]: "의견을 입력해 주세요." }));
      return;
    }
    setBusyCommentId(comment.id);
    try {
      const updated = await api<CommunityComment>(
        `/community/${post.id}/comments/${comment.id}`,
        {
          method: "PATCH",
          ...jsonBody({ content, is_anonymous: editCommentAnonymous }),
        }
      );
      setPosts(current =>
        current.map(item =>
          item.id === post.id
            ? {
                ...item,
                comments: item.comments.map(value =>
                  value.id === updated.id ? updated : value
                ),
              }
            : item
        )
      );
      setEditingCommentId(null);
      toast.success("의견을 수정했습니다.");
    } catch (caught) {
      setCommentErrors(current => ({
        ...current,
        [post.id]: caught instanceof Error ? caught.message : "의견을 수정하지 못했습니다.",
      }));
    } finally {
      setBusyCommentId(null);
    }
  }

  async function deleteComment(post: CommunityPost, comment: CommunityComment) {
    if (!window.confirm("이 의견을 삭제할까요?")) return;
    setBusyCommentId(comment.id);
    try {
      await api(`/community/${post.id}/comments/${comment.id}`, { method: "DELETE" });
      setPosts(current =>
        current.map(item =>
          item.id === post.id
            ? {
                ...item,
                comment_count: Math.max(0, item.comment_count - 1),
                comments: item.comments.filter(value => value.id !== comment.id),
              }
            : item
        )
      );
      if (editingCommentId === comment.id) setEditingCommentId(null);
      toast.success("의견을 삭제했습니다.");
    } catch (caught) {
      setCommentErrors(current => ({
        ...current,
        [post.id]: caught instanceof Error ? caught.message : "의견을 삭제하지 못했습니다.",
      }));
    } finally {
      setBusyCommentId(null);
    }
  }

  function fillPlanForm(plan: CommunityEventPlan | null) {
    const planDates = plan?.operation_dates?.length ? plan.operation_dates : [""];
    setPlanForm(
      plan
        ? {
            ...(Object.fromEntries(
              planFields.map(field => [field.key, plan[field.key] ?? ""])
            ) as Pick<EventPlanForm, "purpose" | "target_participants" | "schedule_plan" | "location_plan" | "program_plan" | "role_plan" | "budget_plan" | "safety_plan">),
            operation_days: plan.operation_days ?? 1,
            operation_dates: planDates,
            teams_per_day: plan.teams_per_day ?? 2,
            people_per_team: plan.people_per_team ?? 3,
            team_role_description: plan.team_role_description ?? "",
            team_requirements: plan.team_requirements?.length
              ? plan.team_requirements.map(team => ({
                  ...team,
                  operation_dates: team.operation_dates ?? planDates.filter(Boolean),
                }))
              : emptyPlanForm.team_requirements,
            team_manager_id: plan.team_manager_id ?? "",
            poster_manager_id: plan.poster_manager_id ?? "",
            poster_required: plan.poster_required,
          }
        : emptyPlanForm
    );
  }

  async function refreshPlanWorkspace(postId: string) {
    const workspace = await api<PlanWorkspace>(`/community/${postId}/plan`);
    setPlanWorkspace(workspace);
    fillPlanForm(workspace.plan);
    setPlanTarget(current =>
      current?.id === postId
        ? { ...current, plan: workspace.plan, can_write_plan: workspace.plan.can_edit }
        : current
    );
    setPosts(current =>
      current.map(post =>
        post.id === postId
          ? { ...post, plan: workspace.plan, can_write_plan: workspace.plan.can_edit }
          : post
      )
    );
    return workspace;
  }

  async function openPlan(post: CommunityPost) {
    setPlanTarget(post);
    setPlanWorkspace(null);
    fillPlanForm(post.plan);
    setReviewNote(post.plan?.review_note ?? "");
    setSuggestionForm({ section: "purpose", proposedContent: "", reason: "" });
    setPlanError("");
    if (post.plan) {
      try {
        const workspace = await refreshPlanWorkspace(post.id);
        setReviewNote(workspace.plan.review_note ?? "");
      } catch (caught) {
        setPlanError(caught instanceof Error ? caught.message : "공동 작성 내역을 불러오지 못했습니다.");
      }
    }
  }

  async function savePlan() {
    if (!planTarget) return;
    const operationDates = planForm.operation_dates.filter(Boolean);
    if (new Set(operationDates).size !== operationDates.length) {
      setPlanError("활동 날짜는 서로 다르게 선택해 주세요.");
      return;
    }

    setPlanSaving(true);
    setPlanError("");
    try {
      const teamsPerDay = Math.max(
        ...operationDates.map(
          operationDate =>
            planForm.team_requirements.filter(team =>
              team.operation_dates?.includes(operationDate)
            ).length
        ),
        0
      );
      const saved = await api<CommunityEventPlan>(`/community/${planTarget.id}/plan`, {
        method: "PUT",
        ...jsonBody({
          ...planForm,
          operation_dates: operationDates.length ? operationDates : null,
          operation_days: operationDates.length || null,
          teams_per_day: teamsPerDay || null,
          people_per_team: Math.max(...planForm.team_requirements.map(team => team.people_count)),
          team_role_description: planForm.team_requirements.map(team => `${team.name}: ${team.role_description}`).join(" / "),
          team_manager_id: planForm.team_manager_id || null,
          poster_manager_id: planForm.poster_required ? planForm.poster_manager_id || null : null,
          base_version: activePlan?.version ?? null,
        }),
      });
      setPosts(current =>
        current.map(post => (post.id === planTarget.id ? { ...post, plan: saved } : post))
      );
      setPlanTarget(current => current ? { ...current, plan: saved, can_write_plan: saved.can_edit } : current);
      await refreshPlanWorkspace(planTarget.id);
      toast.success(isPlanCoordinator ? "행사 계획서 초안을 저장했습니다." : "계획서 내용을 저장했습니다.");
    } catch (caught) {
      setPlanError(caught instanceof Error ? caught.message : "기획서를 저장하지 못했습니다.");
    } finally {
      setPlanSaving(false);
    }
  }

  function updatePlanOperationDate(index: number, nextDate: string) {
    setPlanForm(current => {
      const previousDate = current.operation_dates[index];
      return {
        ...current,
        operation_dates: current.operation_dates.map((item, itemIndex) =>
          itemIndex === index ? nextDate : item
        ),
        team_requirements: current.team_requirements.map(team => ({
          ...team,
          operation_dates: (team.operation_dates ?? [])
            .map(date => (date === previousDate ? nextDate : date))
            .filter(Boolean),
        })),
      };
    });
  }

  function removePlanOperationDate(index: number) {
    setPlanForm(current => {
      const removedDate = current.operation_dates[index];
      return {
        ...current,
        operation_dates: current.operation_dates.filter(
          (_, itemIndex) => itemIndex !== index
        ),
        team_requirements: current.team_requirements.map(team => ({
          ...team,
          operation_dates: (team.operation_dates ?? []).filter(
            date => date !== removedDate
          ),
        })),
      };
    });
  }

  function togglePlanTeamDate(teamIndex: number, operationDate: string) {
    if (!operationDate) return;
    setPlanForm(current => ({
      ...current,
      team_requirements: current.team_requirements.map((team, itemIndex) => {
        if (itemIndex !== teamIndex) return team;
        const dates = team.operation_dates ?? [];
        return {
          ...team,
          operation_dates: dates.includes(operationDate)
            ? dates.filter(date => date !== operationDate)
            : [...dates, operationDate],
        };
      }),
    }));
  }

  async function submitPlan() {
    if (!planTarget || !activePlan) return;
    setPlanSaving(true);
    setPlanError("");
    try {
      await api(`/community/${planTarget.id}/plan/submit`, {
        method: "POST",
        ...jsonBody({ base_version: activePlan.version }),
      });
      await refreshPlanWorkspace(planTarget.id);
      toast.success("최종 제출했습니다. 담당 선생님이 검토할 수 있습니다.");
    } catch (caught) {
      setPlanError(caught instanceof Error ? caught.message : "최종 제출하지 못했습니다.");
    } finally {
      setPlanSaving(false);
    }
  }

  async function reviewPlan(action: "APPROVE" | "REQUEST_CHANGES" | "REJECT") {
    if (!planTarget || !activePlan) return;
    if (action !== "APPROVE" && !reviewNote.trim()) {
      setPlanError("수정이 필요한 내용을 적어 주세요.");
      return;
    }
    setPlanSaving(true);
    setPlanError("");
    try {
      await api(`/community/${planTarget.id}/plan/review`, {
        method: "POST",
        ...jsonBody({ action, note: reviewNote.trim() || null }),
      });
      await refreshPlanWorkspace(planTarget.id);
      if (action === "APPROVE") await load(false);
      toast.success(
        action === "APPROVE"
          ? "기획서를 승인하고 행사와 조 편성 업무를 만들었습니다."
          : action === "REJECT" ? "기획서를 반려했습니다." : "수정 요청을 보냈습니다."
      );
    } catch (caught) {
      setPlanError(caught instanceof Error ? caught.message : "기획서를 검토하지 못했습니다.");
    } finally {
      setPlanSaving(false);
    }
  }

  async function createPlanSuggestion() {
    if (!planTarget || !suggestionForm.proposedContent.trim()) {
      setPlanError("제안할 내용을 입력해 주세요.");
      return;
    }
    setPlanSaving(true);
    setPlanError("");
    try {
      await api(`/community/${planTarget.id}/plan/suggestions`, {
        method: "POST",
        ...jsonBody({
          section: suggestionForm.section,
          proposed_content: suggestionForm.proposedContent,
          reason: suggestionForm.reason || null,
        }),
      });
      await refreshPlanWorkspace(planTarget.id);
      setSuggestionForm({ section: "purpose", proposedContent: "", reason: "" });
      toast.success("수정 제안을 남겼습니다.");
    } catch (caught) {
      setPlanError(caught instanceof Error ? caught.message : "수정 제안을 남기지 못했습니다.");
    } finally {
      setPlanSaving(false);
    }
  }

  async function resolvePlanSuggestion(suggestionId: string, action: "ADOPT" | "REJECT") {
    if (!planTarget || !activePlan) return;
    setPlanSaving(true);
    setPlanError("");
    try {
      const workspace = await api<PlanWorkspace>(
        `/community/${planTarget.id}/plan/suggestions/${suggestionId}`,
        {
          method: "PUT",
          ...jsonBody({ action, base_version: activePlan.version }),
        }
      );
      setPlanWorkspace(workspace);
      fillPlanForm(workspace.plan);
      setPlanTarget(current => current ? { ...current, plan: workspace.plan, can_write_plan: workspace.plan.can_edit } : current);
      setPosts(current => current.map(post => post.id === planTarget.id ? { ...post, plan: workspace.plan, can_write_plan: workspace.plan.can_edit } : post));
      toast.success(action === "ADOPT" ? "수정 제안을 반영했습니다." : "수정 제안을 반영하지 않기로 했습니다.");
    } catch (caught) {
      setPlanError(caught instanceof Error ? caught.message : "수정 제안을 처리하지 못했습니다.");
    } finally {
      setPlanSaving(false);
    }
  }

  function openConversion(post: CommunityPost) {
    setConversionTarget(post);
    setEventForm({ eventDate: "", location: "", startsAt: "", endsAt: "" });
    setFormError("");
  }

  async function convertToEvent() {
    if (!conversionTarget || !eventForm.eventDate) {
      setFormError("행사 날짜를 선택해 주세요.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const updated = await api<CommunityPost>(
        `/community/${conversionTarget.id}/convert-to-event`,
        {
          method: "POST",
          ...jsonBody({
            event_date: eventForm.eventDate,
            location: eventForm.location || null,
            starts_at: eventForm.startsAt || null,
            ends_at: eventForm.endsAt || null,
          }),
        }
      );
      setPosts(current =>
        orderPosts(current.map(item => (item.id === updated.id ? updated : item)), sort)
      );
      setConversionTarget(null);
      toast.success("아이디어가 실제 행사로 이어졌습니다.");
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : "행사로 전환하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-[980px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[-.03em]">게시판</h1>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            추천 10개를 받으면 부장회의 안건으로 올라갑니다.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus size={17} />행사 아이디어 던지기
        </Button>
      </header>

      <div className="mt-6 flex items-center gap-2 border-b border-slate-200 pb-3">
        <button
          onClick={() => setSort("popular")}
          className={`h-9 rounded-md px-3 text-sm font-semibold ${
            sort === "popular"
              ? "bg-[#2563a8] text-white"
              : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          추천순
        </button>
        <button
          onClick={() => setSort("recent")}
          className={`h-9 rounded-md px-3 text-sm font-semibold ${
            sort === "recent"
              ? "bg-[#2563a8] text-white"
              : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          최신순
        </button>
        <span className="ml-1 hidden text-xs text-slate-500 sm:inline">
          아이디어 {posts.length}개 · 추천 {totalRecommendations}개
        </span>
        <button
          aria-label="새로고침"
          title="새로고침"
          onClick={() => void load(false)}
          className="ml-auto grid h-9 w-9 place-items-center rounded-md border border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="mt-3">
        {loading ? (
          <LoadingState label="행사 아이디어를 불러오는 중이에요." />
        ) : error ? (
          <ErrorState description={error} onRetry={() => void load()} />
        ) : posts.length === 0 ? (
          <EmptyState
            title="아직 행사 아이디어가 없어요"
            description="행사 목적과 대략적인 진행 모습을 적어 첫 제안을 올려 보세요."
            action={
              <Button onClick={() => setCreateOpen(true)}>
                <Plus size={16} />첫 아이디어 던지기
              </Button>
            }
          />
        ) : (
          <section className="border-y border-slate-200">
            {posts.map(post => (
              <article
                key={post.id}
                className={`min-w-0 border-b border-slate-200 px-1 py-5 last:border-b-0 ${post.agenda_at ? "bg-[#f8fbfe]" : ""}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {post.agenda_at && (
                        <span className="inline-flex items-center gap-1 rounded bg-[#e8f0f8] px-2 py-1 text-xs font-bold text-[#1f528b]">
                          <FileText size={13} />부장회의 안건 · 상단 고정
                        </span>
                      )}
                      {post.converted_event_id && (
                        <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700">
                          <CheckCircle2 size={13} />행사로 이어짐
                        </span>
                      )}
                    </div>
                    <h2 className="mt-3 break-words text-base font-bold leading-6 text-slate-900">
                      {post.title}
                    </h2>
                  </div>
                  <button
                    type="button"
                    aria-label={post.recommended_by_me ? "추천 취소" : "추천"}
                    aria-pressed={post.recommended_by_me}
                    disabled={busyPostId === post.id}
                    onClick={() => void toggleRecommendation(post)}
                    className={`flex h-10 min-w-12 shrink-0 items-center justify-center gap-1 border-l border-slate-200 pl-3 transition disabled:opacity-50 ${
                      post.recommended_by_me
                        ? "text-amber-700"
                        : "text-slate-500 hover:text-amber-700"
                    }`}
                  >
                    <Star size={19} fill={post.recommended_by_me ? "currentColor" : "none"} />
                    <span className="text-xs font-bold">{post.recommendation_count}</span>
                  </button>
                </div>

                <p className="mt-3 line-clamp-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                  {post.content || "아직 자세한 설명은 없어요. 관심을 눌러 아이디어에 힘을 보태 주세요."}
                </p>

                {(post.is_mine || currentRole === "TEACHER") && (
                  <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-dashed border-slate-200 pt-3">
                    <button
                      type="button"
                      onClick={() => openPostEdit(post)}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                    >
                      <Pencil size={14} />게시물 수정
                    </button>
                    <button
                      type="button"
                      disabled={busyPostId === post.id}
                      onClick={() => void deletePost(post)}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-rose-200 px-3 text-xs font-semibold text-[#a12622] hover:bg-rose-50"
                    >
                      <Trash2 size={14} />게시물 삭제
                    </button>
                    {currentRole === "TEACHER" && (
                      <span className="flex flex-wrap items-center gap-1 border-l border-slate-200 pl-2">
                        <span className="px-1 text-[11px] font-semibold text-slate-500">테스트 추천</span>
                        {[1, 10].map(amount => (
                          <button
                            key={amount}
                            type="button"
                            disabled={busyPostId === post.id}
                            onClick={() => void setTestRecommendationCount(post, post.recommendation_count + amount)}
                            className="min-h-8 rounded border border-amber-200 bg-amber-50 px-2 text-xs font-bold text-amber-800"
                          >
                            +{amount}
                          </button>
                        ))}
                        <button
                          type="button"
                          disabled={busyPostId === post.id || post.test_recommendation_bonus === 0}
                          onClick={() => void setTestRecommendationCount(post, post.recommendation_count - post.test_recommendation_bonus)}
                          className="min-h-8 rounded border border-slate-200 px-2 text-xs font-semibold text-slate-500 disabled:opacity-40"
                        >
                          초기화
                        </button>
                      </span>
                    )}
                    {post.converted_event_id && currentRole === "TEACHER" && (
                      <Link
                        href={`/events/${post.converted_event_id}`}
                        className="ml-auto inline-flex min-h-9 items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-[#1f528b] hover:bg-[#f4f8fc]"
                      >
                        <CalendarPlus size={14} />행사 관리
                      </Link>
                    )}
                  </div>
                )}

                {post.agenda_at && (
                  <section className="mt-4 border-l-2 border-[#2563a8] bg-[#f4f8fc] px-3 py-3">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <strong className="text-sm text-slate-800">부장회의 기획서 작성</strong>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {post.plan_writer_name
                            ? `${post.plan_writer_name}님이 회의 내용을 지정 양식에 정리합니다.`
                            : "부장회의에서 기획서 작성자를 지정해 주세요."}
                        </p>
                      </div>
                      {post.can_assign_plan_writer && (
                        <select
                          aria-label={`${post.title} 기획서 작성자`}
                          value={writerDrafts[post.id] ?? post.plan_writer_id ?? ""}
                          disabled={busyPostId === post.id}
                          onChange={event => void assignPlanWriter(post, event.target.value)}
                          className="h-9 min-w-48 rounded-md border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-700"
                        >
                          <option value="">작성자 선택</option>
                          {meetingWriters.map(user => (
                            <option key={user.id} value={user.id}>{user.name} · {[user.grade, user.department].filter(Boolean).join(" · ")}</option>
                          ))}
                        </select>
                      )}
                    </div>
                    <div className="mt-3 border-t border-[#d7e5f0] pt-3">
                      <strong className="text-sm text-slate-800">부장회의 일정</strong>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {post.meeting_date && post.meeting_time_slot
                          ? `${post.meeting_date.replaceAll("-", ". ")} · ${meetingTimeSlotLabels[post.meeting_time_slot]}${post.meeting_time ? ` ${post.meeting_time.slice(0, 5)}` : ""}`
                          : "아직 회의 일정이 정해지지 않았습니다."}
                      </p>
                      {post.can_schedule_meeting && (
                        <div className="mt-2 grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.8fr)_auto] sm:items-end">
                          <label className="grid gap-1 text-xs font-semibold text-slate-600">
                            회의 날짜
                            <input
                              type="date"
                              aria-label={`${post.title} 부장회의 날짜`}
                              value={meetingDraftFor(post).meetingDate}
                              onChange={event => updateMeetingDraft(post, { meetingDate: event.target.value })}
                              className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700"
                            />
                          </label>
                          <label className="grid gap-1 text-xs font-semibold text-slate-600">
                            시간대
                            <select
                              aria-label={`${post.title} 부장회의 시간대`}
                              value={meetingDraftFor(post).meetingTimeSlot}
                              onChange={event => updateMeetingDraft(post, { meetingTimeSlot: event.target.value as MeetingTimeSlot })}
                              className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700"
                            >
                              <option value="MORNING">아침시간</option>
                              <option value="LUNCH">점심시간</option>
                              <option value="AFTER_SCHOOL">방과후</option>
                            </select>
                          </label>
                          <label className="grid gap-1 text-xs font-semibold text-slate-600">
                            정확한 시각 (선택)
                            <input
                              type="time"
                              aria-label={`${post.title} 부장회의 정확한 시각`}
                              value={meetingDraftFor(post).meetingTime}
                              onChange={event => updateMeetingDraft(post, { meetingTime: event.target.value })}
                              className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700"
                            />
                          </label>
                          <button
                            type="button"
                            disabled={busyPostId === post.id}
                            onClick={() => void saveMeetingSchedule(post)}
                            className="h-9 rounded-md bg-[#2563a8] px-4 text-xs font-bold text-white disabled:opacity-50"
                          >
                            일정 저장
                          </button>
                        </div>
                      )}
                    </div>
                  </section>
                )}

                {post.plan ? (
                  <button
                    type="button"
                    onClick={() => void openPlan(post)}
                    className="mt-4 flex w-full items-center gap-3 border-l-2 border-[#2563a8] bg-[#f4f8fc] px-3 py-3 text-left hover:bg-[#eaf2f8]"
                  >
                    <FileText size={18} className="shrink-0 text-[#2563a8]" />
                    <span className="min-w-0 flex-1">
                      <strong className="block text-sm text-slate-800">상세 행사기획서</strong>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        {planStatusLabels[post.plan.status]} · {post.plan.can_edit ? "함께 수정할 수 있어요." : "내용을 확인해 보세요."}
                      </span>
                    </span>
                    <span className="shrink-0 text-xs font-semibold text-[#2563a8]">
                      {post.plan.author_id === currentUser.id
                        ? "계획서 작성"
                        : post.plan.can_edit
                          ? "내용 보완"
                          : "보기"}
                    </span>
                  </button>
                ) : post.can_write_plan ? (
                  <button
                    type="button"
                    onClick={() => void openPlan(post)}
                    className="mt-4 flex w-full items-center gap-3 border-l-2 border-emerald-500 bg-emerald-50 px-3 py-3 text-left hover:bg-emerald-100/70"
                  >
                    <FileText size={18} className="shrink-0 text-emerald-700" />
                    <span className="min-w-0 flex-1">
                      <strong className="block text-sm text-emerald-900">행사 계획서 작성하기</strong>
                      <span className="mt-0.5 block text-xs text-emerald-700">
                        작성자로 지정되었습니다. 기존 행사 계획서 양식에 회의 내용을 정리해 주세요.
                      </span>
                    </span>
                    <span className="shrink-0 text-xs font-bold text-emerald-800">작성</span>
                  </button>
                ) : post.is_mine ? (
                  <p className="mt-4 border-l-2 border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                    상세 기획서 작성까지 추천 {Math.max(0, 10 - post.recommendation_count)}개 남았어요.
                  </p>
                ) : post.recommendation_count >= 10 ? (
                  <p className="mt-4 border-l-2 border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                    추천 10개를 달성해 학생 임원이 공동 기획서를 시작할 수 있어요.
                  </p>
                ) : null}

                <div className="pt-5">
                  <div className="flex flex-col gap-3 border-t border-slate-100 pt-3 sm:flex-row sm:items-center sm:justify-between">
                    <span className="flex min-w-0 items-center gap-1.5 text-xs text-slate-500">
                      <UserRound size={14} />
                      <span className="truncate">
                        {post.author_name}{post.is_mine ? " · 내가 올림" : ""} · {formatTime(post.created_at)}
                      </span>
                    </span>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => toggleComments(post.id)}
                        aria-expanded={expandedPostIds.has(post.id)}
                        className="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        <MessageCircle size={15} />의견 {post.comment_count}
                      </button>
                      {canConvert && post.plan?.can_convert && !post.converted_event_id && (
                        <Button
                          size="sm"
                          variant="secondary"
                          className="shrink-0"
                          onClick={() => openConversion(post)}
                        >
                          <CalendarPlus size={15} />행사로 만들기
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                {expandedPostIds.has(post.id) && (
                  <section className="mt-4 border-t border-slate-200 pt-4" aria-label={`${post.title} 의견`}>
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-bold text-slate-800">아이디어 구체화 의견</h3>
                      <span className="text-xs text-slate-500">익명 또는 이름 공개를 선택해요</span>
                    </div>
                    {post.comments.length ? (
                      <div className="mt-3 divide-y divide-slate-100">
                        {post.comments.map(comment => (
                          <div key={comment.id} className="py-3 first:pt-0">
                            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                              <strong className="text-xs text-slate-700">{comment.author_name}</strong>
                              {comment.is_mine && (
                                <span className="text-xs font-semibold text-[#2563a8]">내 의견</span>
                              )}
                              <span className="text-xs text-slate-400">{formatTime(comment.created_at)}</span>
                              {comment.is_mine && (
                                <span className="ml-auto flex items-center gap-1">
                                  <button
                                    type="button"
                                    onClick={() => startCommentEdit(comment)}
                                    className="inline-flex min-h-8 items-center gap-1 rounded px-2 text-xs font-semibold text-slate-500 hover:bg-slate-100"
                                  >
                                    <Pencil size={13} />수정
                                  </button>
                                  <button
                                    type="button"
                                    disabled={busyCommentId === comment.id}
                                    onClick={() => void deleteComment(post, comment)}
                                    className="inline-flex min-h-8 items-center gap-1 rounded px-2 text-xs font-semibold text-[#a12622] hover:bg-rose-50"
                                  >
                                    <Trash2 size={13} />삭제
                                  </button>
                                </span>
                              )}
                            </div>
                            {editingCommentId === comment.id ? (
                              <div className="mt-2 rounded-md bg-slate-50 p-3">
                                <div className="flex gap-2">
                                  {([true, false] as const).map(isAnonymous => (
                                    <button
                                      key={String(isAnonymous)}
                                      type="button"
                                      onClick={() => setEditCommentAnonymous(isAnonymous)}
                                      className={`min-h-8 rounded border px-2.5 text-xs font-semibold ${
                                        editCommentAnonymous === isAnonymous
                                          ? "border-[#2563a8] bg-white text-[#1f528b]"
                                          : "border-slate-200 text-slate-500"
                                      }`}
                                    >
                                      {isAnonymous ? "익명" : "이름 공개"}
                                    </button>
                                  ))}
                                </div>
                                <textarea
                                  rows={3}
                                  maxLength={1000}
                                  value={editCommentContent}
                                  onChange={event => setEditCommentContent(event.target.value)}
                                  className="mt-2 min-h-20 w-full resize-y rounded-md border border-slate-200 bg-white px-3 py-2 text-sm leading-6 outline-none focus-visible:border-[#2563a8] focus-visible:ring-2 focus-visible:ring-[#2563a8]/20"
                                />
                                <div className="mt-2 flex justify-end gap-2">
                                  <Button size="sm" variant="secondary" onClick={() => setEditingCommentId(null)}>
                                    취소
                                  </Button>
                                  <Button
                                    size="sm"
                                    disabled={busyCommentId === comment.id}
                                    onClick={() => void saveCommentEdit(post, comment)}
                                  >
                                    수정 저장
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <p className="mt-1.5 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">
                                {comment.content}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-slate-500">
                        아직 의견이 없어요. 첫 번째로 아이디어를 구체화해 보세요.
                      </p>
                    )}
                    <form
                      className="mt-4 border-t border-slate-100 pt-4"
                      onSubmit={event => {
                        event.preventDefault();
                        void submitComment(post);
                      }}
                    >
                      <label htmlFor={`comment-${post.id}`} className="text-sm font-semibold text-slate-800">
                        의견 더하기
                      </label>
                      <div className="mt-2 flex items-center gap-2" role="group" aria-label="의견 이름 표시">
                        <button
                          type="button"
                          onClick={() => setCommentAnonymous(current => ({ ...current, [post.id]: true }))}
                          className={`min-h-9 rounded-md border px-3 text-xs font-semibold ${
                            (commentAnonymous[post.id] ?? true)
                              ? "border-[#2563a8] bg-[#f4f8fc] text-[#1f528b]"
                              : "border-slate-200 text-slate-600 hover:bg-slate-50"
                          }`}
                          aria-pressed={commentAnonymous[post.id] ?? true}
                        >
                          익명
                        </button>
                        <button
                          type="button"
                          onClick={() => setCommentAnonymous(current => ({ ...current, [post.id]: false }))}
                          className={`min-h-9 rounded-md border px-3 text-xs font-semibold ${
                            !(commentAnonymous[post.id] ?? true)
                              ? "border-[#2563a8] bg-[#f4f8fc] text-[#1f528b]"
                              : "border-slate-200 text-slate-600 hover:bg-slate-50"
                          }`}
                          aria-pressed={!(commentAnonymous[post.id] ?? true)}
                        >
                          이름 공개
                        </button>
                      </div>
                      <textarea
                        id={`comment-${post.id}`}
                        rows={2}
                        maxLength={1000}
                        value={commentDrafts[post.id] ?? ""}
                        onChange={event => {
                          setCommentDrafts(current => ({ ...current, [post.id]: event.target.value }));
                          setCommentErrors(current => ({ ...current, [post.id]: "" }));
                        }}
                        placeholder="예산, 장소, 진행 방법처럼 아이디어를 발전시킬 의견을 적어 주세요."
                        className="mt-2 min-h-20 w-full resize-y rounded-md border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400 focus-visible:border-[#2563a8] focus-visible:ring-2 focus-visible:ring-[#2563a8]/20"
                      />
                      <div className="mt-2 flex items-center justify-between gap-3">
                        <p className="text-xs text-[#a12622]">{commentErrors[post.id]}</p>
                        <Button
                          type="submit"
                          size="sm"
                          disabled={busyCommentPostId === post.id}
                          className="shrink-0"
                        >
                          <Send size={14} />
                          {busyCommentPostId === post.id ? "남기는 중…" : "의견 남기기"}
                        </Button>
                      </div>
                    </form>
                  </section>
                )}
              </article>
            ))}
          </section>
        )}
      </div>

      <AppModal
        open={Boolean(editPostTarget)}
        title="행사 게시물 수정"
        description="제목과 행사 전체 개요를 수정합니다. 담당 선생님은 모든 게시물을 관리할 수 있어요."
        onClose={() => {
          setEditPostTarget(null);
          setFormError("");
        }}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditPostTarget(null)}>취소</Button>
            <Button disabled={saving} onClick={() => void savePostEdit()}>
              {saving ? "저장하는 중…" : "수정 내용 저장"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4">
          <TextInput
            label="행사 이름"
            required
            maxLength={160}
            value={editPostForm.title}
            onChange={event => setEditPostForm(current => ({ ...current, title: event.target.value }))}
          />
          <TextArea
            label="행사 전체 개요"
            required
            rows={5}
            maxLength={5000}
            value={editPostForm.content}
            onChange={event => setEditPostForm(current => ({ ...current, content: event.target.value }))}
          />
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={editPostForm.isAnonymous}
              onChange={event => setEditPostForm(current => ({ ...current, isAnonymous: event.target.checked }))}
            />
            작성자를 익명으로 표시
          </label>
          {formError && <p className="text-sm text-[#a12622]">{formError}</p>}
        </div>
      </AppModal>

      <AppModal
        open={Boolean(planTarget)}
        size="xl"
        title={isPlanCoordinator ? "행사 계획서 작성" : "행사 계획서 확인"}
        description={
          isPlanCoordinator
            ? "부장회의에서 정한 내용을 기존 행사 계획서 양식에 작성하고 선생님께 제출합니다."
            : canEditPlan
              ? "작성자를 도와 내용을 보완할 수 있으며 저장한 사람과 버전이 기록됩니다."
            : "공동으로 작성한 행사기획서와 검토 상태를 확인합니다."
        }
        onClose={() => {
          setPlanTarget(null);
          setPlanWorkspace(null);
          setPlanError("");
        }}
        footer={
          activePlan?.can_review ? (
            <>
              <Button variant="secondary" onClick={() => void reviewPlan("REJECT")} disabled={planSaving}>
                반려
              </Button>
              <Button variant="secondary" onClick={() => void reviewPlan("REQUEST_CHANGES")} disabled={planSaving}>
                수정 요청
              </Button>
              <Button onClick={() => void reviewPlan("APPROVE")} disabled={planSaving}>
                <ShieldCheck size={16} /> 승인
              </Button>
            </>
          ) : canEditPlan ? (
            <>
              <Button variant="secondary" onClick={() => setPlanTarget(null)}>취소</Button>
              <Button disabled={planSaving} onClick={() => void savePlan()}>
                {planSaving ? "저장하는 중…" : "초안 저장"}
              </Button>
              {isPlanCoordinator && activePlan && (
                <Button
                  disabled={planSaving || !activePlan.can_submit}
                  onClick={() => void submitPlan()}
                  title={activePlan.can_submit ? undefined : "모든 항목과 담당자를 저장하면 최종 제출할 수 있어요."}
                >
                  <Send size={15} /> 최종 제출
                </Button>
              )}
            </>
          ) : (
            <Button onClick={() => setPlanTarget(null)}>닫기</Button>
          )
        }
      >
        <div className="grid gap-5">
          {activePlan && (
            <section className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm text-slate-800">{planStatusLabels[activePlan.status]}</strong>
                <span className="text-xs text-slate-500">버전 {activePlan.version}</span>
              </div>
              {activePlan.review_note && (
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#a12622]">
                  선생님 의견: {activePlan.review_note}
                </p>
              )}
              {planWorkspace?.contributors.length ? (
                <p className="mt-2 text-xs text-slate-500">
                  함께 작성: {planWorkspace.contributors.map(item => item.name).join(", ")}
                </p>
              ) : null}
            </section>
          )}

          {canEditPlan ? (
          <div className="grid gap-5 md:grid-cols-2">
            <SelectField
              label="조 편성 담당자"
              required
              value={planForm.team_manager_id}
              onChange={event => setPlanForm(current => ({ ...current, team_manager_id: event.target.value }))}
            >
              <option value="">담당자를 선택해 주세요</option>
              {studentCouncilUsers.map(user => <option key={user.id} value={user.id}>{user.name} · {[user.grade, user.department].filter(Boolean).join(" · ")}</option>)}
            </SelectField>
            <div className="grid gap-2">
              <label className="flex min-h-11 items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={planForm.poster_required}
                  onChange={event => setPlanForm(current => ({ ...current, poster_required: event.target.checked }))}
                />
                포스터 제작이 필요한 행사
              </label>
              {planForm.poster_required && (
                <SelectField
                  label="포스터 담당자"
                  required
                  value={planForm.poster_manager_id}
                  onChange={event => setPlanForm(current => ({ ...current, poster_manager_id: event.target.value }))}
                >
                  <option value="">담당자를 선택해 주세요</option>
                  {studentCouncilUsers.map(user => <option key={user.id} value={user.id}>{user.name} · {[user.grade, user.department].filter(Boolean).join(" · ")}</option>)}
                </SelectField>
              )}
            </div>
            <div className="md:col-span-2 grid gap-4 rounded-md border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="mb-2 text-sm font-bold text-slate-800">활동 날짜</p>
                  <div className="grid gap-2">
                    {planForm.operation_dates.map((date, dateIndex) => (
                      <div key={dateIndex} className="flex gap-2">
                        <input type="date" required value={date} onChange={event => updatePlanOperationDate(dateIndex, event.target.value)} className="h-11 rounded-md border border-slate-300 bg-white px-3 text-sm" />
                        <button type="button" disabled={planForm.operation_dates.length === 1} onClick={() => removePlanOperationDate(dateIndex)} className="inline-flex h-11 w-11 items-center justify-center rounded border border-slate-300 text-slate-500 disabled:opacity-40" aria-label="날짜 삭제"><Trash2 size={16} /></button>
                      </div>
                    ))}
                    <button type="button" onClick={() => setPlanForm(current => ({ ...current, operation_dates: [...current.operation_dates, ""] }))} className="text-left text-sm font-semibold text-[#2563a8]">+ 날짜 추가</button>
                  </div>
                </div>
                <Button type="button" variant="secondary" onClick={() => setPlanForm(current => ({ ...current, team_requirements: [...current.team_requirements, { name: `${current.team_requirements.length + 1}조`, people_count: 1, role_description: "", operation_dates: current.operation_dates.filter(Boolean) }] }))}>
                  <Plus size={16} /> 조 추가
                </Button>
              </div>
              <p className="text-sm font-bold text-slate-800">하루에 필요한 조</p>
              {planForm.team_requirements.map((team, index) => (
                <div key={index} className="grid gap-3 border-t border-slate-200 pt-4 sm:grid-cols-[1fr_140px_auto]">
                  <TextInput label="조 이름" required value={team.name} onChange={event => setPlanForm(current => ({ ...current, team_requirements: current.team_requirements.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item) }))} />
                  <TextInput label="필요 인원" type="number" min={1} max={20} required value={team.people_count} onChange={event => setPlanForm(current => ({ ...current, team_requirements: current.team_requirements.map((item, itemIndex) => itemIndex === index ? { ...item, people_count: Number(event.target.value) } : item) }))} />
                  <button type="button" disabled={planForm.team_requirements.length === 1} onClick={() => setPlanForm(current => ({ ...current, team_requirements: current.team_requirements.filter((_, itemIndex) => itemIndex !== index) }))} className="mt-7 inline-flex h-11 w-11 items-center justify-center rounded border border-slate-300 text-slate-500 disabled:opacity-40" aria-label={`${team.name} 삭제`}><Trash2 size={17} /></button>
                  <TextArea className="sm:col-span-3" label={`${team.name || `${index + 1}조`} 역할`} required rows={2} maxLength={500} value={team.role_description} onChange={event => setPlanForm(current => ({ ...current, team_requirements: current.team_requirements.map((item, itemIndex) => itemIndex === index ? { ...item, role_description: event.target.value } : item) }))} placeholder="예: 정문에서 참가자 확인과 이동 안내" />
                  <fieldset className="sm:col-span-3">
                    <legend className="text-sm font-semibold text-slate-700">운영 날짜</legend>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
                      {planForm.operation_dates.filter(Boolean).map(operationDate => (
                        <label key={operationDate} className="inline-flex items-center gap-2 text-sm text-slate-700">
                          <input type="checkbox" checked={team.operation_dates?.includes(operationDate) ?? false} onChange={() => togglePlanTeamDate(index, operationDate)} />
                          {operationDate}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                </div>
              ))}
              <p className="text-sm text-slate-600">{planForm.operation_dates.filter(Boolean).length}일 · 총 {planForm.operation_dates.filter(Boolean).reduce((sum, operationDate) => sum + planForm.team_requirements.filter(team => team.operation_dates?.includes(operationDate)).length, 0)}개 조를 편성합니다.</p>
            </div>
            {planFields.map((field, index) => (
              <TextArea
                key={field.key}
                className={index >= 4 ? "md:col-span-2" : undefined}
                label={field.label}
                required
                rows={index >= 4 ? 4 : 3}
                maxLength={field.maxLength}
                value={planForm[field.key]}
                onChange={event => {
                  setPlanForm(current => ({ ...current, [field.key]: event.target.value }));
                  setPlanError("");
                }}
                placeholder={field.placeholder}
              />
            ))}
          </div>
        ) : activePlan ? (
          <div className="grid gap-5 md:grid-cols-2">
            <section className="border-t border-slate-200 pt-3">
              <h3 className="text-sm font-bold text-slate-800">조 편성 담당자</h3>
              <p className="mt-2 text-sm text-slate-600">
                {users.find(user => user.id === activePlan.team_manager_id)?.name ?? "아직 정하지 않음"}
              </p>
            </section>
            <section className="border-t border-slate-200 pt-3">
              <h3 className="text-sm font-bold text-slate-800">포스터 담당자</h3>
              <p className="mt-2 text-sm text-slate-600">
                {activePlan.poster_required
                  ? users.find(user => user.id === activePlan.poster_manager_id)?.name ?? "아직 정하지 않음"
                  : "포스터가 필요하지 않은 행사"}
              </p>
            </section>
            <section className="md:col-span-2 border-t border-slate-200 pt-3">
              <h3 className="text-sm font-bold text-slate-800">조 편성 운영 조건</h3>
              <p className="mt-2 text-sm leading-7 text-slate-600">
                {(activePlan.operation_dates?.join(", ") || `${activePlan.operation_days ?? 0}일`)} · 하루 {activePlan.team_requirements?.length ?? activePlan.teams_per_day ?? 0}개 조
                {activePlan.team_requirements?.map((team, index) => <span key={`${team.name}-${index}`} className="mt-2 block"><strong>{team.name || `${index + 1}조`} · {team.people_count}명</strong><br />{team.role_description || "역할 미작성"}</span>) ?? <span className="mt-2 block">{activePlan.team_role_description || "아직 작성하지 않음"}</span>}
              </p>
            </section>
            {planFields.map((field, index) => (
              <section
                key={field.key}
                className={`border-t border-slate-200 pt-3 ${index >= 4 ? "md:col-span-2" : ""}`}
              >
                <h3 className="text-sm font-bold text-slate-800">{field.label}</h3>
                <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-slate-600">
                  {activePlan[field.key] || "아직 작성하지 않음"}
                </p>
              </section>
            ))}
          </div>
        ) : null}

          {activePlan?.can_review && (
            <TextArea
              label="선생님 검토 의견"
              rows={4}
              maxLength={2000}
              value={reviewNote}
              onChange={event => setReviewNote(event.target.value)}
              placeholder="수정 요청을 보낼 때는 고쳐야 할 항목과 이유를 적어 주세요."
            />
          )}

          {activePlan && canEditPlan && (
            <section className="grid gap-3 border-t border-slate-200 pt-5">
              <div>
                <h3 className="text-sm font-bold text-slate-800">수정 제안 남기기</h3>
                <p className="mt-1 text-xs text-slate-500">직접 고치기 전에 다른 의견을 받고 싶다면 제안으로 남겨요.</p>
              </div>
              <SelectField
                label="제안할 항목"
                value={suggestionForm.section}
                onChange={event => setSuggestionForm(current => ({ ...current, section: event.target.value as PlanSuggestion["section"] }))}
              >
                {planFields.map(field => <option key={field.key} value={field.key}>{field.label}</option>)}
              </SelectField>
              <TextArea
                label="바꿀 내용"
                rows={4}
                maxLength={5000}
                value={suggestionForm.proposedContent}
                onChange={event => setSuggestionForm(current => ({ ...current, proposedContent: event.target.value }))}
              />
              <TextInput
                label="제안 이유"
                maxLength={1000}
                value={suggestionForm.reason}
                onChange={event => setSuggestionForm(current => ({ ...current, reason: event.target.value }))}
                placeholder="선택 사항"
              />
              <div className="flex justify-end">
                <Button variant="secondary" disabled={planSaving} onClick={() => void createPlanSuggestion()}>
                  수정 제안 남기기
                </Button>
              </div>
            </section>
          )}

          {planWorkspace?.suggestions.length ? (
            <section className="border-t border-slate-200 pt-5">
              <h3 className="text-sm font-bold text-slate-800">수정 제안</h3>
              <div className="mt-3 divide-y divide-slate-100 rounded-md border border-slate-200">
                {planWorkspace.suggestions.map(suggestion => (
                  <article key={suggestion.id} className="p-4">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <strong className="text-slate-700">{planFields.find(field => field.key === suggestion.section)?.label}</strong>
                      <span>{suggestion.author_name}</span>
                      <span>{formatTime(suggestion.created_at)}</span>
                      <span className="ml-auto font-semibold">{suggestion.status === "OPEN" ? "논의 중" : suggestion.status === "ADOPTED" ? "반영됨" : "반영하지 않음"}</span>
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{suggestion.proposed_content}</p>
                    {suggestion.reason && <p className="mt-2 text-xs text-slate-500">이유: {suggestion.reason}</p>}
                    {isPlanCoordinator && suggestion.status === "OPEN" && activePlan?.status !== "IN_REVIEW" && activePlan?.status !== "APPROVED" && (
                      <div className="mt-3 flex justify-end gap-2">
                        <Button size="sm" variant="secondary" disabled={planSaving} onClick={() => void resolvePlanSuggestion(suggestion.id, "REJECT")}>반영하지 않기</Button>
                        <Button size="sm" disabled={planSaving} onClick={() => void resolvePlanSuggestion(suggestion.id, "ADOPT")}>반영하기</Button>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {planWorkspace?.revisions.length ? (
            <section className="border-t border-slate-200 pt-5">
              <h3 className="text-sm font-bold text-slate-800">변경 기록</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {planWorkspace.revisions.slice(0, 8).map(revision => (
                  <span key={revision.id} className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-500">
                    v{revision.version} · {revision.editor_name} · {formatTime(revision.created_at)}
                  </span>
                ))}
              </div>
            </section>
          ) : null}

          {planError && (
            <p className="rounded-md bg-rose-50 px-3 py-2 text-sm text-[#a12622]">{planError}</p>
          )}
        </div>
      </AppModal>

      <AppModal
        open={createOpen}
        title="행사 아이디어 던지기"
        description="행사 이름과 전체 개요만 먼저 적어 주세요. 세부 계획은 의견을 모아 함께 발전시킵니다."
        onClose={() => {
          setCreateOpen(false);
          resetForm();
        }}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>취소</Button>
            <Button disabled={saving} onClick={() => void createPost()}>
              {saving ? "올리는 중…" : "게시판에 올리기"}
            </Button>
          </>
        }
      >
        <div className="grid gap-5">
          <TextInput
            label="해보고 싶은 행사"
            required
            maxLength={160}
            value={form.title}
            onChange={event => setForm(current => ({ ...current, title: event.target.value }))}
            placeholder="예: 점심시간 보물찾기"
            hint="행사 이름이나 핵심 생각을 한 줄로 적어 주세요."
          />
          <TextArea
            label="행사 전체 개요"
            required
            maxLength={5000}
            value={form.content}
            onChange={event => setForm(current => ({ ...current, content: event.target.value }))}
            placeholder="왜 필요한 행사인지, 누가 참여하고 대략 어떻게 진행할지 적어 주세요."
            hint="10자 이상 적어 주세요. 예산과 역할 같은 세부 계획은 나중에 함께 정할 수 있어요."
          />
          <fieldset>
            <legend className="text-sm font-semibold text-slate-800">이름 표시</legend>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setForm(current => ({ ...current, isAnonymous: true }))}
                className={`rounded-md border p-3 text-left ${
                  form.isAnonymous
                    ? "border-[#2563a8] bg-[#f4f8fc]"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <span className="block text-sm font-bold text-slate-900">익명으로 올리기</span>
                <span className="mt-1 block text-xs leading-5 text-slate-500">게시판에 이름이 보이지 않아요.</span>
              </button>
              <button
                type="button"
                onClick={() => setForm(current => ({ ...current, isAnonymous: false }))}
                className={`rounded-md border p-3 text-left ${
                  !form.isAnonymous
                    ? "border-[#2563a8] bg-[#f4f8fc]"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <span className="block text-sm font-bold text-slate-900">이름 공개하기</span>
                <span className="mt-1 block text-xs leading-5 text-slate-500">내 이름과 함께 아이디어가 보여요.</span>
              </button>
            </div>
          </fieldset>
          {formError && (
            <p className="rounded-md bg-rose-50 px-3 py-2 text-sm text-[#a12622]">{formError}</p>
          )}
        </div>
      </AppModal>

      <AppModal
        open={Boolean(conversionTarget)}
        title="실제 행사로 만들기"
        description={conversionTarget ? `${conversionTarget.title} 아이디어를 학생회 행사 일정에 등록합니다.` : undefined}
        onClose={() => {
          setConversionTarget(null);
          setFormError("");
        }}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConversionTarget(null)}>취소</Button>
            <Button disabled={saving} onClick={() => void convertToEvent()}>
              {saving ? "만드는 중…" : "행사로 만들기"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            className="sm:col-span-2"
            label="행사 날짜"
            type="date"
            required
            value={eventForm.eventDate}
            onChange={event => setEventForm(current => ({ ...current, eventDate: event.target.value }))}
          />
          <TextInput
            className="sm:col-span-2"
            label="장소"
            maxLength={200}
            value={eventForm.location}
            onChange={event => setEventForm(current => ({ ...current, location: event.target.value }))}
            placeholder="예: 운동장 또는 시청각실"
          />
          <TextInput
            label="시작 시간"
            type="time"
            value={eventForm.startsAt}
            onChange={event => setEventForm(current => ({ ...current, startsAt: event.target.value }))}
          />
          <TextInput
            label="종료 시간"
            type="time"
            value={eventForm.endsAt}
            onChange={event => setEventForm(current => ({ ...current, endsAt: event.target.value }))}
          />
          <p className="sm:col-span-2 rounded-md bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
            행사 제안자는 자동으로 담당자가 되지 않습니다. 확정하면 기획서에서 정한 조 편성·포스터
            담당자에게 업무와 알림이 가고, 현재 학생회 임원 모두가 행사 일정을 볼 수 있습니다.
          </p>
          {formError && (
            <p className="sm:col-span-2 rounded-md bg-rose-50 px-3 py-2 text-sm text-[#a12622]">
              {formError}
            </p>
          )}
        </div>
      </AppModal>
    </div>
  );
}
