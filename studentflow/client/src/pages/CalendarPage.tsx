/** StudentFlow | 학기 운영 보드: 월간 규칙선, 날짜 칩, 문장형 일정으로 한눈에 읽는 캘린더 */
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  List,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "@/components/MpaLink";
import { useApp } from "@/contexts/AppContext";
import { EmptyState, StatusBadge } from "@/components/primitives";
import { api } from "@/lib/api";

type CalendarType = "업무" | "조 일정" | "부장회의" | "공지";
type Filter = "전체" | CalendarType;
type CalendarItem = {
  id: string;
  type: CalendarType;
  dateKey: string;
  title: string;
  meta: string;
  href: string;
};
type ApiCalendarItem = {
  id: string;
  source: string;
  title: string;
  description: string | null;
  starts_at: string;
};

const tone = {
  업무: "bg-amber-50 text-[#895d09]",
  "조 일정": "bg-emerald-50 text-[#17663d]",
  부장회의: "bg-violet-50 text-violet-700",
  공지: "bg-slate-100 text-slate-700",
};
const typeStatus = {
  업무: "해야 할 일",
  "조 일정": "참여 일정",
  부장회의: "회의 일정",
  공지: "모집 중",
} as const;
const weekday = ["일", "월", "화", "수", "목", "금", "토"];
const pad = (value: number) => String(value).padStart(2, "0");
const dateKey = (date: Date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
const formatMonth = (date: Date) =>
  `${date.getFullYear()}년 ${date.getMonth() + 1}월`;

function calendarDays(base: Date) {
  const year = base.getFullYear();
  const month = base.getMonth();
  const startDay = new Date(year, month, 1).getDay();
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(year, month, index - startDay + 1);
    return {
      date,
      key: dateKey(date),
      inCurrentMonth: date.getMonth() === month,
    };
  });
}

function itemForDay(items: CalendarItem[], key: string, filter: Filter) {
  return items.filter(
    item => item.dateKey === key && (filter === "전체" || item.type === filter)
  );
}

