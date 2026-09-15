import { CalendarCheck, FileAudio, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Link } from "@/components/MpaLink";
import {
  Button,
  ErrorState,
  LoadingState,
  TextArea,
  TextInput,
} from "@/components/primitives";
import { useApp } from "@/contexts/AppContext";
import { api, jsonBody } from "@/lib/api";
import { planningStageLabel, type ProposalWorkflow } from "@/lib/proposals";

const value = (record: Record<string, unknown> | null, key: string) =>
  String(record?.[key] ?? "");

type MeetingRecordDraft = {
  title: string;
  held_at: string;
  location: string;
  summary: string;
  decisions: string;
  next_actions: string;
};

type PlanningTeamRequirement = {
  id: string;
  name: string;
  people_count: number | "";
  start_time: string;
  end_time: string;
  role_description: string;
  operation_dates: string[];
};

function newTeamRequirement(
  index: number,
  operationDates: string[]
): PlanningTeamRequirement {
  return {
    id: crypto.randomUUID(),
    name: `${index + 1}조`,
    people_count: 1,
    start_time: "",
    end_time: "",
    role_description: "",
    operation_dates: operationDates.filter(Boolean),
  };
}

function datetimeLocalValue(value: string | null) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  const local = new Date(
    parsed.getTime() - parsed.getTimezoneOffset() * 60_000
  );
  return local.toISOString().slice(0, 16);
}

