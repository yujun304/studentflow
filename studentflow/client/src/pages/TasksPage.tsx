/** StudentFlow | 학기 운영 보드: 데스크톱은 드래그 가능한 문서형 칸반, 모바일은 상태 탭 목록 */
import { GripVertical, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "wouter";
import { useApp } from "@/contexts/AppContext";
import type { Task, TaskStatus } from "@/types";
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
  { status: "IN_REVIEW", label: "검토 중" },
  { status: "DONE", label: "완료" },
  { status: "REJECTED", label: "반려" },
];
const labels = Object.fromEntries(
  columns.map(column => [column.status, column.label])
) as Record<TaskStatus, string>;

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
  const { tasks, currentRole, currentUser, createTask, updateTaskStatus } =
    useApp();
  const [status, setStatus] = useState<TaskStatus>("TODO");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<TaskStatus | null>(null);
  const [moveMessage, setMoveMessage] = useState("");
  const [form, setForm] = useState({
    title: "",
    description: "",
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
  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (form.title.trim().length < 4)
      return setError("업무 제목을 4자 이상 적어 주세요.");
    createTask(form);
    setOpen(false);
    setForm({
      title: "",
      description: "",
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
          <p className="text-sm text-slate-500">업무</p>
          <h1 className="mt-1 text-2xl font-bold tracking-[-.03em]">
            해야 할 일을 상태별로 확인하세요
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            행을 열면 요구사항 확인과 제출까지 이어서 할 수 있어요.
          </p>
        </div>
        {canCreate && (
          <Button onClick={() => setOpen(true)}>
            <Plus size={17} />
            업무 만들기
          </Button>
        )}
      </header>
      <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row">
        <div className="max-w-md flex-1">
          <TextInput
            aria-label="업무 검색"
            placeholder="업무 제목으로 찾기"
            value={query}
            onChange={event => setQuery(event.target.value)}
            className="[&>input]:pl-9"
          />
          <Search
            className="pointer-events-none absolute -mt-[31px] ml-3 text-slate-400"
            size={16}
          />
        </div>
        {canMove && (
          <p className="text-xs leading-5 text-slate-500">
            카드를 원하는 상태 칸으로 끌어 놓으면 상태가 바뀝니다.
          </p>
        )}
      </div>
      {moveMessage && (
        <p className="mb-4 border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-[#17663d]">
          {moveMessage}
        </p>
      )}
      <div className="hidden gap-5 xl:grid xl:grid-cols-5">
        {columns.map(column => {
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
          {columns.map(column => (
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
