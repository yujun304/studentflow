import {
  ArrowRight,
  Bell,
  CalendarDays,
  CheckSquare,
  Megaphone,
  MessageSquareText,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "@/components/MpaLink";
import { ErrorState, LoadingState, StatusBadge } from "@/components/primitives";
import { useApp } from "@/contexts/AppContext";
import { api } from "@/lib/api";
import type { ProposalListItem } from "@/lib/proposals";

function SectionTitle({
  icon,
  title,
  href,
}: {
  icon: ReactNode;
  title: string;
  href: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-200 pb-3">
      <div className="flex items-center gap-2 text-slate-800">
        <span className="text-[#2563a8]">{icon}</span>
        <h2 className="text-base font-bold">{title}</h2>
      </div>
      <Link
        href={href}
        className="text-xs font-bold text-[#2563a8] hover:underline"
      >
        전체 보기
      </Link>
    </div>
  );
}

export default function ProposalHomePage() {
  const { currentUser, currentRole, tasks, events, announcements, notices } =
    useApp();
  const [proposals, setProposals] = useState<ProposalListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true);
    setError("");
    try {
      setProposals(await api<ProposalListItem[]>("/proposals"));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "홈을 불러오지 못했습니다."
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);

  const openTasks = useMemo(() => {
    const visible =
      currentRole === "MEMBER"
        ? tasks.filter(
            task => task.assignedToMe || task.assigneeId === currentUser.id
          )
        : currentRole === "DEPARTMENT_HEAD"
          ? tasks.filter(
              task =>
                task.department === currentUser.department || task.assignedToMe
            )
          : tasks;
    return visible.filter(task => task.status !== "DONE").slice(0, 3);
  }, [currentRole, currentUser, tasks]);
  const actionProposals = useMemo(
    () =>
      proposals.filter(
        item =>
          item.status !== "CONFIRMED" &&
          (item.is_current_user_feedback_required ||
            !item.has_current_user_feedback)
      ),
    [proposals]
  );
  const upcomingEvents = useMemo(
    () =>
      [...events]
        .filter(event => event.dateKey && event.status !== "마감")
        .sort((a, b) => (a.dateKey ?? "").localeCompare(b.dateKey ?? ""))
        .slice(0, 2),
    [events]
  );
  const latestAnnouncement = useMemo(
    () =>
      [...announcements].sort((a, b) => Number(b.pinned) - Number(a.pinned))[0],
    [announcements]
  );
  const unreadCount = notices.filter(item => !item.read).length;
  const today = new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());

  if (loading)
    return (
      <main className="mx-auto max-w-[1080px] px-4 py-8">
        <LoadingState />
      </main>
    );
  if (error)
    return (
      <main className="mx-auto max-w-[1080px] px-4 py-8">
        <ErrorState description={error} onRetry={() => void load()} />
      </main>
    );
  const empty = (text: string) => (
    <p className="py-6 text-sm text-slate-500">{text}</p>
  );

  return (
    <main className="mx-auto max-w-[980px] px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
      <header className="flex items-end justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-sm font-medium text-slate-500">{today}</p>
          <h1 className="mt-1 text-2xl font-bold tracking-[-.035em] text-slate-900">
            오늘
          </h1>
        </div>
        <Link
          href="/notifications"
          className="inline-flex items-center gap-2 py-2 text-sm font-semibold text-slate-600 hover:text-[#2563a8]"
        >
          <Bell size={17} /> 알림 {unreadCount}
        </Link>
      </header>

      <div className="mt-8 grid gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,1.45fr)_minmax(260px,.75fr)]">
        <section>
          <SectionTitle
            icon={<CheckSquare size={18} />}
            title="할 업무"
            href="/tasks"
          />
          {openTasks.length ? (
            <div className="divide-y divide-slate-100">
              {openTasks.map(task => (
                <Link
                  key={task.id}
                  href={`/tasks/${task.id}`}
                  className="group flex items-center gap-3 py-4 hover:bg-slate-50 sm:px-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold group-hover:text-[#1f528b]">
                      {task.title}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {task.dueDate === "마감일 없음"
                        ? task.dueDate
                        : `${task.dueDate.slice(0, 10)} 마감`}{" "}
                      · {task.department}
                    </p>
                  </div>
                  <StatusBadge
                    label={
                      task.status === "IN_PROGRESS" ? "진행 중" : "시작 전"
                    }
                  />
                  <ArrowRight size={15} className="shrink-0 text-slate-400" />
                </Link>
              ))}
            </div>
          ) : (
            empty("남아 있는 업무가 없습니다.")
          )}
        </section>

        <section>
          <SectionTitle
            icon={<CalendarDays size={18} />}
            title="다음 일정"
            href="/calendar"
          />
          {upcomingEvents.length ? (
            <div className="divide-y divide-slate-100">
              {upcomingEvents.map(event => (
                <Link
                  key={event.id}
                  href={`/events/${event.id}`}
                  className="group grid grid-cols-[48px_1fr] gap-3 py-4 hover:bg-slate-50"
                >
                  <strong className="border-r border-slate-200 pr-3 text-sm text-[#2563a8]">
                    {event.dateKey?.slice(5, 7)}.{event.dateKey?.slice(8, 10)}
                  </strong>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold group-hover:text-[#1f528b]">
                      {event.title}
                    </p>
                    <p className="mt-1 truncate text-xs text-slate-500">
                      {event.time} · {event.location}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            empty("예정된 행사가 없습니다.")
          )}
        </section>
      </div>

      <section
        className="mt-10 border-t border-slate-200 pt-4"
        aria-label="추가 확인"
      >
        <div className="grid divide-y divide-slate-100 sm:grid-cols-2 sm:divide-x sm:divide-y-0">
          <Link
            href="/proposals"
            className="group flex items-center gap-3 py-3 sm:pr-6"
          >
            <MessageSquareText size={17} className="text-slate-400" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold group-hover:text-[#1f528b]">
                의견이 필요한 제안
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                {actionProposals.length
                  ? `${actionProposals.length}건 확인`
                  : "새 요청 없음"}
              </p>
            </div>
            <ArrowRight size={15} className="text-slate-400" />
          </Link>
          <Link
            href="/announcements"
            className="group flex items-center gap-3 py-3 sm:pl-6"
          >
            <Megaphone size={17} className="text-slate-400" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold group-hover:text-[#1f528b]">
                최근 공지
              </p>
              <p className="mt-0.5 truncate text-xs text-slate-500">
                {latestAnnouncement
                  ? latestAnnouncement.title.replace("[중요] ", "")
                  : "등록된 공지 없음"}
              </p>
            </div>
            <ArrowRight size={15} className="text-slate-400" />
          </Link>
        </div>
      </section>
    </main>
  );
}