export default function ProposalWorkflowPanel({
  proposalId,
}: {
  proposalId: string;
}) {
  const { currentRole, currentUser, users } = useApp();
  const [workflow, setWorkflow] = useState<ProposalWorkflow | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [brief, setBrief] = useState<Record<string, unknown>>({});
  const [transcript, setTranscript] = useState("");
  const [meetingNotes, setMeetingNotes] = useState("");
  const [finalPlan, setFinalPlan] = useState<Record<string, unknown>>({});
  const [operationDates, setOperationDates] = useState<string[]>([""]);
  const [teamRequirements, setTeamRequirements] = useState<
    PlanningTeamRequirement[]
  >([]);
  const [teamManagerId, setTeamManagerId] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [meetingRecordDraft, setMeetingRecordDraft] =
    useState<MeetingRecordDraft | null>(null);
  const canSaveMeetingRecord = [
    "DEPARTMENT_HEAD",
    "EXECUTIVE_BOARD",
    "TEACHER",
  ].includes(currentRole);

  const load = useCallback(async () => {
    setError("");
    try {
      const next = await api<ProposalWorkflow>(
        `/proposals/${proposalId}/workflow`
      );
      setWorkflow(next);
      setBrief(next.brief_plan ?? {});
      setFinalPlan(next.final_plan ?? {});
      setTranscript(next.meeting_transcript ?? "");
      setMeetingNotes(String(next.meeting_notes?.summary ?? ""));
      const loadedDates = Array.isArray(next.final_plan?.operation_dates)
        ? next.final_plan.operation_dates.map(String).filter(Boolean)
        : [];
      setOperationDates(loadedDates.length ? loadedDates : [""]);
      const loadedTeams = Array.isArray(next.final_plan?.team_requirements)
        ? next.final_plan.team_requirements.map(item => {
            const team = item as Record<string, unknown>;
            const teamDates = Array.isArray(team.operation_dates)
              ? team.operation_dates.map(String).filter(date => loadedDates.includes(date))
              : loadedDates;
            const peopleCount = Number(team.people_count);
            return {
              id: crypto.randomUUID(),
              name: String(team.name ?? ""),
              people_count:
                Number.isInteger(peopleCount) && peopleCount > 0
                  ? peopleCount
                  : "",
              start_time: String(team.start_time ?? ""),
              end_time: String(team.end_time ?? ""),
              role_description: String(team.role_description ?? ""),
              operation_dates: teamDates,
            } satisfies PlanningTeamRequirement;
          })
        : [];
      setTeamRequirements(loadedTeams);
      const loadedManagerId = next.plan?.team_manager_id ?? "";
      setTeamManagerId(
        users.some(
          user => user.id === loadedManagerId && user.role !== "TEACHER"
        )
          ? loadedManagerId
          : ""
      );
      setReviewNote(next.plan?.review_note ?? "");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "기획 진행 상태를 불러오지 못했습니다."
      );
    }
  }, [proposalId, users]);
  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    try {
      await action();
      await load();
      toast.success(success);
    } catch (reason) {
      toast.error(
        reason instanceof Error ? reason.message : "요청을 처리하지 못했습니다."
      );
    } finally {
      setBusy(false);
    }
  }
  function setBriefField(key: string, next: string) {
    setBrief(current => ({ ...current, [key]: next }));
  }
  function setFinalField(key: string, next: string) {
    setFinalPlan(current => ({ ...current, [key]: next }));
  }
  async function uploadAudio(file?: File) {
    if (!file) return;
    if (workflow && file.size > workflow.audio_max_bytes) {
      toast.error(
        `녹음 파일은 최대 ${Math.floor(workflow.audio_max_bytes / 1024 / 1024)}MB까지 올릴 수 있습니다.`
      );
      return;
    }
    const form = new FormData();
    form.append("upload", file);
    setBusy(true);
    let uploaded = false;
    try {
      await api(`/proposals/${proposalId}/meeting-audio`, {
        method: "POST",
        body: form,
      });
      uploaded = true;
      if (workflow?.can_transcribe) {
        await api(`/proposals/${proposalId}/transcribe-meeting-audio`, {
          method: "POST",
        });
        toast.success("녹음을 올리고 Whisper 전사 결과를 불러왔습니다.");
      } else {
        toast.success(
          "회의 녹음을 올렸습니다. 서버의 로컬 Whisper 설정을 확인해 주세요."
        );
      }
    } catch (reason) {
      const message =
        reason instanceof Error
          ? reason.message
          : "요청을 처리하지 못했습니다.";
      toast.error(
        uploaded ? `녹음은 저장됐지만 전사하지 못했습니다. ${message}` : message
      );
    } finally {
      await load();
      setBusy(false);
    }
  }
  function saveFinal() {
    return run(
      () =>
        api(`/proposals/${proposalId}/final-plan`, {
          method: "PUT",
          ...jsonBody({ document: finalDocument() }),
        }),
      "최종 기획서를 저장했습니다."
    );
  }
  const normalizedOperationDates = operationDates.filter(Boolean);
  const hasDuplicateOperationDate =
    new Set(normalizedOperationDates).size !== normalizedOperationDates.length;
  const hasOperationDateWithoutTeam = normalizedOperationDates.some(
    operationDate =>
      !teamRequirements.some(team => team.operation_dates.includes(operationDate))
  );
  const hasInvalidTeamRequirement = teamRequirements.some(
    item =>
      !item.name.trim() ||
      !Number.isInteger(item.people_count) ||
      Number(item.people_count) < 1 ||
      Number(item.people_count) > 20 ||
      !item.role_description.trim() ||
      !item.operation_dates.length
  );
  function finalDocument() {
    const operation_dates = normalizedOperationDates;
    const team_requirements = teamRequirements.map(({ id: _id, ...team }) => ({
      ...team,
      name: team.name.trim(),
      people_count: Number(team.people_count),
      role_description: team.role_description.trim(),
      start_time: team.start_time || null,
      end_time: team.end_time || null,
      operation_dates: team.operation_dates.filter(date =>
        operation_dates.includes(date)
      ),
    }));
    return { ...finalPlan, operation_dates, team_requirements, team_manager_id: teamManagerId || null };
  }
  function updateOperationDate(index: number, nextDate: string) {
    const previousDate = operationDates[index];
    setOperationDates(current =>
      current.map((date, dateIndex) => (dateIndex === index ? nextDate : date))
    );
    if (!previousDate) return;
    setTeamRequirements(current =>
      current.map(team => ({
        ...team,
        operation_dates: team.operation_dates.map(date =>
          date === previousDate ? nextDate : date
        ).filter(Boolean),
      }))
    );
  }
  function removeOperationDate(index: number) {
    const removedDate = operationDates[index];
    setOperationDates(current => current.filter((_, dateIndex) => dateIndex !== index));
    setTeamRequirements(current =>
      current.map(team => ({
        ...team,
        operation_dates: team.operation_dates.filter(date => date !== removedDate),
      }))
    );
  }
  function updateTeam(
    id: string,
    values: Partial<PlanningTeamRequirement>
  ) {
    setTeamRequirements(current =>
      current.map(team => (team.id === id ? { ...team, ...values } : team))
    );
  }
  function toggleTeamDate(teamId: string, operationDate: string) {
    setTeamRequirements(current =>
      current.map(team => {
        if (team.id !== teamId) return team;
        const selected = team.operation_dates.includes(operationDate);
        return {
          ...team,
          operation_dates: selected
            ? team.operation_dates.filter(date => date !== operationDate)
            : [...team.operation_dates, operationDate],
        };
      })
    );
  }
  async function saveAndSubmitFinal() {
    if (
      !window.confirm(
        "현재 작성 내용을 저장하고 선생님께 최종 검토를 요청할까요?"
      )
    )
      return;
    setBusy(true);
    try {
      const saved = await api<ProposalWorkflow>(
        `/proposals/${proposalId}/final-plan`,
        {
          method: "PUT",
          ...jsonBody({ document: finalDocument() }),
        }
      );
      const version = saved.plan?.version;
      if (!version)
        throw new Error("저장된 기획서 버전을 확인하지 못했습니다.");
      await api(`/community/${proposalId}/plan/submit`, {
        method: "POST",
        ...jsonBody({ base_version: version }),
      });
      await load();
      toast.success("최종 기획서를 저장하고 선생님께 검토를 요청했습니다.");
    } catch (reason) {
      await load();
      toast.error(
        reason instanceof Error
          ? reason.message
          : "최종 기획서를 제출하지 못했습니다."
      );
    } finally {
      setBusy(false);
    }
  }
  async function generateMeetingRecordDraft() {
    setBusy(true);
    try {
      const draft = await api<
        Omit<MeetingRecordDraft, "held_at"> & { held_at: string | null }
      >(`/proposals/${proposalId}/generate-meeting-record-draft`, {
        method: "POST",
        ...jsonBody({ transcript }),
      });
      setMeetingRecordDraft({
        ...draft,
        held_at: datetimeLocalValue(draft.held_at),
      });
      toast.success("음성인식 원문으로 부장 회의록 양식을 채웠습니다.");
    } catch (reason) {
      toast.error(
        reason instanceof Error
          ? reason.message
          : "부장 회의록을 만들지 못했습니다."
      );
    } finally {
      setBusy(false);
    }
  }
  async function saveMeetingRecord() {
    if (!meetingRecordDraft?.title.trim() || !meetingRecordDraft.held_at)
      return;
    setBusy(true);
    try {
      await api("/meeting-records", {
        method: "POST",
        ...jsonBody({
          title: meetingRecordDraft.title.trim(),
          held_at: new Date(meetingRecordDraft.held_at).toISOString(),
          location: meetingRecordDraft.location.trim() || null,
          summary: meetingRecordDraft.summary.trim() || null,
          decisions: meetingRecordDraft.decisions.trim() || null,
          next_actions: meetingRecordDraft.next_actions.trim() || null,
          attendee_ids: [],
        }),
      });
      await api(`/proposals/${proposalId}/meeting-notes`, {
        method: "PUT",
        ...jsonBody({
          transcript,
          manual_notes: [
            meetingRecordDraft.summary,
            meetingRecordDraft.decisions,
            meetingRecordDraft.next_actions,
          ]
            .map(item => item.trim())
            .filter(Boolean)
            .join("\n"),
        }),
      });
      await load();
      toast.success("부장 회의록을 저장하고 일정·시간·필요 인원을 자동으로 채웠습니다.");
    } catch (reason) {
      toast.error(
        reason instanceof Error
          ? reason.message
          : "회의록을 저장하지 못했습니다."
      );
    } finally {
      setBusy(false);
    }
  }

  if (error)
    return (
      <section className="border-b border-slate-200 py-7">
        <ErrorState description={error} onRetry={() => void load()} />
      </section>
    );
  if (!workflow)
    return (
      <section className="border-b border-slate-200 py-7">
        <LoadingState />
      </section>
    );
  const requiredFinalFields = [
    ["purpose", "목적"],
    ["target_participants", "대상"],
    ["schedule_plan", "일정 계획"],
    ["location_plan", "장소 계획"],
    ["program_plan", "진행 방식"],
    ["role_plan", "역할 계획"],
    ["budget_plan", "예산과 준비물"],
    ["safety_plan", "안전·비상 계획"],
  ] as const;
  const submissionMissing: string[] = requiredFinalFields
    .filter(([key]) => !value(finalPlan, key).trim())
    .map(([, label]) => label);
  if (!normalizedOperationDates.length || operationDates.some(date => !date))
    submissionMissing.push("운영 날짜");
  else if (hasDuplicateOperationDate) submissionMissing.push("중복되지 않은 운영 날짜");
  else if (hasOperationDateWithoutTeam)
    submissionMissing.push("각 운영 날짜에 배정할 조");
  if (!teamRequirements.length || hasInvalidTeamRequirement)
    submissionMissing.push("조별 이름·인원·역할·운영 날짜");
  if (!teamManagerId) submissionMissing.push("조 편성 담당자");
  const canRequestReview = Boolean(
    workflow.plan &&
      workflow.plan.author_id === currentUser.id &&
      ["DRAFT", "CHANGES_REQUESTED", "REJECTED"].includes(workflow.plan.status)
  );
  return (
    <section className="border-b border-slate-200 py-7">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">기획 및 실행</h2>
          <p className="mt-1 text-sm text-slate-500">
            현재 단계 · {planningStageLabel[workflow.stage]}
          </p>
        </div>
        {workflow.can_promote && workflow.stage === "DISCUSSING" && (
          <Button
            disabled={busy}
            onClick={() =>
              void run(
                () =>
                  api(`/proposals/${proposalId}/agenda`, { method: "POST" }),
                "부장 회의 안건과 간이 기획서를 만들었습니다."
              )
            }
          >
            부장 회의 안건으로 전환
          </Button>
        )}
      </div>
      {workflow.brief_plan && (
        <div className="mt-6 border-t border-slate-200 pt-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-bold">회의 전 간이 기획서</h3>
              <p className="mt-1 text-xs text-slate-500">
                가장 최근 기획서와 현재 버전의 학생 의견을 LLM이 JSON으로 정리한
                초안입니다. 각 칸을 확인하고 직접 수정해 주세요.
              </p>
            </div>
            {workflow.can_manage && (
              <div className="text-right">
                <Button
                  variant="secondary"
                  disabled={busy || !workflow.can_generate_brief}
                  onClick={() =>
                    void run(
                      () =>
                        api(`/proposals/${proposalId}/brief/draft`, {
                          method: "POST",
                        }),
                      "최신 기획서와 학생 의견으로 각 칸을 다시 채웠습니다."
                    )
                  }
                >
                  <RefreshCw size={16} className={busy ? "animate-spin" : ""} />
                  AI 초안 다시 작성
                </Button>
                {!workflow.can_generate_brief && (
                  <p className="mt-1 text-xs text-slate-500">
                    AI를 사용할 수 없어도 아래 칸을 직접 작성하고 저장할 수
                    있습니다.
                  </p>
                )}
              </div>
            )}
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <TextInput
              label="행사명"
              value={value(brief, "title")}
              onChange={event => setBriefField("title", event.target.value)}
            />
            <TextInput
              label="예상 대상"
              value={value(brief, "expected_participants")}
              onChange={event =>
                setBriefField("expected_participants", event.target.value)
              }
            />
            <TextArea
              className="sm:col-span-2"
              label="배경"
              value={value(brief, "background")}
              onChange={event =>
                setBriefField("background", event.target.value)
              }
            />
            <TextArea
              className="sm:col-span-2"
              label="목적"
              value={value(brief, "purpose")}
              onChange={event => setBriefField("purpose", event.target.value)}
            />
            <TextInput
              label="예상 일시"
              value={value(brief, "expected_date")}
              onChange={event =>
                setBriefField("expected_date", event.target.value)
              }
            />
            <TextInput
              label="예상 장소"
              value={value(brief, "expected_location")}
              onChange={event =>
                setBriefField("expected_location", event.target.value)
              }
            />
            <TextArea
              className="sm:col-span-2"
              label="예상 운영 방식"
              value={value(brief, "expected_operation")}
              onChange={event =>
                setBriefField("expected_operation", event.target.value)
              }
            />
          </div>
          {workflow.can_manage && (
            <div className="mt-3 flex justify-end">
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void run(
                    () =>
                      api(`/proposals/${proposalId}/brief`, {
                        method: "PUT",
                        ...jsonBody({ document: brief }),
                      }),
                    "간이 기획서를 저장했습니다."
                  )
                }
              >
                간이 기획서 저장
              </Button>
            </div>
          )}
        </div>
      )}
      {workflow.can_manage && workflow.brief_plan && (
        <div className="mt-6 border-t border-slate-200 pt-6">
          <h3 className="font-bold">부장 회의 결과</h3>
          <p className="mt-1 text-xs text-slate-500">
            회의록을 저장하면 확정된 날짜·시간·조별 필요 인원을 찾아 최종
            기획서와 조 편성 기준에 자동으로 넣습니다. 결과는 제출 전에 수정할 수 있습니다.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 border border-slate-300 px-3 text-sm font-semibold">
              <FileAudio size={16} />
              녹음 선택 (선택)
              <input
                className="sr-only"
                type="file"
                accept={workflow.audio_extensions
                  .map(ext => `.${ext}`)
                  .join(",")}
                onChange={event => void uploadAudio(event.target.files?.[0])}
              />
            </label>
            <span className="text-xs text-slate-500">
              {workflow.audio_extensions.join(", ")} · 최대{" "}
              {Math.floor(workflow.audio_max_bytes / 1024 / 1024)}MB
            </span>
            {workflow.meeting_audio && (
              <a
                className="text-sm font-semibold text-[#2563a8]"
                href={workflow.meeting_audio.download_path}
              >
                {workflow.meeting_audio.original_name}
              </a>
            )}
          </div>
          {workflow.meeting_audio && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button
                variant="secondary"
                disabled={busy || !workflow.can_transcribe}
                onClick={() =>
                  void run(
                    () =>
                      api(`/proposals/${proposalId}/transcribe-meeting-audio`, {
                        method: "POST",
                      }),
                    "Whisper 전사 결과를 불러왔습니다."
                  )
                }
              >
                <RefreshCw size={16} className={busy ? "animate-spin" : ""} />
                Whisper 전사 다시 실행
              </Button>
              {!workflow.can_transcribe && (
                <span className="text-xs text-slate-500">
                  서버에 API 키와 Whisper 모델을 설정하면 전사할 수 있습니다.
                </span>
              )}
            </div>
          )}
          <div className="mt-4 grid gap-3">
            <div className="border-l-2 border-[#2563a8] bg-slate-50 p-4">
              <p className="text-sm font-bold text-slate-800">음성인식 원문</p>
              <p className="mt-1 text-xs text-slate-500">
                자동 인식 결과를 확인해 수정하거나, 인식하지 못한 경우 직접 붙여
                넣으세요.
              </p>
              <div className="mt-3">
                <TextArea
                  label="전사된 텍스트"
                  rows={8}
                  placeholder="음성인식 결과가 여기에 표시됩니다. 직접 입력해도 됩니다."
                  value={transcript}
                  onChange={event => setTranscript(event.target.value)}
                />
              </div>
              <div className="mt-3 flex flex-wrap justify-end gap-2">
                <Button
                  variant="secondary"
                  disabled={
                    busy || !workflow.can_auto_process || !transcript.trim()
                  }
                  onClick={() => void generateMeetingRecordDraft()}
                >
                  기존 양식으로 부장 회의록 작성
                </Button>
                <Button
                  disabled={
                    busy || !workflow.can_auto_process || !transcript.trim()
                  }
                  onClick={() =>
                    void run(
                      () =>
                        api(
                          `/proposals/${proposalId}/generate-plan-from-transcript`,
                          {
                            method: "POST",
                            ...jsonBody({ transcript, manual_notes: null }),
                          }
                        ),
                      "확인한 녹취로 기획서를 작성했습니다."
                    )
                  }
                >
                  이 녹취로 AI 기획서 채우기
                </Button>
              </div>
              {!workflow.can_auto_process && (
                <p className="mt-2 text-xs text-slate-500">
                  AI 작성이 꺼져 있어도 아래 회의 결과를 직접 저장한 뒤 최종
                  기획서 초안을 만들 수 있습니다.
                </p>
              )}
            </div>
            {meetingRecordDraft && (
              <div className="border border-slate-200 p-4">
                <h4 className="font-bold text-slate-800">부장 회의록 양식</h4>
                <p className="mt-1 text-xs text-slate-500">
                  AI가 채운 내용을 확인하고 수정한 뒤 저장해 주세요. 참석자는
                  자동 지정하지 않습니다.
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <TextInput
                    label="회의 제목"
                    required
                    value={meetingRecordDraft.title}
                    onChange={event =>
                      setMeetingRecordDraft({
                        ...meetingRecordDraft,
                        title: event.target.value,
                      })
                    }
                  />
                  <TextInput
                    label="회의 일시"
                    type="datetime-local"
                    required
                    value={meetingRecordDraft.held_at}
                    onChange={event =>
                      setMeetingRecordDraft({
                        ...meetingRecordDraft,
                        held_at: event.target.value,
                      })
                    }
                  />
                  <TextInput
                    className="sm:col-span-2"
                    label="장소"
                    value={meetingRecordDraft.location}
                    onChange={event =>
                      setMeetingRecordDraft({
                        ...meetingRecordDraft,
                        location: event.target.value,
                      })
                    }
                  />
                  <TextArea
                    className="sm:col-span-2"
                    label="회의 요약"
                    rows={5}
                    value={meetingRecordDraft.summary}
                    onChange={event =>
                      setMeetingRecordDraft({
                        ...meetingRecordDraft,
                        summary: event.target.value,
                      })
                    }
                  />
                  <TextArea
                    label="결정사항"
                    rows={6}
                    value={meetingRecordDraft.decisions}
                    onChange={event =>
                      setMeetingRecordDraft({
                        ...meetingRecordDraft,
                        decisions: event.target.value,
                      })
                    }
                  />
                  <TextArea
                    label="다음 할 일"
                    rows={6}
                    value={meetingRecordDraft.next_actions}
                    onChange={event =>
                      setMeetingRecordDraft({
                        ...meetingRecordDraft,
                        next_actions: event.target.value,
                      })
                    }
                  />
                </div>
                {canSaveMeetingRecord ? (
                  <div className="mt-3 flex justify-end">
                    <Button
                      disabled={
                        busy ||
                        !meetingRecordDraft.title.trim() ||
                        !meetingRecordDraft.held_at
                      }
                      onClick={() => void saveMeetingRecord()}
                    >
                      부장 회의록 저장
                    </Button>
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-slate-500">
                    부장단·회장단·선생님이 검토 후 회의록으로 저장할 수
                    있습니다.
                  </p>
                )}
              </div>
            )}
            <TextArea
              label="회의 결과 직접 입력"
              rows={7}
              value={meetingNotes}
              onChange={event => setMeetingNotes(event.target.value)}
            />
            <div className="flex justify-end">
              <Button
                variant="secondary"
                disabled={busy || (!transcript.trim() && !meetingNotes.trim())}
                onClick={() =>
                  void run(
                    () =>
                      api(`/proposals/${proposalId}/meeting-notes`, {
                        method: "PUT",
                        ...jsonBody({
                          transcript,
                          manual_notes: meetingNotes.trim() || null,
                        }),
                      }),
                    "부장 회의 결과를 저장했습니다."
                  )
                }
              >
                회의 결과 저장하고 일정·인원 자동 채우기
              </Button>
            </div>
          </div>
        </div>
      )}
      {workflow.meeting_notes && (
        <div className="mt-6 border-t border-slate-200 pt-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-bold">최종 기획서</h3>
              <p className="mt-1 text-xs text-slate-500">
                회의에 없는 결정은 자동으로 채우지 않습니다.
              </p>
            </div>
            {workflow.can_manage && !workflow.final_plan && (
              <Button
                disabled={busy}
                onClick={() =>
                  void run(
                    () =>
                      api(`/proposals/${proposalId}/final-plan`, {
                        method: "POST",
                      }),
                    "최종 기획서 초안을 만들었습니다."
                  )
                }
              >
                <RefreshCw size={16} />
                초안 생성
              </Button>
            )}
          </div>
          {workflow.final_plan && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <TextArea
                label="목적"
                value={value(finalPlan, "purpose")}
                onChange={event => setFinalField("purpose", event.target.value)}
              />
              <TextArea
                label="대상"
                value={value(finalPlan, "target_participants")}
                onChange={event =>
                  setFinalField("target_participants", event.target.value)
                }
              />
              <TextArea
                label="일정 계획"
                value={value(finalPlan, "schedule_plan")}
                onChange={event =>
                  setFinalField("schedule_plan", event.target.value)
                }
              />
              <TextArea
                label="장소 계획"
                value={value(finalPlan, "location_plan")}
                onChange={event =>
                  setFinalField("location_plan", event.target.value)
                }
              />
              <TextArea
                label="진행 방식"
                value={value(finalPlan, "program_plan")}
                onChange={event =>
                  setFinalField("program_plan", event.target.value)
                }
              />
              <TextArea
                label="역할 계획"
                value={value(finalPlan, "role_plan")}
                onChange={event =>
                  setFinalField("role_plan", event.target.value)
                }
              />
              <TextArea
                label="예산과 준비물"
                value={value(finalPlan, "budget_plan")}
                onChange={event =>
                  setFinalField("budget_plan", event.target.value)
                }
              />
              <TextArea
                label="안전·비상 계획"
                value={value(finalPlan, "safety_plan")}
                onChange={event =>
                  setFinalField("safety_plan", event.target.value)
                }
              />
              <div className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-4 sm:col-span-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h4 className="text-sm font-bold text-slate-800">운영 날짜</h4>
                    <p className="mt-1 text-xs text-slate-500">
                      달력에서 날짜를 고른 뒤 그날 운영할 조를 선택하세요.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setOperationDates(current => [...current, ""])}
                  >
                    <Plus size={15} /> 날짜 추가
                  </Button>
                </div>
                {operationDates.map((operationDate, dateIndex) => (
                  <div
                    key={`${operationDate}-${dateIndex}`}
                    className="grid gap-3 border-t border-slate-200 pt-3 sm:grid-cols-[180px_1fr_auto]"
                  >
                    <label className="grid gap-1 text-sm font-semibold text-slate-700">
                      {dateIndex + 1}일차
                      <input
                        type="date"
                        className="h-11 rounded-md border border-slate-300 bg-white px-3 text-sm font-normal"
                        value={operationDate}
                        onChange={event =>
                          updateOperationDate(dateIndex, event.target.value)
                        }
                      />
                    </label>
                    <fieldset className="min-w-0">
                      <legend className="text-sm font-semibold text-slate-700">
                        이 날짜에 운영할 조
                      </legend>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
                        {teamRequirements.map((team, teamIndex) => (
                          <label
                            key={team.id}
                            className="inline-flex items-center gap-2 text-sm text-slate-700"
                          >
                            <input
                              type="checkbox"
                              disabled={!operationDate}
                              checked={
                                Boolean(operationDate) &&
                                team.operation_dates.includes(operationDate)
                              }
                              onChange={() => toggleTeamDate(team.id, operationDate)}
                            />
                            {team.name.trim() || `${teamIndex + 1}조`}
                          </label>
                        ))}
                      </div>
                    </fieldset>
                    <button
                      type="button"
                      disabled={operationDates.length === 1}
                      onClick={() => removeOperationDate(dateIndex)}
                      className="inline-flex h-11 w-11 items-center justify-center self-end rounded border border-slate-300 bg-white text-slate-500 disabled:opacity-40"
                      aria-label={`${dateIndex + 1}일차 날짜 삭제`}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
              <div className="grid gap-3 sm:col-span-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h4 className="text-sm font-bold text-slate-800">조 구성</h4>
                    <p className="mt-1 text-xs text-slate-500">
                      조마다 필요한 내용을 각각 입력하세요.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() =>
                      setTeamRequirements(current => [
                        ...current,
                        newTeamRequirement(current.length, normalizedOperationDates),
                      ])
                    }
                  >
                    <Plus size={15} /> 조 추가
                  </Button>
                </div>
                {teamRequirements.map((team, teamIndex) => (
                  <div
                    key={team.id}
                    className="grid gap-3 rounded-md border border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-[1fr_120px_140px_140px_auto]"
                  >
                    <TextInput
                      label="조 이름"
                      value={team.name}
                      onChange={event => updateTeam(team.id, { name: event.target.value })}
                    />
                    <TextInput
                      label="필요 인원"
                      type="number"
                      min={1}
                      max={20}
                      value={team.people_count}
                      onChange={event =>
                        updateTeam(team.id, {
                          people_count: event.target.value
                            ? Number(event.target.value)
                            : "",
                        })
                      }
                    />
                    <TextInput
                      label="시작 시간"
                      type="time"
                      value={team.start_time}
                      onChange={event =>
                        updateTeam(team.id, { start_time: event.target.value })
                      }
                    />
                    <TextInput
                      label="종료 시간"
                      type="time"
                      value={team.end_time}
                      onChange={event =>
                        updateTeam(team.id, { end_time: event.target.value })
                      }
                    />
                    <button
                      type="button"
                      disabled={teamRequirements.length === 1}
                      onClick={() =>
                        setTeamRequirements(current =>
                          current.filter(item => item.id !== team.id)
                        )
                      }
                      className="mt-6 inline-flex h-11 w-11 items-center justify-center rounded border border-slate-300 text-slate-500 disabled:opacity-40"
                      aria-label={`${team.name || `${teamIndex + 1}조`} 삭제`}
                    >
                      <Trash2 size={16} />
                    </button>
                    <TextArea
                      className="sm:col-span-2 lg:col-span-5"
                      label={`${team.name.trim() || `${teamIndex + 1}조`} 역할`}
                      rows={2}
                      value={team.role_description}
                      onChange={event =>
                        updateTeam(team.id, { role_description: event.target.value })
                      }
                      placeholder="예: 정문에서 참가자 확인과 이동 안내"
                    />
                  </div>
                ))}
                {!teamRequirements.length && (
                  <p className="rounded-md border border-dashed border-slate-300 px-4 py-5 text-center text-sm text-slate-500">
                    아직 조가 없습니다. ‘조 추가’를 눌러 필요한 조를 입력하세요.
                  </p>
                )}
              </div>
              <label className="grid gap-1 text-sm font-semibold text-slate-700">
                조 편성 담당자
                <select
                  className="min-h-11 border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900"
                  value={teamManagerId}
                  onChange={event => setTeamManagerId(event.target.value)}
                >
                  <option value="">담당 학생 선택</option>
                  {users.filter(user => user.role !== "TEACHER").map(user => (
                    <option key={user.id} value={user.id}>
                      {user.name} · {user.department}
                    </option>
                  ))}
                </select>
              </label>
              {workflow.can_manage && (
                <div className="sm:col-span-2">
                  {canRequestReview && submissionMissing.length > 0 && (
                    <p className="mb-3 text-sm text-amber-700">
                      제출 전 작성할 항목: {submissionMissing.join(", ")}
                    </p>
                  )}
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button
                      variant="secondary"
                      disabled={busy}
                      onClick={() => void saveFinal()}
                    >
                      최종 기획서 저장
                    </Button>
                    {canRequestReview && (
                      <Button
                        disabled={busy || submissionMissing.length > 0}
                        onClick={() => void saveAndSubmitFinal()}
                      >
                        저장 후 교사 검토 요청
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {workflow.plan?.can_review && (
        <div className="mt-6 border-t border-slate-200 pt-6">
          <h3 className="font-bold">교사 최종 검토</h3>
          <p className="mt-1 text-sm text-slate-600">
            승인하면 행사와 조 편성 업무가 실제로 생성되고, 위에서 선택한 담당 학생에게 배정됩니다.
          </p>
          <TextArea
            className="mt-3"
            label="피드백"
            value={reviewNote}
            onChange={event => setReviewNote(event.target.value)}
          />
          <div className="mt-3 flex flex-wrap justify-end gap-2">
            <Button
              variant="secondary"
              disabled={busy || !reviewNote.trim()}
              onClick={() =>
                void run(
                  () =>
                    api(`/community/${proposalId}/plan/review`, {
                      method: "POST",
                      ...jsonBody({
                        action: "REJECT",
                        note: reviewNote.trim(),
                      }),
                    }),
                  "기획서를 반려했습니다."
                )
              }
            >
              반려
            </Button>
            <Button
              variant="secondary"
              disabled={busy || !reviewNote.trim()}
              onClick={() =>
                void run(
                  () =>
                    api(`/community/${proposalId}/plan/review`, {
                      method: "POST",
                      ...jsonBody({
                        action: "REQUEST_CHANGES",
                        note: reviewNote.trim(),
                      }),
                    }),
                  "수정 요청을 보냈습니다."
                )
              }
            >
              수정 요청
            </Button>
            <Button
              disabled={busy}
              onClick={() =>
                void run(
                  () =>
                    api(`/community/${proposalId}/plan/review`, {
                      method: "POST",
                      ...jsonBody({
                        action: "APPROVE",
                        note: reviewNote.trim() || null,
                      }),
                    }),
                  "기획서를 승인했습니다."
                )
              }
            >
              승인
            </Button>
          </div>
        </div>
      )}
      {workflow.plan?.review_note && !workflow.plan.can_review && (
        <p className="mt-5 border-l-2 border-slate-300 pl-4 text-sm text-slate-600">
          교사 피드백: {workflow.plan.review_note}
        </p>
      )}
      {workflow.plan?.team_task_id && (
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href={`/tasks/${workflow.plan.team_task_id}`}
            className="inline-flex min-h-11 items-center gap-2 bg-[#2563a8] px-4 text-sm font-bold text-white"
          >
            <CalendarCheck size={16} />조 편성 열기
          </Link>
          <Link
            href="/calendar"
            className="inline-flex min-h-11 items-center border border-slate-300 px-4 text-sm font-bold text-slate-700"
          >
            캘린더 확인
          </Link>
        </div>
      )}
      <p className="mt-5 text-xs text-slate-400">
        수정 제안·버전 기록은{" "}
        <Link
          className="font-semibold text-[#2563a8]"
          href="/community-workspace"
        >
          기존 공동 기획 작업공간
        </Link>
        에서도 확인할 수 있습니다.
      </p>
    </section>
  );
}
