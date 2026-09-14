/** StudentFlow | 학기 운영 보드: 데스크톱은 드래그 가능한 문서형 칸반, 모바일은 상태 탭 목록 */
import { CheckCircle2, GripVertical, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "@/components/MpaLink";
import { useApp } from "@/contexts/AppContext";
import type { Task, TaskStatus, TaskType } from "@/types";
import {
  AppModal,
  Button,
  SelectField,
  TextArea,
  TextInput,
} from "@/components/primitives";

const columns: Array<{ status: TaskStatus; label: string }> = [
  { status: "TODO", label: "해야 할 일" },
  { status: "IN_PROGRESS", label: "진행 중" },
  { status: "DONE", label: "완료" },
];
const labels = Object.fromEntries(
  columns.map(column => [column.status, column.label])
) as Record<TaskStatus, string>;
const typeLabels: Record<TaskType, string> = {
  SIMPLE: "일반 업무",
  SUBMISSION: "파일 제출",
  TEAM_FORMATION: "자동 조 편성",
};

function TaskRow({
  task,
  draggable,
  isDragging,
  onDragStart,
  onDragEnd,
}: {
  task: Task;
  draggable?: boolean;
  isDragging?: boolean;
  onDragStart?: (event: React.DragEvent<HTMLAnchorElement>) => void;
  onDragEnd?: () => void;
}) {
  const overdue =
    task.dueDate.startsWith("2026-08-13") ||
    task.dueDate.startsWith("2026-08-14");
  return (
    <Link
      href={`/tasks/${task.id}`}
      draggable={draggable}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={`group relative block border-b border-slate-200 bg-white px-3.5 py-4 last:border-b-0 hover:bg-[#f8fbfe] ${isDragging ? "opacity-40" : ""} ${draggable ? "cursor-grab active:cursor-grabbing" : ""}`}
    >
      <div className="flex gap-1.5">
        {draggable && (
          <GripVertical
            aria-hidden="true"
            size={16}
            className="mt-0.5 shrink-0 text-slate-300"
          />
        )}
        <p className="text-sm font-semibold leading-5 text-slate-800">
          {task.title}
        </p>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="rounded bg-[#e8f0f8] px-2 py-1 text-[11px] font-semibold text-[#1f528b]">
          {typeLabels[task.type]}
        </span>
        <span
          className={`border-l-2 pl-2 text-xs font-semibold ${overdue && task.status !== "DONE" ? "border-[#b42318] text-[#b42318]" : "border-[#2563a8] text-slate-600"}`}
        >
          {overdue && task.status !== "DONE" ? "마감 임박 · " : "마감 "}
          {task.dueDate.slice(5)}
        </span>
        <span className="text-slate-300">·</span>
        <span className="text-xs text-slate-500">{task.priority} 우선</span>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        {task.department}
        {task.submitted ? " · 제출함" : " · 미제출"}
      </p>
    </Link>
  );
}

export default function TasksPage() {
  const requestedType = new URLSearchParams(window.location.search).get("create");
  const initialType: TaskType =
    requestedType === "TEAM_FORMATION" || requestedType === "SUBMISSION"
      ? requestedType
      : "SIMPLE";
  const { tasks, currentRole, currentUser, createTask, updateTaskStatus } =
    useApp();
  const [status, setStatus] = useState<TaskStatus>("TODO");
  const [query, setQuery] = useState("");
  const [showCompleted, setShowCompleted] = useState(false);
  const [open, setOpen] = useState(requestedType !== null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<TaskStatus | null>(null);
  const [moveMessage, setMoveMessage] = useState("");
  const [form, setForm] = useState({
    title: "",
    description: "",
    type: initialType,
    department: currentUser.department,
    dueDate: "2026-08-22 16:30",
    priority: "보통" as Task["priority"],
  });
  const [error, setError] = useState("");
  const canCreate = currentRole !== "MEMBER";
  const canMove = currentRole !== "MEMBER";
  const shown = useMemo(
    () =>
      tasks.filter(task =>
        task.title.toLowerCase().includes(query.toLowerCase())
      ),
    [tasks, query]
  );
  const completedCount = shown.filter(task => task.status === "DONE").length;
  const visibleColumns = showCompleted
    ? columns
    : columns.filter(column => column.status !== "DONE");
  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (form.title.trim().length < 4)
      return setError("업무 제목을 4자 이상 적어 주세요.");
    createTask(form);
    setOpen(false);
    setForm({
      title: "",
      description: "",
      type: "SIMPLE",
      department: currentUser.department,
      dueDate: "2026-08-22 16:30",
      priority: "보통",
    });
    setError("");
  }
  function startDrag(
    event: React.DragEvent<HTMLAnchorElement>,
    taskId: string
  ) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", taskId);
    setDraggedId(taskId);
    setMoveMessage("");
  }
  function dropOnColumn(targetStatus: TaskStatus) {
    if (!draggedId) return;
    const task = tasks.find(item => item.id === draggedId);
    if (task && task.status !== targetStatus) {
      updateTaskStatus(draggedId, targetStatus);
      setMoveMessage(
        `‘${task.title}’ 업무를 ${labels[targetStatus]} 상태로 옮겼어요.`
      );
    }
    setDraggedId(null);
    setDragOver(null);
  }
  return (
    <div className="mx-auto max-w-[1440px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-[-.03em]">업무</h1>
        </div>
        {canCreate && (
          <Button onClick={() => setOpen(true)}>
            <Plus size={17} />
            업무 만들기
          </Button>
        )}
      </header>
      <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div className="max-w-md flex-1">
          <TextInput
            aria-label="업무 검색"
            placeholder="업무 검색"
            value={query}
            onChange={event => setQuery(event.target.value)}
            className="[&>input]:pl-9"
          />
          <Search
            className="pointer-events-none absolute -mt-[31px] ml-3 text-slate-400"
            size={16}
          />
        </div>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setShowCompleted(value => !value);
            if (status === "DONE") setStatus("TODO");
          }}
          aria-expanded={showCompleted}
          className="justify-start text-slate-500 md:justify-center"
        >
          <CheckCircle2 size={16} />
          {showCompleted ? "완료 업무 숨기기" : `완료 업무 ${completedCount}건 보기`}
        </Button>
      </div>
      {moveMessage && (
        <p className="mb-4 border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-[#17663d]">
          {moveMessage}
        </p>
      )}
      <div className={`hidden gap-5 xl:grid ${showCompleted ? "xl:grid-cols-3" : "xl:grid-cols-2"}`}>
        {visibleColumns.map(column => {
          const items = shown.filter(task => task.status === column.status);
          const activeDrop = dragOver === column.status;
          return (
            <section
              key={column.status}
              onDragOver={event => {
                if (canMove) {
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                  setDragOver(column.status);
                }
              }}
              onDragLeave={() => setDragOver(null)}
              onDrop={() => dropOnColumn(column.status)}
              className={`min-w-0 transition-colors ${activeDrop ? "bg-[#f3f8fd]" : ""}`}
            >
              <header
                className={`flex items-center justify-between border-b-2 px-1 py-2 ${activeDrop ? "border-[#2563a8]" : "border-slate-700"}`}
              >
                <h2 className="text-sm font-bold text-slate-700">
                  {column.label}
                </h2>
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-500">
                  {items.length}
                </span>
              </header>
              <div className="min-h-20 border-b border-slate-200 bg-white">
                {items.length ? (
                  items.map(task => (
                    <TaskRow
                      key={task.id}
                      task={task}
                      draggable={canMove}
                      isDragging={draggedId === task.id}
                      onDragStart={event => startDrag(event, task.id)}
                      onDragEnd={() => {
                        setDraggedId(null);
                        setDragOver(null);
                      }}
                    />
                  ))
                ) : (
                  <p className="px-3 py-8 text-center text-xs text-slate-500">
                    여기에 놓을 업무가 없어요.
                  </p>
                )}
              </div>
            </section>
          );
        })}
      </div>
      <div className="xl:hidden">
        <div className="-mx-4 flex snap-x scroll-px-4 overflow-x-auto border-y border-slate-200 bg-white px-4 sm:mx-0 sm:px-0">
          {visibleColumns.map(column => (
            <button
              key={column.status}
              onClick={() => setStatus(column.status)}
              aria-pressed={status === column.status}
              className={`flex min-h-12 shrink-0 snap-start items-center gap-2 border-b-2 px-4 py-3 text-sm font-bold ${status === column.status ? "border-[#2563a8] text-[#2563a8]" : "border-transparent text-slate-500"}`}
            >
              {column.label}
              <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                {shown.filter(task => task.status === column.status).length}
              </span>
            </button>
          ))}
        </div>
        <section className="mt-4 border-t-2 border-slate-700 bg-white">
          <div className="divide-y divide-slate-100">
            {shown.filter(task => task.status === status).length ? (
              shown
                .filter(task => task.status === status)
                .map(task => <TaskRow task={task} key={task.id} />)
            ) : (
              <p className="px-3 py-12 text-center text-sm text-slate-500">
                이 상태의 업무가 없어요.
              </p>
            )}
          </div>
        </section>
      </div>
      <AppModal
        open={open}
        title="업무 만들기"
        description="작성 후에는 담당자에게 바로 해야 할 일로 보입니다."
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              취소
            </Button>
            <Button form="create-task" type="submit">
              업무 만들기
            </Button>
          </>
        }
      >
        <form id="create-task" onSubmit={submit} className="grid gap-4">
          <TextInput
            label="업무 제목"
            value={form.title}
            onChange={event => setForm({ ...form, title: event.target.value })}
            error={error}
            required
            placeholder="예: 축제 무대 순서 최종 확인"
          />
          <SelectField
            label="업무 카테고리"
            value={form.type}
            onChange={event =>
              setForm({ ...form, type: event.target.value as TaskType })
            }
            required
          >
            <option value="SIMPLE">일반 업무 — 끝나면 완료 처리</option>
            <option value="SUBMISSION">파일 제출 — 올리면 바로 완료</option>
            <option value="TEAM_FORMATION">자동 조 편성 — 편성 후 바로 저장</option>
          </SelectField>
          {form.type === "TEAM_FORMATION" && (
            <p className="-mt-2 border-l-2 border-[#2563a8] pl-3 text-xs leading-5 text-slate-600">
              만든 업무를 열면 참여 인원과 조 개수를 골라 자동 편성할 수 있어요.
            </p>
          )}
          <TextArea
            label="업무 설명"
            value={form.description}
            onChange={event =>
              setForm({ ...form, description: event.target.value })
            }
            hint="담당자가 알아야 할 기준이나 제출물을 적어 주세요."
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextInput
              label="마감"
              value={form.dueDate}
              onChange={event =>
                setForm({ ...form, dueDate: event.target.value })
              }
              required
            />
            <SelectField
              label="우선순위"
              value={form.priority}
              onChange={event =>
                setForm({
                  ...form,
                  priority: event.target.value as Task["priority"],
                })
              }
            >
              <option>높음</option>
              <option>보통</option>
              <option>낮음</option>
            </SelectField>
          </div>
        </form>
      </AppModal>
    </div>
  );
}
