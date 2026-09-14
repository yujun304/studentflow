/** StudentFlow | 학기 운영 보드: 오늘의 핵심 업무, 클릭 가능한 주간 일정, 조용한 보조 정보 */
import {
  ArrowRight,
  CalendarDays,
  ClipboardCheck,
  FileText,
  Trash2,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "@/components/MpaLink";
import { useApp } from "@/contexts/AppContext";
import { AppModal, Button, StatusBadge } from "@/components/primitives";
import { api, ApiError, jsonBody } from "@/lib/api";

type QuickMemo = {
  id: string;
  content: string;
  created_at: string;
};

const statusLabel = {
  TODO: "해야 할 일",
  IN_PROGRESS: "진행 중",
  DONE: "완료",
} as const;
const dayMeta = [
  { day: "금", date: "14", key: "2026-08-14" },
  { day: "토", date: "15", key: "2026-08-15" },
  { day: "일", date: "16", key: "2026-08-16" },
  { day: "월", date: "17", key: "2026-08-17" },
  { day: "화", date: "18", key: "2026-08-18" },
  { day: "수", date: "19", key: "2026-08-19" },
  { day: "목", date: "20", key: "2026-08-20" },
];
type ScheduleType = "행사" | "업무" | "공지";
type ScheduleItem = {
  id: string;
  dateKey: string;
  type: ScheduleType;
  title: string;
  meta: string;
  href: string;
};
const typeStatus = {
  행사: "진행 행사",
  업무: "해야 할 일",
  공지: "모집 중",
} as const;
const typeTone = {
  행사: "bg-[#2563a8]",
  업무: "bg-amber-500",
  공지: "bg-slate-500",
};

function WeekCalendar({
  items,
  onSelect,
}: {
  items: ScheduleItem[];
  onSelect: (key: string) => void;
}) {
  return (
    <section className="mt-10">
      <div className="flex items-center justify-between gap-4 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2">
          <CalendarDays size={18} className="text-[#2563a8]" />
          <h2 className="font-bold">이번 주</h2>
        </div>
        <Link
          href="/calendar"
          className="shrink-0 text-sm font-semibold text-[#2563a8] hover:underline"
        >
          전체
        </Link>
      </div>
      <div className="grid grid-cols-7 border-b border-slate-200">
        {dayMeta.map((item, index) => {
          const dayItems = items.filter(
            schedule => schedule.dateKey === item.key
          );
          return (
            <button
              key={item.key}
              onClick={() => onSelect(item.key)}
              className={`min-h-[72px] px-2 py-3 text-left hover:bg-[#f8fbfe] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#2563a8] sm:min-h-[84px] sm:px-3 ${index === 0 ? "bg-[#f7fbff]" : ""}`}
              aria-label={`${item.date}일 일정 ${dayItems.length}개 보기`}
            >
              <div className="flex items-baseline justify-between gap-1">
                <span
                  className={`text-xs font-bold ${index === 0 ? "text-[#2563a8]" : "text-slate-500"}`}
                >
                  {item.day}
                </span>
                <span
                  className={`text-lg font-bold ${index === 0 ? "border-b-2 border-[#2563a8] text-slate-900" : "text-slate-700"}`}
                >
                  {item.date}
                </span>
              </div>
              <div className="mt-2 flex items-center gap-1.5">
                {dayItems.slice(0, 3).map(schedule => (
                  <i
                    key={schedule.id}
                    className={`h-1.5 w-1.5 rounded-full ${typeTone[schedule.type]}`}
                  />
                ))}
                {dayItems.length > 0 && (
                  <span className="hidden text-[10px] font-semibold text-slate-500 sm:inline">
                    {dayItems.length}개
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const { currentRole, currentUser, tasks, events, announcements } = useApp();
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [memos, setMemos] = useState<QuickMemo[]>([]);
  const [memoDraft, setMemoDraft] = useState("");
  const [memoBusy, setMemoBusy] = useState(false);
  const [memoLoading, setMemoLoading] = useState(true);
  const [memoError, setMemoError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api<QuickMemo[]>("/memos")
      .then(items => {
        if (!cancelled) setMemos(items);
      })
      .catch(error => {
        if (!cancelled) {
          setMemoError(error instanceof ApiError ? error.message : "메모를 불러오지 못했습니다.");
        }
      })
      .finally(() => {
        if (!cancelled) setMemoLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function addMemo(event: FormEvent) {
    event.preventDefault();
    const content = memoDraft.trim();
    if (!content || memoBusy) return;
    setMemoBusy(true);
    setMemoError("");
    try {
      const created = await api<QuickMemo>("/memos", {
        method: "POST",
        ...jsonBody({ content }),
      });
      setMemos(current => [created, ...current]);
      setMemoDraft("");
    } catch (error) {
      setMemoError(error instanceof ApiError ? error.message : "메모를 저장하지 못했습니다.");
    } finally {
      setMemoBusy(false);
    }
  }

  async function removeMemo(memoId: string) {
    setMemoError("");
    try {
      await api(`/memos/${memoId}`, { method: "DELETE" });
      setMemos(current => current.filter(memo => memo.id !== memoId));
    } catch (error) {
      setMemoError(error instanceof ApiError ? error.message : "메모를 삭제하지 못했습니다.");
    }
  }
  const scopedTasks =
    currentRole === "MEMBER"
      ? tasks.filter(task => task.assigneeId === currentUser.id)
      : currentRole === "DEPARTMENT_HEAD"
        ? tasks.filter(task => task.department === currentUser.department)
        : tasks;
  const urgentTasks = scopedTasks
    .filter(task => ["TODO", "IN_PROGRESS"].includes(task.status))
    .slice(0, 3);
  const scheduleItems = useMemo<ScheduleItem[]>(
    () => [
      ...events
        .filter(event => event.dateKey)
        .map(event => ({
          id: `event-${event.id}`,
          dateKey: event.dateKey!,
          type: "행사" as const,
          title: event.title,
          meta: `${event.time} · ${event.location}`,
          href: `/events/${event.id}`,
        })),
      ...tasks
        .filter(task => task.status !== "DONE")
        .map(task => ({
          id: `task-${task.id}`,
          dateKey: task.dueDate.slice(0, 10),
          type: "업무" as const,
          title: task.title,
          meta: `마감 ${task.dueDate.slice(11)} · ${task.department}`,
          href: `/tasks/${task.id}`,
        })),
      ...announcements
        .filter(announcement => announcement.pinned || announcement.application)
        .map(announcement => ({
          id: `announcement-${announcement.id}`,
          dateKey: announcement.id === "a1" ? "2026-08-14" : "2026-08-17",
          type: "공지" as const,
          title: announcement.title.replace("[중요] ", ""),
          meta: announcement.application
            ? `신청 마감 ${announcement.application.deadline}`
            : `${announcement.target} 대상`,
          href: `/announcements/${announcement.id}`,
        })),
    ],
    [tasks, events, announcements]
  );
  const selectedItems = selectedDate
    ? scheduleItems.filter(item => item.dateKey === selectedDate)
    : [];
  return (
    <div className="mx-auto max-w-[1120px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-9">
        <div>
          <p className="text-sm text-slate-500">
            {new Intl.DateTimeFormat("ko-KR", { dateStyle: "full" }).format(
              new Date()
            )}
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-[-.03em] text-slate-900">
            {currentUser.name}님의 오늘
          </h1>
        </div>
      </header>
      <section className="mb-9" aria-labelledby="quick-memo-title">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
          <FileText size={18} className="text-[#2563a8]" />
          <h2 id="quick-memo-title" className="font-bold">빠른 메모</h2>
        </div>
        <form onSubmit={addMemo} className="flex flex-col gap-2 py-3 sm:flex-row">
          <label htmlFor="quick-memo" className="sr-only">메모 내용</label>
          <input
            id="quick-memo"
            value={memoDraft}
            onChange={event => setMemoDraft(event.target.value)}
            maxLength={2000}
            placeholder="잊지 말아야 할 내용을 적어 두세요."
            className="min-h-10 flex-1 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-[#2563a8] focus:ring-2 focus:ring-[#2563a8]/15"
          />
          <Button type="submit" disabled={!memoDraft.trim() || memoBusy}>
            {memoBusy ? "저장 중" : "메모 추가"}
          </Button>
        </form>
        {memoError && <p role="alert" className="pb-2 text-sm text-[#a12622]">{memoError}</p>}
        {memoLoading ? (
          <p className="py-4 text-sm text-slate-500">메모를 불러오는 중입니다.</p>
        ) : memos.length ? (
          <ul className="divide-y divide-slate-100 border-t border-slate-100">
            {memos.slice(0, 5).map(memo => (
              <li key={memo.id} className="flex items-start gap-3 py-3">
                <p className="min-w-0 flex-1 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">
                  {memo.content}
                </p>
                <button
                  type="button"
                  onClick={() => void removeMemo(memo.id)}
                  className="rounded p-1.5 text-slate-400 hover:bg-slate-100 hover:text-[#a12622] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563a8]"
                  aria-label={`${memo.content.slice(0, 20)} 메모 삭제`}
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="border-t border-slate-100 py-4 text-sm text-slate-500">저장한 메모가 없습니다.</p>
        )}
      </section>
      <section>
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2">
            <ClipboardCheck size={18} className="text-[#2563a8]" />
            <h2 className="font-bold">지금 할 일</h2>
          </div>
          <Link
            href="/tasks"
            className="text-sm font-semibold text-[#2563a8] hover:underline"
          >
            전체
          </Link>
        </div>
        <div className="divide-y divide-slate-100">
          {urgentTasks.length ? (
            urgentTasks.map(task => (
              <Link
                href={`/tasks/${task.id}`}
                key={task.id}
                className="group flex items-center gap-3 py-4 hover:bg-[#f8fbfe]"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-slate-800 group-hover:text-[#1f528b]">
                    {task.title}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {task.dueDate.slice(0, 10)} 마감
                  </p>
                </div>
                <StatusBadge label={statusLabel[task.status]} />
                <ArrowRight
                  size={17}
                  className="hidden text-slate-400 sm:block"
                />
              </Link>
            ))
          ) : (
            <p className="px-4 py-8 text-center text-sm text-slate-500">
              지금 처리할 업무가 없어요.
            </p>
          )}
        </div>
      </section>
      <WeekCalendar items={scheduleItems} onSelect={setSelectedDate} />
      <AppModal
        open={Boolean(selectedDate)}
        title={
          selectedDate
            ? `${selectedDate.slice(5, 7)}월 ${Number(selectedDate.slice(8))}일 일정`
            : "일정"
        }
        description={
          selectedItems.length
            ? `행사·업무·공지 ${selectedItems.length}개가 있어요.`
            : "이 날짜에는 등록된 일정이 없어요."
        }
        onClose={() => setSelectedDate(null)}
        footer={<Button onClick={() => setSelectedDate(null)}>닫기</Button>}
      >
        {selectedItems.length ? (
          <div className="divide-y divide-slate-100">
            {selectedItems.map(item => (
              <Link
                key={item.id}
                href={item.href}
                onClick={() => setSelectedDate(null)}
                className="block py-3 first:pt-0 last:pb-0 hover:bg-[#f8fbfe]"
              >
                <StatusBadge label={typeStatus[item.type]} />
                <h3 className="mt-2 text-sm font-bold leading-5 text-slate-800">
                  {item.title}
                </h3>
                <p className="mt-1.5 text-sm text-slate-500">{item.meta}</p>
                <span className="mt-2 inline-block text-xs font-semibold text-[#2563a8]">
                  상세 보기
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-slate-500">
            다른 날짜를 선택해 보세요.
          </p>
        )}
      </AppModal>
    </div>
  );
}