export default function CalendarPage() {
  const { currentUser, tasks, announcements, teams } = useApp();
  const [filter, setFilter] = useState<Filter>("전체");
  const [monthOffset, setMonthOffset] = useState(0);
  const [selectedKey, setSelectedKey] = useState(() => dateKey(new Date()));
  const [mobileList, setMobileList] = useState(
    () => window.matchMedia("(max-width: 639px)").matches
  );
  const currentMonth = useMemo(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
  }, [monthOffset]);
  const days = useMemo(() => calendarDays(currentMonth), [currentMonth]);
  const [communityMeetings, setCommunityMeetings] = useState<CalendarItem[]>([]);
  useEffect(() => {
    const start = dateKey(new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1));
    const end = dateKey(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0));
    let cancelled = false;
    api<ApiCalendarItem[]>(`/calendar?start=${start}&end=${end}`, { cache: "no-store" })
      .then(calendarItems => {
        if (cancelled) return;
        setCommunityMeetings(
          calendarItems
            .filter(item => item.source === "COMMUNITY_MEETING")
            .map(item => {
              const startsAt = new Date(item.starts_at);
              return {
                id: item.id,
                type: "부장회의" as const,
                dateKey: dateKey(startsAt),
                title: item.title,
                meta: item.description ?? "회의 시간 미정",
                href: "/community",
              };
            })
        );
      })
      .catch(() => {
        if (!cancelled) setCommunityMeetings([]);
      });
    return () => {
      cancelled = true;
    };
  }, [currentMonth, currentUser.id]);
  const items = useMemo<CalendarItem[]>(
    () => [
      ...tasks
        .filter(task => task.status !== "DONE")
        .map(task => ({
          id: task.id,
          type: "업무" as const,
          dateKey: task.dueDate.slice(0, 10),
          title: task.title,
          meta: `마감 ${task.dueDate.slice(11)} · ${task.department}`,
          href: `/tasks/${task.id}`,
        })),
      ...teams
        .filter(team => team.scheduleAt)
        .map(team => {
          const schedule = new Date(team.scheduleAt as string);
          return {
            id: `team-${team.id}`,
            type: "조 일정" as const,
            dateKey: dateKey(schedule),
            title: team.name,
            meta: `${schedule.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })} · ${team.roleDescription ?? team.purpose}`,
            href: "/teams",
          };
        }),
      ...announcements
        .filter(announcement => announcement.application || announcement.pinned)
        .map(announcement => ({
          id: announcement.id,
          type: "공지" as const,
          dateKey: announcement.id === "a1" ? "2026-08-14" : "2026-08-17",
          title: announcement.title.replace("[중요] ", ""),
          meta: announcement.application
            ? `신청 마감 ${announcement.application.deadline}`
            : `${announcement.target} 대상`,
          href: `/announcements/${announcement.id}`,
        })),
      ...communityMeetings,
    ],
    [tasks, announcements, teams, communityMeetings]
  );
  const currentItems = itemForDay(items, selectedKey, filter);
  const monthItems = items.filter(
    item =>
      item.dateKey.startsWith(
        `${currentMonth.getFullYear()}-${pad(currentMonth.getMonth() + 1)}`
      ) &&
      (filter === "전체" || item.type === filter)
  );
  function moveMonth(direction: number) {
    const now = new Date();
    const next = new Date(
      now.getFullYear(),
      now.getMonth() + monthOffset + direction,
      1
    );
    setMonthOffset(monthOffset + direction);
    setSelectedKey(dateKey(next));
  }
  return (
    <div className="mx-auto max-w-[1240px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-[-.03em]">캘린더</h1>
        </div>
        <div className="flex items-center gap-1 self-start border border-slate-200 bg-white p-1">
          <button
            onClick={() => setMobileList(false)}
            className={`inline-flex items-center gap-1.5 rounded px-3 py-2 text-xs font-bold ${!mobileList ? "bg-[#e8f0f8] text-[#1f528b]" : "text-slate-500 hover:bg-slate-50"}`}
          >
            <CalendarDays size={15} />
            월간
          </button>
          <button
            onClick={() => setMobileList(true)}
            className={`inline-flex items-center gap-1.5 rounded px-3 py-2 text-xs font-bold ${mobileList ? "bg-[#e8f0f8] text-[#1f528b]" : "text-slate-500 hover:bg-slate-50"}`}
          >
            <List size={15} />
            목록
          </button>
        </div>
      </header>
      <div className="flex flex-col justify-between gap-3 border-y border-slate-200 bg-white px-3 py-2.5 sm:flex-row sm:items-center">
        <div className="flex items-center gap-1">
          <button
            onClick={() => moveMonth(-1)}
            className="rounded p-2 text-slate-600 hover:bg-slate-100"
            aria-label="이전 달"
          >
            <ChevronLeft size={19} />
          </button>
          <p className="min-w-32 px-2 text-center text-sm font-bold text-slate-800">
            {formatMonth(currentMonth)}
          </p>
          <button
            onClick={() => moveMonth(1)}
            className="rounded p-2 text-slate-600 hover:bg-slate-100"
            aria-label="다음 달"
          >
            <ChevronRight size={19} />
          </button>
        </div>
        <div className="flex flex-wrap gap-1">
          {(["전체", "업무", "조 일정", "부장회의", "공지"] as const).map(item => (
            <button
              key={item}
              onClick={() => setFilter(item)}
              className={`rounded px-3 py-1.5 text-xs font-bold ${filter === item ? "bg-[#e8f0f8] text-[#1f528b]" : "text-slate-500 hover:bg-slate-100"}`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      {!mobileList ? (
        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
          <section className="overflow-hidden border border-slate-200 bg-white">
            <div className="grid grid-cols-7 border-b border-slate-200 bg-slate-50">
              {weekday.map((day, index) => (
                <div
                  key={day}
                  className={`px-2 py-2 text-center text-xs font-bold ${index === 0 ? "text-[#b42318]" : index === 6 ? "text-[#2563a8]" : "text-slate-500"}`}
                >
                  {day}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {days.map(day => {
                const dayItems = itemForDay(items, day.key, filter);
                const selected = selectedKey === day.key;
                const today = day.key === dateKey(new Date());
                return (
                  <button
                    key={day.key}
                    onClick={() => setSelectedKey(day.key)}
                    className={`min-h-[100px] border-b border-r border-slate-100 p-1.5 text-left outline-none transition hover:bg-[#f8fbfe] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#2563a8] sm:min-h-[116px] sm:p-2 ${!day.inCurrentMonth ? "bg-slate-50/80 text-slate-400" : "bg-white"} ${selected ? "bg-[#f7fbff] shadow-[inset_0_0_0_2px_#2563a8]" : ""}`}
                  >
                    <span
                      className={`grid h-6 w-6 place-items-center rounded-full text-xs font-bold ${today ? "bg-[#2563a8] text-white" : day.inCurrentMonth ? "text-slate-700" : "text-slate-400"}`}
                    >
                      {day.date.getDate()}
                    </span>
                    <div className="mt-1 grid gap-1">
                      {dayItems.slice(0, 2).map(item => (
                        <span
                          key={item.id}
                          className={`hidden truncate rounded px-1.5 py-1 text-[10px] font-bold sm:block ${tone[item.type]}`}
                        >
                          {item.title}
                        </span>
                      ))}
                      {dayItems.length > 0 && (
                        <span className="flex gap-1 sm:hidden">
                          {dayItems.slice(0, 3).map(item => (
                            <i
                              key={item.id}
                              className={`h-1.5 w-1.5 rounded-full ${
                                item.type === "업무"
                                  ? "bg-amber-500"
                                  : item.type === "조 일정"
                                    ? "bg-emerald-600"
                                    : item.type === "부장회의"
                                      ? "bg-violet-600"
                                    : "bg-slate-500"
                              }`}
                            />
                          ))}
                        </span>
                      )}
                      {dayItems.length > 2 && (
                        <span className="hidden text-[10px] font-semibold text-slate-500 sm:block">
                          +{dayItems.length - 2}개 일정
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
          <aside className="border-t-2 border-[#2563a8] bg-white">
            <div className="border-b border-slate-200 px-4 py-3">
              <p className="text-xs font-bold text-[#2563a8]">선택한 날짜</p>
              <h2 className="mt-1 text-base font-bold text-slate-800">
                {selectedKey.slice(5, 7)}월 {Number(selectedKey.slice(8))}일
                일정
              </h2>
            </div>
            <div className="divide-y divide-slate-100">
              {currentItems.length ? (
                currentItems.map(item => (
                  <article key={item.id} className="px-4 py-4">
                    <StatusBadge label={typeStatus[item.type]} />
                    <h3 className="mt-2 text-sm font-bold leading-5 text-slate-800">
                      {item.title}
                    </h3>
                    <p className="mt-1.5 text-xs leading-5 text-slate-500">
                      {item.meta}
                    </p>
                  </article>
                ))
              ) : (
                <div className="px-4 py-10 text-center">
                  <CalendarDays
                    aria-hidden="true"
                    className="mx-auto mb-3 text-slate-400"
                    size={34}
                  />
                  <p className="text-sm font-bold text-slate-700">
                    이 날짜에는 일정이 없어요.
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    다른 날짜를 선택해 보세요.
                  </p>
                </div>
              )}
            </div>
          </aside>
        </div>
      ) : (
        <section className="mt-5 border border-slate-200 bg-white">
          <div className="divide-y divide-slate-100">
            {monthItems.length ? (
              monthItems
                .sort((a, b) => a.dateKey.localeCompare(b.dateKey))
                .map(item => (
                  <Link
                    key={item.id}
                    className="grid w-full grid-cols-[58px_minmax(0,1fr)] gap-3 px-4 py-4 text-left hover:bg-[#f8fbfe] sm:grid-cols-[90px_minmax(0,1fr)]"
                    href={item.href}
                  >
                    <p className="text-xs font-bold text-slate-500">
                      {item.dateKey.slice(5, 7)}월<br />
                      {Number(item.dateKey.slice(8))}일
                    </p>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge label={typeStatus[item.type]} />
                        <h2 className="text-sm font-bold text-slate-800">
                          {item.title}
                        </h2>
                      </div>
                      <p className="mt-1.5 text-sm text-slate-500">
                        {item.meta}
                      </p>
                    </div>
                  </Link>
                ))
            ) : (
              <EmptyState
                title="이 조건에 맞는 일정이 없어요."
                description="다른 일정 종류를 선택해 보세요."
              />
            )}
          </div>
        </section>
      )}
    </div>
  );
}
