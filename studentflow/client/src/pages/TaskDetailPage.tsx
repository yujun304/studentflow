/** StudentFlow | 업무 유형에 맞는 다음 행동을 한 화면에서 끝낸다. */
import {
  ArrowLeft,
  Bookmark,
  CheckCircle2,
  CornerDownRight,
  FileUp,
  MessageSquare,
  Paperclip,
  RefreshCw,
  Send,
  Trash2,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "@/components/MpaLink";
import { useApp } from "@/contexts/AppContext";
import { documentPathId } from "@/lib/document-path";
import { api, ApiError, jsonBody } from "@/lib/api";
import {
  createFormationPlan,
  type TeamFormationPreview,
} from "@/lib/team-formation";
import type { TaskType } from "@/types";
import { Calendar } from "@/components/ui/calendar";
import {
  AppModal,
  Button,
  SaveMessage,
  SelectField,
  StatusBadge,
  TextArea,
  TextInput,
} from "@/components/primitives";

const statusLabel = {
  TODO: "해야 할 일",
  IN_PROGRESS: "진행 중",
  DONE: "완료",
} as const;

const typeLabel: Record<TaskType, string> = {
  SIMPLE: "일반 업무",
  SUBMISSION: "파일 제출",
  TEAM_FORMATION: "자동 조 편성",
};

function defaultFormationDate() {
  const value = new Date();
  value.setDate(value.getDate() + 7);
  value.setHours(12, 0, 0, 0);
  return value;
}

function localDateKey(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function TaskDetailPage() {
  const taskId = documentPathId("/tasks");
  const {
    tasks,
    events,
    users,
    currentRole,
    currentUser,
    submitTask,
    updateTask,
    updateTaskStatus,
    deleteTask,
  } = useApp();
  const foundTask = tasks.find(item => item.id === taskId);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [formationOpen, setFormationOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editDraft, setEditDraft] = useState({ title: "", description: "" });
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [teamCount, setTeamCount] = useState(2);
  const [selectedDates, setSelectedDates] = useState<Date[]>([
    defaultFormationDate(),
  ]);
  const [teamPreview, setTeamPreview] = useState<TeamFormationPreview[]>([]);
  const [planWarnings, setPlanWarnings] = useState<string[]>([]);
  const [formationError, setFormationError] = useState("");
  const [formationSaving, setFormationSaving] = useState(false);
  const [submissions, setSubmissions] = useState<Array<{
    id: string;
    submitter_name: string;
    created_at: string;
    files: Array<{
      id: string;
      original_name: string;
      size: number;
      download_path: string;
    }>;
  }>>([]);
  const [comments, setComments] = useState<Array<{
    id: string;
    author_id: string;
    author_name: string;
    content: string;
    parent_id: string | null;
    created_at: string;
    can_delete: boolean;
    deleted: boolean;
  }>>([]);
  const [commentDraft, setCommentDraft] = useState("");
  const [replyTo, setReplyTo] = useState<{ id: string; authorName: string } | null>(null);
  const [commentSaving, setCommentSaving] = useState(false);
  const [commentError, setCommentError] = useState("");
  const [savedItemId, setSavedItemId] = useState<string | null>(null);
  const [bookmarkBusy, setBookmarkBusy] = useState(false);
  const selectedPeople = useMemo(
    () => users.filter(user => participantIds.includes(user.id)),
    [participantIds, users]
  );

  useEffect(() => {
    if (!taskId) return;
    api<typeof submissions>(`/tasks/${taskId}/submissions`)
      .then(setSubmissions)
      .catch(() => setSubmissions([]));
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;
    api<Array<{ id: string; target_type: string; target_id: string }>>("/saved-items")
      .then(items => {
        setSavedItemId(items.find(item => item.target_type === "task" && item.target_id === taskId)?.id ?? null);
      })
      .catch(() => setSavedItemId(null));
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;
    api<typeof comments>(`/comments?target_type=task&target_id=${taskId}`)
      .then(setComments)
      .catch(() => setComments([]));
  }, [taskId]);

  if (!foundTask) return <div className="p-8">업무를 찾을 수 없어요.</div>;
  const task = foundTask;
  const assignee = users.find(user => user.id === task.assigneeId);
  const ownTask = task.assignedToMe ?? task.assigneeId === currentUser.id;
  const eligiblePeople = users.filter(user => user.role !== "TEACHER");

  async function handleSubmit() {
    if (!selectedFile) {
      setFileError("제출할 파일을 선택해 주세요.");
      return;
    }
    setSaving(true);
    try {
      await submitTask(task.id, selectedFile);
      const refreshedSubmissions = await api<typeof submissions>(
        `/tasks/${task.id}/submissions`
      );
      setSubmissions(refreshedSubmissions);
      setSelectedFile(null);
      setSaved(true);
      setSubmitOpen(false);
    } catch {
      setFileError("파일을 제출하지 못했어요. 파일 형식과 크기를 확인해 주세요.");
    } finally {
      setSaving(false);
    }
  }

  async function removeTask() {
    if (!window.confirm(`“${task.title}” 업무를 삭제할까요? 삭제한 업무는 되돌릴 수 없습니다.`)) return;
    setSaving(true);
    try {
      await deleteTask(task.id);
      window.location.href = "/tasks";
    } catch (error) {
      setFileError(error instanceof ApiError ? error.message : "업무를 삭제하지 못했습니다.");
      setSaving(false);
    }
  }

  function openFormation() {
    const plannedTeamCount = task.teamRequirements?.length ?? task.teamsPerDay ?? 2;
    const requiredPeople = task.teamRequirements?.reduce((sum, team) => sum + team.peopleCount, 0)
      ?? (task.peoplePerTeam ? plannedTeamCount * task.peoplePerTeam : eligiblePeople.length);
    const event = events.find(item => item.id === task.eventId);
    const eventPeople = event?.participantIds?.length
      ? eligiblePeople.filter(user => event.participantIds?.includes(user.id))
      : eligiblePeople;
    const plannedPeople = eventPeople.slice(0, requiredPeople);
    const start = event?.dateKey ? new Date(`${event.dateKey}T12:00:00`) : defaultFormationDate();
    const plannedDates = task.operationDates?.length
      ? task.operationDates.map(date => new Date(`${date}T12:00:00`))
      : Array.from({ length: task.operationDays ?? 1 }, (_, index) => {
          const value = new Date(start);
          value.setDate(start.getDate() + index);
          return value;
        });
    const ids = plannedPeople.map(user => user.id);
    setParticipantIds(ids);
    setTeamCount(plannedTeamCount);
    setSelectedDates(plannedDates);
    const plan = createFormationPlan({
      people: plannedPeople,
      teamsPerDay: plannedTeamCount,
      dates: plannedDates.map(localDateKey),
      requirements: task.teamRequirements,
    });
    setTeamPreview(plan.teams);
    setPlanWarnings(plan.warnings);
    setFormationError("");
    setFormationOpen(true);
  }

  function toggleParticipant(userId: string) {
    const nextIds = participantIds.includes(userId)
      ? participantIds.filter(id => id !== userId)
      : [...participantIds, userId];
    setParticipantIds(nextIds);
    rebuildFormation(
      selectedDates,
      teamCount,
      users.filter(user => nextIds.includes(user.id))
    );
    setFormationError("");
  }

  function toggleAllParticipants() {
    const nextIds =
      participantIds.length === eligiblePeople.length
        ? []
        : eligiblePeople.map(user => user.id);
    setParticipantIds(nextIds);
    rebuildFormation(
      selectedDates,
      teamCount,
      eligiblePeople.filter(user => nextIds.includes(user.id))
    );
  }

  function rebuildFormation(
    nextDates = selectedDates,
    nextTeamCount = teamCount,
    nextPeople = selectedPeople
  ) {
    const plan = createFormationPlan({
      people: nextPeople,
      teamsPerDay: nextTeamCount,
      dates: nextDates.map(localDateKey),
      requirements: task.teamRequirements,
    });
    setTeamPreview(plan.teams);
    setPlanWarnings(plan.warnings);
    setFormationError("");
  }

  function removePreviewMember(teamIndex: number, userId: string) {
    setTeamPreview(previous =>
      previous.map((team, index) => {
        if (index !== teamIndex) return team;
        const members = team.members.filter(member => member.id !== userId);
        return { ...team, members, leaderId: members[0]?.id ?? "" };
      })
    );
  }

  function addPreviewMember(teamIndex: number, userId: string) {
    const person = users.find(user => user.id === userId);
    if (!person) return;
    setTeamPreview(previous => {
      const targetDate = previous[teamIndex]?.scheduleAt;
      const withoutPrevious = previous.map(team => {
        if (team.scheduleAt !== targetDate) return team;
        const members = team.members.filter(member => member.id !== userId);
        return { ...team, members, leaderId: members[0]?.id ?? "" };
      });
      return withoutPrevious.map((team, index) => {
        if (
          index !== teamIndex ||
          team.members.some(member => member.id === userId)
        )
          return team;
        const members = [...team.members, person];
        return { ...team, members, leaderId: team.leaderId || person.id };
      });
    });
  }

  function setPreviewLeader(teamIndex: number, leaderId: string) {
    setTeamPreview(previous =>
      previous.map((team, index) =>
        index === teamIndex ? { ...team, leaderId } : team
      )
    );
  }

  async function handleFormationSubmit() {
    if (!selectedDates.length) {
      setFormationError("조를 운영할 날짜를 한 개 이상 선택해 주세요.");
      return;
    }
    if (!teamPreview.length || teamPreview.some(team => !team.members.length)) {
      setFormationError("모든 조에 학생을 한 명 이상 배정해 주세요.");
      return;
    }
    setFormationSaving(true);
    setFormationError("");
    try {
      await api(`/tasks/${task.id}/team-formation`, {
        method: "POST",
        ...jsonBody({
          content: `${selectedDates.length}일 조 편성`,
          repeatable_member_ids: selectedDates.length > 1 ? participantIds : [],
          teams: teamPreview.map(team => ({
            name: team.name,
            description: null,
            role_description: team.roleDescription ?? null,
            leader_id: team.leaderId || null,
            member_ids: team.members.map(member => member.id),
            schedule_at: `${team.scheduleAt}:00+09:00`,
          })),
        }),
      });
      setFormationOpen(false);
      window.location.reload();
    } catch (error) {
      setFormationError(
        error instanceof ApiError
          ? error.message
          : "조 편성을 저장하지 못했어요. 배정 인원과 날짜를 확인해 주세요."
      );
    } finally {
      setFormationSaving(false);
    }
  }

  async function submitComment() {
    const content = commentDraft.trim();
    if (!content) return;
    setCommentSaving(true);
    setCommentError("");
    try {
      const created = await api<(typeof comments)[number]>("/comments", {
        method: "POST",
        ...jsonBody({
          target_type: "task",
          target_id: task.id,
          content,
          parent_id: replyTo?.id ?? null,
        }),
      });
      setComments(previous => [...previous, created]);
      setCommentDraft("");
      setReplyTo(null);
    } catch (error) {
      setCommentError(error instanceof ApiError ? error.message : "댓글을 등록하지 못했어요.");
    } finally {
      setCommentSaving(false);
    }
  }

  async function removeComment(commentId: string) {
    setCommentError("");
    try {
      await api(`/comments/${commentId}`, { method: "DELETE" });
      setComments(previous =>
        previous.map(comment =>
          comment.id === commentId
            ? { ...comment, content: "삭제된 댓글입니다.", deleted: true, can_delete: false }
            : comment
        )
      );
    } catch (error) {
      setCommentError(error instanceof ApiError ? error.message : "댓글을 삭제하지 못했어요.");
    }
  }

  async function toggleBookmark() {
    setBookmarkBusy(true);
    try {
      if (savedItemId) {
        await api(`/saved-items/${savedItemId}`, { method: "DELETE" });
        setSavedItemId(null);
      } else {
        const item = await api<{ id: string }>("/saved-items", {
          method: "POST",
          ...jsonBody({ target_type: "task", target_id: task.id }),
        });
        setSavedItemId(item.id);
      }
    } finally {
      setBookmarkBusy(false);
    }
  }

  function saveEdit() {
    if (editDraft.title.trim().length < 4) return;
    updateTask(task.id, editDraft);
    setEditOpen(false);
    setSaved(true);
  }

  const nextAction = (() => {
    if (task.status === "DONE")
      return (
        <>
          <CheckCircle2 size={24} className="text-[#17663d]" />
          <p className="mt-2 text-sm leading-6 text-slate-600">
            이 업무는 완료됐어요.
          </p>
        </>
      );
    if (ownTask && task.type === "TEAM_FORMATION")
      return (
        <>
          <p className="text-sm leading-6 text-slate-600">
            날짜와 참여자를 확인한 뒤 조 편성을 저장하면 배정된 학생에게
            알림과 개인 일정이 생성됩니다.
          </p>
          <Button onClick={openFormation} className="mt-4 w-full">
            <UsersRound size={17} /> 편성 미리보기
          </Button>
        </>
      );
    if (ownTask && task.type === "SUBMISSION")
      return (
        <>
          <p className="text-sm leading-6 text-slate-600">
            완성한 파일을 올리면 업무가 바로 완료돼요.
          </p>
          <Button onClick={() => setSubmitOpen(true)} className="mt-4 w-full">
            <FileUp size={17} /> 제출물 올리기
          </Button>
        </>
      );
    if (ownTask)
      return (
        <>
          <p className="text-sm leading-6 text-slate-600">
            업무를 마쳤다면 완료로 표시해 주세요.
          </p>
          <Button
            onClick={() => updateTaskStatus(task.id, "DONE")}
            className="mt-4 w-full"
          >
            <CheckCircle2 size={17} /> 완료로 표시
          </Button>
        </>
      );
    if (currentRole !== "MEMBER")
      return (
        <>
          <p className="text-sm leading-6 text-slate-600">
            업무 상태를 바꾸면 담당자에게 바로 표시됩니다.
          </p>
          <Button
            onClick={() => updateTaskStatus(task.id, "DONE")}
            className="mt-4 w-full"
          >
            <CheckCircle2 size={17} /> 완료로 처리하기
          </Button>
        </>
      );
    return (
      <p className="text-sm leading-6 text-slate-600">
        이 업무는 {assignee?.name}님이 담당하고 있어요.
      </p>
    );
  })();

  return (
    <div className="mx-auto max-w-[1020px] px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-3">
        <Link
          href="/tasks"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-[#2563a8]"
        >
          <ArrowLeft size={17} /> 업무 목록
        </Link>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => void toggleBookmark()} disabled={bookmarkBusy}>
            <Bookmark size={15} fill={savedItemId ? "currentColor" : "none"} />
            {savedItemId ? "저장됨" : "저장"}
          </Button>
          {task.canEdit && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setEditDraft({
                  title: task.title,
                  description: task.description,
                });
                setEditOpen(true);
              }}
            >
              업무 수정
            </Button>
          )}
          {task.canEdit && (
            <Button variant="danger" size="sm" disabled={saving} onClick={() => void removeTask()}>
              <Trash2 size={15} />업무 삭제
            </Button>
          )}
        </div>
      </div>

      <header className="mt-5 border-b border-slate-200 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={statusLabel[task.status]} />
          <span className="rounded bg-[#e8f0f8] px-2 py-1 text-xs font-semibold text-[#1f528b]">
            {typeLabel[task.type]}
          </span>
        </div>
        <h1 className="mt-3 text-2xl font-bold tracking-[-.03em] text-slate-900">
          {task.title}
        </h1>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-500">
          <span>{task.department}</span>
          <span>마감 {task.dueDate}</span>
          <span>{task.priority} 우선</span>
          <span className="flex items-center gap-1">
            <UserRound size={15} /> {assignee?.name}
          </span>
        </div>
      </header>

      <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_290px]">
        <section className="bg-white">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="font-bold">해야 할 내용</h2>
          </div>
          <div className="px-4 py-5">
            <p className="whitespace-pre-line text-sm leading-7 text-slate-700">
              {task.description}
            </p>
            {task.attachmentHint && (
              <div className="mt-5 flex items-center gap-2 border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-600">
                <Paperclip size={16} />
                <span>{task.attachmentHint}</span>
                <span className="ml-auto text-xs text-slate-500">
                  참고 파일
                </span>
              </div>
            )}
            {task.type === "SUBMISSION" && submissions.some(item => item.files.length) && (
              <section className="mt-6 border-t border-slate-200 pt-4">
                <h3 className="text-sm font-bold text-slate-800">제출된 파일</h3>
                <div className="mt-2 divide-y divide-slate-100 border-y border-slate-100">
                  {submissions.flatMap(submission =>
                    submission.files.map(file => (
                      <a
                        key={file.id}
                        href={file.download_path}
                        className="flex min-h-11 items-center gap-2 py-2.5 text-sm text-[#1f528b] hover:underline"
                      >
                        <Paperclip size={15} />
                        <span className="min-w-0 flex-1 truncate">{file.original_name}</span>
                        <span className="shrink-0 text-xs text-slate-500">
                          {submission.submitter_name} · {Math.max(1, Math.round(file.size / 1024))}KB
                        </span>
                      </a>
                    ))
                  )}
                </div>
                {currentRole === "TEACHER" && (
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    담당 선생님 권한으로 포스터 원본을 확인할 수 있어요.
                  </p>
                )}
              </section>
            )}
          </div>
        </section>
        <aside className="border-t-2 border-[#2563a8] bg-white">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="font-bold">다음 행동</h2>
          </div>
          <div className="p-4">
            {saved && <SaveMessage>변경한 내용을 저장했어요.</SaveMessage>}
            <div className={saved ? "mt-4" : ""}>{nextAction}</div>
          </div>
        </aside>
      </div>

      <section className="mt-7 border-t border-slate-200 bg-white">
        <header className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
          <MessageSquare size={17} className="text-[#2563a8]" />
          <h2 className="font-bold">업무 댓글</h2>
          <span className="text-xs text-slate-500">{comments.length}</span>
        </header>
        <div className="divide-y divide-slate-100">
          {comments.map(comment => (
            <article
              key={comment.id}
              className={`px-4 py-3 ${comment.parent_id ? "ml-6 border-l-2 border-slate-100 sm:ml-10" : ""}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-bold text-slate-700">
                    {comment.author_name}
                    <span className="ml-2 font-normal text-slate-400">
                      {new Intl.DateTimeFormat("ko-KR", {
                        month: "numeric",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      }).format(new Date(comment.created_at))}
                    </span>
                  </p>
                  <p className={`mt-1 whitespace-pre-wrap text-sm leading-6 ${comment.deleted ? "text-slate-400" : "text-slate-700"}`}>
                    {comment.content}
                  </p>
                </div>
                {!comment.deleted && (
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setReplyTo({ id: comment.id, authorName: comment.author_name })}
                      className="rounded p-1.5 text-slate-400 hover:bg-slate-100 hover:text-[#2563a8]"
                      aria-label={`${comment.author_name}님에게 답글`}
                    >
                      <CornerDownRight size={15} />
                    </button>
                    {comment.can_delete && (
                      <button
                        type="button"
                        onClick={() => void removeComment(comment.id)}
                        className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-[#b42318]"
                        aria-label="댓글 삭제"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </article>
          ))}
          {!comments.length && (
            <p className="px-4 py-6 text-center text-sm text-slate-500">
              아직 댓글이 없습니다. 진행 상황이나 질문을 남겨 보세요.
            </p>
          )}
        </div>
        <div className="border-t border-slate-200 p-4">
          {replyTo && (
            <div className="mb-2 flex items-center justify-between rounded bg-slate-50 px-3 py-2 text-xs text-slate-600">
              <span>{replyTo.authorName}님에게 답글 작성 중</span>
              <button type="button" onClick={() => setReplyTo(null)} className="font-semibold text-slate-500 hover:text-slate-800">
                취소
              </button>
            </div>
          )}
          <textarea
            value={commentDraft}
            onChange={event => setCommentDraft(event.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="진행 상황이나 확인할 내용을 남겨 주세요."
            className="w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-[#2563a8] focus:ring-2 focus:ring-[#2563a8]/15"
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="text-xs text-slate-400">{commentDraft.length}/2000</span>
            <Button size="sm" onClick={() => void submitComment()} disabled={commentSaving || !commentDraft.trim()}>
              {commentSaving ? "등록 중…" : "댓글 등록"}
            </Button>
          </div>
          {commentError && <p className="mt-2 text-sm font-semibold text-[#b42318]">{commentError}</p>}
        </div>
      </section>

      <AppModal
        open={formationOpen}
        title="날짜를 골라 조 편성"
        description="자동 편성 결과를 확인하고 필요한 학생을 옮긴 뒤 저장하세요."
        onClose={() => setFormationOpen(false)}
        size="xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setFormationOpen(false)}>
              취소
            </Button>
            <Button onClick={() => void handleFormationSubmit()} disabled={formationSaving}>
              {formationSaving ? "저장 중…" : "조 편성 저장"}
              <Send size={16} />
            </Button>
          </>
        }
      >
        <div className="grid gap-6">
          <section>
            <h3 className="mb-3 text-sm font-bold text-slate-800">
              편성 날짜와 조 개수
            </h3>
            <div className="grid gap-5 lg:grid-cols-[minmax(0,380px)_minmax(200px,1fr)] lg:items-start">
              <div>
                <Calendar
                  mode="multiple"
                  selected={selectedDates}
                  onSelect={dates => {
                    const nextDates = [...(dates ?? [])].sort(
                      (a, b) => a.getTime() - b.getTime()
                    );
                    setSelectedDates(nextDates);
                    rebuildFormation(nextDates, teamCount);
                  }}
                  className="w-full border border-slate-200 bg-white"
                  classNames={{ root: "w-full", month: "w-full" }}
                />
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  날짜를 누르면 선택되고, 다시 누르면 해제돼요.
                </p>
              </div>
              <div className="grid gap-4 border border-slate-200 bg-slate-50 p-4">
                {task.teamRequirements?.length ? (
                  <div className="rounded border border-slate-200 bg-white p-3 text-sm leading-6 text-slate-700">
                    <p className="font-bold text-slate-900">기획서 편성 기준</p>
                    <p>{task.operationDays}일 · 하루 {task.teamRequirements.length}개 조</p>
                    {task.teamRequirements.map(team => <p key={team.name} className="mt-1"><strong>{team.name} · {team.peopleCount}명{team.startTime ? ` · ${team.startTime}${team.endTime ? `~${team.endTime}` : ""}` : ""}</strong> — {team.roleDescription}</p>)}
                  </div>
                ) : task.peoplePerTeam && task.teamRoleDescription ? (
                  <div className="rounded border border-slate-200 bg-white p-3 text-sm leading-6 text-slate-700">{task.operationDays}일 · 하루 {task.teamsPerDay}개 조 · 조당 {task.peoplePerTeam}명<br />역할: {task.teamRoleDescription}</div>
                ) : null}
                <SelectField
                  label="하루 조 개수"
                  value={teamCount}
                  disabled={Boolean(task.teamsPerDay)}
                  onChange={event => {
                    const nextTeamCount = Number(event.target.value);
                    setTeamCount(nextTeamCount);
                    rebuildFormation(selectedDates, nextTeamCount);
                  }}
                >
                  {Array.from({ length: 8 }, (_, index) => index + 1).map(
                    count => (
                      <option key={count} value={count}>
                        {count}개 조
                      </option>
                    )
                  )}
                </SelectField>
                <div className="border-t border-slate-200 pt-3 text-sm leading-6 text-slate-600">
                  <p className="font-semibold text-slate-800">
                    {selectedDates.length}일 · 총{" "}
                    {selectedDates.length * teamCount}개 조
                  </p>
                  <p className="mt-1">
                    선택한 학생은 각 날짜에 한 번씩 배치돼요.
                  </p>
                  <p className="mt-1 font-semibold text-slate-800">
                    하루 필요 {task.teamRequirements?.reduce((sum, item) => sum + item.peopleCount, 0) ?? selectedPeople.length}명 · 현재 선택 {selectedPeople.length}명
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section>
            <div className="mb-2 flex items-center justify-between gap-3">
              <h3 className="text-sm font-bold text-slate-800">
                참여 학생 · {selectedPeople.length}명
              </h3>
              <button
                type="button"
                onClick={toggleAllParticipants}
                className="text-xs font-semibold text-[#2563a8]"
              >
                {participantIds.length === eligiblePeople.length
                  ? "전체 해제"
                  : "전체 선택"}
              </button>
            </div>
            <p className="mb-3 text-xs leading-5 text-slate-500">
              행사 참여자가 등록되어 있으면 해당 학생을 먼저 선택합니다. 제외할 학생만 체크를 해제하세요.
            </p>
            <div className="max-h-72 overflow-y-auto border-y border-slate-200 sm:grid sm:grid-cols-2">
              {eligiblePeople.map(user => (
                <div
                  key={user.id}
                  className={`border-b border-slate-100 px-3 py-3 sm:odd:border-r ${participantIds.includes(user.id) ? "bg-white" : "bg-slate-50 opacity-60"}`}
                >
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={participantIds.includes(user.id)}
                      onChange={() => toggleParticipant(user.id)}
                      className="h-4 w-4 accent-[#2563a8]"
                    />
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-slate-700">
                        {user.name}
                      </span>
                      <span className="block truncate text-[11px] text-slate-500">
                        {[user.grade, user.department]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                      <span className="block text-[11px] font-semibold text-[#2563a8]">
                        현재{" "}
                        {teamPreview.reduce(
                          (count, team) =>
                            count +
                            (team.members.some(member => member.id === user.id)
                              ? 1
                              : 0),
                          0
                        )}
                        회 배치
                      </span>
                    </span>
                  </label>
                </div>
              ))}
            </div>
          </section>

          <section>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-800">
                  편성 결과 직접 수정
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  이름 옆 ×로 빼고, 각 조 아래에서 학생을 추가하거나 이동할 수
                  있어요.
                </p>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => rebuildFormation()}
              >
                <RefreshCw size={15} /> 다시 계산
              </Button>
            </div>
            {planWarnings.length > 0 && (
              <div className="mb-3 border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
                {planWarnings.map(warning => (
                  <p key={warning}>{warning}</p>
                ))}
              </div>
            )}
            {teamPreview.length ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {teamPreview.map((team, teamIndex) => (
                  <div
                    key={`${team.name}-${team.scheduleAt}`}
                    className="border border-slate-200 bg-slate-50 p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-bold text-slate-800">
                          {team.name}
                        </p>
                        <p className="mt-0.5 text-[11px] text-slate-500">
                          {new Intl.DateTimeFormat("ko-KR", {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                            weekday: "short",
                          }).format(new Date(team.scheduleAt))}
                          {" · "}
                          {new Intl.DateTimeFormat("ko-KR", {
                            hour: "2-digit",
                            minute: "2-digit",
                          }).format(new Date(team.scheduleAt))}
                        </p>
                      </div>
                      <span className="text-xs text-slate-500">
                        {team.members.length}명
                      </span>
                    </div>
                    {team.roleDescription && (
                      <p className="mt-2 min-h-10 text-xs leading-5 text-slate-600">{team.roleDescription}</p>
                    )}
                    <div className="mt-3 flex min-h-9 flex-wrap gap-1.5">
                      {team.members.map(member => (
                        <span
                          key={member.id}
                          className="inline-flex items-center gap-1 rounded bg-white px-2 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200"
                        >
                          {member.name}
                          <button
                            type="button"
                            onClick={() =>
                              removePreviewMember(teamIndex, member.id)
                            }
                            aria-label={`${team.name}에서 ${member.name} 빼기`}
                            className="text-slate-400 hover:text-[#b42318]"
                          >
                            <X size={13} />
                          </button>
                        </span>
                      ))}
                      {!team.members.length && (
                        <span className="text-xs text-[#b42318]">
                          인원을 추가해 주세요.
                        </span>
                      )}
                    </div>
                    <label className="mt-3 grid gap-1 text-[11px] font-semibold text-slate-600">
                      조장
                      <select
                        value={team.leaderId}
                        onChange={event => setPreviewLeader(teamIndex, event.target.value)}
                        className="h-9 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700"
                      >
                        {team.members.map(member => (
                          <option key={member.id} value={member.id}>{member.name}</option>
                        ))}
                      </select>
                    </label>
                    <select
                      aria-label={`${team.name}에 학생 추가`}
                      defaultValue=""
                      onChange={event => {
                        addPreviewMember(teamIndex, event.target.value);
                        event.currentTarget.value = "";
                      }}
                      className="mt-3 h-9 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700"
                    >
                      <option value="" disabled>
                        학생 추가 또는 이동
                      </option>
                      {selectedPeople.map(person => (
                        <option key={person.id} value={person.id}>
                          {person.name}
                        </option>
                      ))}
                    </select>
                    <p className={`mt-2 text-[11px] font-semibold ${team.requiredPeople && team.members.length !== team.requiredPeople ? "text-[#b42318]" : "text-[#17663d]"}`}>
                      {team.requiredPeople
                        ? `정원 ${team.members.length}/${team.requiredPeople}명${team.members.length === team.requiredPeople ? " 충족" : " 확인 필요"}`
                        : `${team.members.length}명 배정`}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500">
                참여 학생을 선택하면 여기에 결과가 보여요.
              </p>
            )}
          </section>
          {formationError && (
            <p className="text-sm font-semibold text-[#b42318]">
              {formationError}
            </p>
          )}
        </div>
      </AppModal>

      <AppModal
        open={submitOpen}
        title="제출물 올리기"
        description="파일을 올리면 이 업무가 바로 완료됩니다."
        onClose={() => setSubmitOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSubmitOpen(false)}>
              취소
            </Button>
            <Button onClick={handleSubmit} disabled={saving}>
              {saving ? "올리는 중…" : "제출하고 완료"}
              <Send size={16} />
            </Button>
          </>
        }
      >
        <label className="grid gap-1.5">
          <span className="text-sm font-semibold text-slate-800">
            제출 파일 <span className="text-[#b42318]">*</span>
          </span>
          <input
            type="file"
            className="block w-full text-sm text-slate-600 file:mr-3 file:rounded file:border-0 file:bg-[#e8f0f8] file:px-3 file:py-2 file:text-sm file:font-semibold file:text-[#1f528b]"
            onChange={event => {
              setSelectedFile(event.target.files?.[0] ?? null);
              setFileError("");
            }}
          />
          {fileError && (
            <span className="text-xs text-[#b42318]">{fileError}</span>
          )}
        </label>
      </AppModal>

      <AppModal
        open={editOpen}
        title="업무 수정"
        description="수정한 제목과 설명이 담당자에게 바로 보입니다."
        onClose={() => setEditOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditOpen(false)}>
              취소
            </Button>
            <Button onClick={saveEdit}>수정 내용 저장하기</Button>
          </>
        }
      >
        <div className="grid gap-4">
          <TextInput
            label="업무 제목"
            value={editDraft.title}
            onChange={event =>
              setEditDraft({ ...editDraft, title: event.target.value })
            }
            required
          />
          <TextArea
            label="업무 설명"
            value={editDraft.description}
            onChange={event =>
              setEditDraft({ ...editDraft, description: event.target.value })
            }
          />
        </div>
      </AppModal>
    </div>
  );
}
