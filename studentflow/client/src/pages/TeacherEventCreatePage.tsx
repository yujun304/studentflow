import { CalendarPlus, Plus, Send, Trash2, UsersRound } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useApp } from "@/contexts/AppContext";
import { api, ApiError, jsonBody } from "@/lib/api";
import {
  Button,
  PermissionState,
  SelectField,
  TextArea,
  TextInput,
} from "@/components/primitives";

type TeamRequirementDraft = {
  id: string;
  name: string;
  peopleCount: number;
  roleDescription: string;
};

const dateKey = (offset = 0) => {
  const value = new Date();
  value.setDate(value.getDate() + offset);
  return value.toISOString().slice(0, 10);
};

const dateTimeKey = (offset = 0) => `${dateKey(offset)}T18:00`;

function newRequirement(index: number): TeamRequirementDraft {
  return {
    id: crypto.randomUUID(),
    name: `${index + 1}조`,
    peopleCount: 4,
    roleDescription: "",
  };
}

export default function TeacherEventCreatePage() {
  const { currentRole, users } = useApp();
  const students = useMemo(() => users.filter(user => user.role !== "TEACHER"), [users]);
  const [participantsInitialized, setParticipantsInitialized] = useState(false);
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [eventType, setEventType] = useState<"EVENT" | "CAMPAIGN">("EVENT");
  const [eventDate, setEventDate] = useState(dateKey(14));
  const [startsAt, setStartsAt] = useState("09:00");
  const [endsAt, setEndsAt] = useState("12:00");
  const [location, setLocation] = useState("");
  const [purpose, setPurpose] = useState("");
  const [targetParticipants, setTargetParticipants] = useState("");
  const [schedulePlan, setSchedulePlan] = useState("");
  const [programPlan, setProgramPlan] = useState("");
  const [preparationPlan, setPreparationPlan] = useState("");
  const [safetyPlan, setSafetyPlan] = useState("");
  const [operationDates, setOperationDates] = useState([dateKey(14)]);
  const [requirements, setRequirements] = useState<TeamRequirementDraft[]>([
    newRequirement(0),
    newRequirement(1),
  ]);
  const [teamManagerId, setTeamManagerId] = useState("");
  const [formationDueAt, setFormationDueAt] = useState(dateTimeKey(7));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!students.length || participantsInitialized) return;
    setParticipantIds(students.map(user => user.id));
    setTeamManagerId(students[0].id);
    setParticipantsInitialized(true);
  }, [participantsInitialized, students]);

  if (currentRole !== "TEACHER") {
    return (
      <div className="mx-auto max-w-[900px] px-4 py-7 sm:px-6 lg:px-8">
        <PermissionState
          title="행사 제작은 담당 선생님만 사용할 수 있어요."
          description="학생이 제안하고 공동으로 작성하는 행사 기획 흐름은 제안 메뉴에서 계속 이용할 수 있습니다."
        />
      </div>
    );
  }

  function updateRequirement(id: string, values: Partial<TeamRequirementDraft>) {
    setRequirements(items =>
      items.map(item => (item.id === id ? { ...item, ...values } : item))
    );
  }

  function changeManager(userId: string) {
    setTeamManagerId(userId);
    setParticipantIds(ids => (ids.includes(userId) ? ids : [...ids, userId]));
  }

  function toggleParticipant(userId: string) {
    if (userId === teamManagerId) return;
    setParticipantIds(ids =>
      ids.includes(userId) ? ids.filter(id => id !== userId) : [...ids, userId]
    );
  }

  function updateOperationDate(index: number, value: string) {
    setOperationDates(items => items.map((item, itemIndex) => (itemIndex === index ? value : item)));
    if (index === 0) setEventDate(value);
  }

  function validate() {
    if (!title.trim() || !location.trim()) return "행사명과 장소를 적어 주세요.";
    if (!purpose.trim() || !targetParticipants.trim()) return "행사 목적과 참여 대상을 적어 주세요.";
    if (!schedulePlan.trim() || !programPlan.trim()) return "진행 일정과 세부 프로그램을 적어 주세요.";
    if (!operationDates.length || operationDates.some(value => !value)) return "모든 활동 날짜를 선택해 주세요.";
    if (!operationDates.includes(eventDate)) return "행사 날짜를 활동 날짜에 포함해 주세요.";
    if (!requirements.length || requirements.some(item => !item.name.trim() || !item.roleDescription.trim())) {
      return "모든 조의 이름과 역할을 적어 주세요.";
    }
    if (new Set(requirements.map(item => item.name.trim())).size !== requirements.length) {
      return "조 이름은 서로 다르게 적어 주세요.";
    }
    if (!teamManagerId || !participantIds.length) return "조 편성 담당 학생과 참여 학생을 선택해 주세요.";
    const requiredPeople = requirements.reduce((sum, item) => sum + item.peopleCount, 0);
    if (requiredPeople !== participantIds.length) {
      return `조별 필요 인원 합계(${requiredPeople}명)와 선택 학생 수(${participantIds.length}명)를 같게 맞춰 주세요.`;
    }
    return "";
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = await api<{ event_id: string; task_id: string }>("/events/teacher-create", {
        method: "POST",
        ...jsonBody({
          title: title.trim(),
          type: eventType,
          purpose: purpose.trim(),
          target_participants: targetParticipants.trim(),
          schedule_plan: schedulePlan.trim(),
          program_plan: programPlan.trim(),
          preparation_plan: preparationPlan.trim() || null,
          safety_plan: safetyPlan.trim() || null,
          location: location.trim(),
          event_date: eventDate,
          starts_at: startsAt || null,
          ends_at: endsAt || null,
          operation_dates: Array.from(new Set(operationDates)).sort(),
          team_requirements: requirements.map(item => ({
            name: item.name.trim(),
            people_count: item.peopleCount,
            role_description: item.roleDescription.trim(),
          })),
          team_manager_id: teamManagerId,
          participant_ids: participantIds,
          formation_due_at: formationDueAt ? new Date(formationDueAt).toISOString() : null,
        }),
      });
      window.location.assign(`/tasks/${result.task_id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "행사를 만들지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const peoplePerDay = requirements.reduce((sum, item) => sum + item.peopleCount, 0);

  return (
    <form onSubmit={submit} className="mx-auto max-w-[980px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-7 border-b border-slate-200 pb-5">
        <p className="text-xs font-bold text-[#2563a8]">교사 전용</p>
        <h1 className="mt-1 text-2xl font-bold tracking-[-.03em]">행사 제작</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          계획과 조별 기준을 작성하면 행사와 조 편성 업무가 함께 생성되고 담당 학생에게 바로 전달됩니다.
        </p>
      </header>

      <div className="grid gap-8">
        <section>
          <div className="mb-4 flex items-center gap-2 border-b border-slate-200 pb-3">
            <CalendarPlus size={18} className="text-[#2563a8]" />
            <h2 className="font-bold">1. 행사 기본 정보</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextInput className="sm:col-span-2" label="행사명" required value={title} onChange={event => setTitle(event.target.value)} />
            <SelectField label="행사 유형" value={eventType} onChange={event => setEventType(event.target.value as "EVENT" | "CAMPAIGN")}>
              <option value="EVENT">행사</option>
              <option value="CAMPAIGN">캠페인</option>
            </SelectField>
            <TextInput label="장소" required value={location} onChange={event => setLocation(event.target.value)} />
            <TextInput label="대표 행사 날짜" type="date" required value={eventDate} onChange={event => setEventDate(event.target.value)} />
            <div className="grid grid-cols-2 gap-3">
              <TextInput label="시작" type="time" value={startsAt} onChange={event => setStartsAt(event.target.value)} />
              <TextInput label="종료" type="time" value={endsAt} onChange={event => setEndsAt(event.target.value)} />
            </div>
          </div>
        </section>

        <section>
          <div className="mb-4 border-b border-slate-200 pb-3">
            <h2 className="font-bold">2. 구체적인 계획서</h2>
            <p className="mt-1 text-xs text-slate-500">작성한 내용은 행사 설명과 조 편성 업무에 그대로 전달됩니다.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextArea label="행사 목적" required value={purpose} onChange={event => setPurpose(event.target.value)} />
            <TextArea label="참여 대상" required value={targetParticipants} onChange={event => setTargetParticipants(event.target.value)} />
            <TextArea label="진행 일정" required value={schedulePlan} onChange={event => setSchedulePlan(event.target.value)} />
            <TextArea label="세부 프로그램" required value={programPlan} onChange={event => setProgramPlan(event.target.value)} />
            <TextArea label="예산과 준비물" value={preparationPlan} onChange={event => setPreparationPlan(event.target.value)} />
            <TextArea label="안전 계획" value={safetyPlan} onChange={event => setSafetyPlan(event.target.value)} />
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-start justify-between gap-4 border-b border-slate-200 pb-3">
            <div>
              <h2 className="font-bold">3. 활동 날짜와 조 정보</h2>
              <p className="mt-1 text-xs text-slate-500">하루 기준 {requirements.length}개 조 · 총 {peoplePerDay}자리</p>
            </div>
            <Button type="button" variant="secondary" size="sm" onClick={() => setOperationDates(items => [...items, items.at(-1) ?? eventDate])}>
              <Plus size={15} /> 날짜 추가
            </Button>
          </div>
          <div className="grid gap-2">
            {operationDates.map((value, index) => (
              <div key={`${index}-${value}`} className="flex items-end gap-2">
                <TextInput className="flex-1" label={index === 0 ? "활동 날짜" : undefined} type="date" required value={value} onChange={event => updateOperationDate(index, event.target.value)} />
                {operationDates.length > 1 && (
                  <Button type="button" variant="ghost" aria-label="활동 날짜 삭제" onClick={() => setOperationDates(items => items.filter((_, itemIndex) => itemIndex !== index))}>
                    <Trash2 size={16} />
                  </Button>
                )}
              </div>
            ))}
          </div>
          <div className="mt-5 divide-y divide-slate-200 border-y border-slate-200">
            {requirements.map((item, index) => (
              <div key={item.id} className="grid gap-3 py-4 sm:grid-cols-[1fr_120px_2fr_auto] sm:items-end">
                <TextInput label={index === 0 ? "조 이름" : undefined} required value={item.name} onChange={event => updateRequirement(item.id, { name: event.target.value })} />
                <TextInput label={index === 0 ? "인원" : undefined} type="number" min={1} max={20} required value={item.peopleCount} onChange={event => updateRequirement(item.id, { peopleCount: Number(event.target.value) })} />
                <TextInput label={index === 0 ? "담당 역할" : undefined} required placeholder="예: 정문 안내와 참가자 확인" value={item.roleDescription} onChange={event => updateRequirement(item.id, { roleDescription: event.target.value })} />
                <Button type="button" variant="ghost" aria-label={`${item.name} 삭제`} disabled={requirements.length === 1} onClick={() => setRequirements(items => items.filter(requirement => requirement.id !== item.id))}>
                  <Trash2 size={16} />
                </Button>
              </div>
            ))}
          </div>
          <Button type="button" variant="secondary" size="sm" className="mt-3" onClick={() => setRequirements(items => [...items, newRequirement(items.length)])}>
            <Plus size={15} /> 조 추가
          </Button>
        </section>

        <section>
          <div className="mb-4 flex items-center gap-2 border-b border-slate-200 pb-3">
            <UsersRound size={18} className="text-[#2563a8]" />
            <h2 className="font-bold">4. 담당 학생에게 전달</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField label="조 편성 담당 학생" required value={teamManagerId} onChange={event => changeManager(event.target.value)}>
              <option value="">학생 선택</option>
              {students.map(user => <option key={user.id} value={user.id}>{user.name} · {user.grade || "학년 미정"} · {user.department}</option>)}
            </SelectField>
            <TextInput label="조 편성 마감" type="datetime-local" value={formationDueAt} onChange={event => setFormationDueAt(event.target.value)} />
          </div>
          <div className="mt-5">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-800">조 편성 대상 학생</p>
              <button type="button" className="text-xs font-semibold text-[#2563a8]" onClick={() => setParticipantIds(students.map(user => user.id))}>전체 선택</button>
            </div>
            <div className="mt-2 grid gap-2 border-y border-slate-200 py-3 sm:grid-cols-2 lg:grid-cols-3">
              {students.map(user => (
                <label key={user.id} className="flex min-h-11 items-center gap-3 px-2 text-sm text-slate-700">
                  <input type="checkbox" checked={participantIds.includes(user.id)} disabled={user.id === teamManagerId} onChange={() => toggleParticipant(user.id)} className="h-4 w-4 accent-[#2563a8]" />
                  <span><b>{user.name}</b><span className="ml-1 text-xs text-slate-500">{user.grade} · {user.department}</span></span>
                </label>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-500">{participantIds.length}명 선택 · 담당 학생은 대상에서 제외할 수 없습니다.</p>
          </div>
        </section>
      </div>

      {error && <p role="alert" className="mt-6 border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-[#a12622]">{error}</p>}
      <div className="sticky bottom-[68px] mt-8 flex justify-end border-t border-slate-200 bg-white/95 py-4 backdrop-blur-sm md:bottom-0">
        <Button type="submit" size="lg" disabled={saving || !students.length}>
          <Send size={17} /> {saving ? "행사 생성 중…" : "행사 만들고 조 편성 전달"}
        </Button>
      </div>
    </form>
  );
}
