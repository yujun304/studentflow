/** StudentFlow | 데스크톱 운영 선반과 휴대폰 5탭 하단 바가 같은 길찾기 문법을 사용한다. */
import {
  Archive,
  Bell,
  CalendarDays,
  CheckSquare,
  ClipboardCheck,
  Ellipsis,
  LayoutDashboard,
  Megaphone,
  NotebookPen,
  ListChecks,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { useApp } from "@/contexts/AppContext";
import { roles } from "@/lib/sample-data";
import { Avatar } from "./primitives";

const mainMenu = [
  ["/", "대시보드", LayoutDashboard],
  ["/tasks", "업무", CheckSquare],
  ["/submissions", "제출 및 검토", ClipboardCheck],
  ["/events", "행사", CalendarDays],
  ["/announcements", "공지", Megaphone],
  ["/calendar", "캘린더", CalendarDays],
  ["/teams", "조 편성", UsersRound],
  ["/attendance", "출석", ClipboardCheck],
  ["/minutes", "회의록", NotebookPen],
  ["/operations", "운영 센터", ListChecks],
] as const;

const supportMenu = [
  ["/notifications", "알림", Bell],
  ["/users", "사용자 및 권한", ShieldCheck],
  ["/archives", "기수 아카이브", Archive],
] as const;

const mobileMain = [
  ["/", "홈", LayoutDashboard],
  ["/tasks", "업무", CheckSquare],
  ["/calendar", "일정", CalendarDays],
  ["/notifications", "알림", Bell],
] as const;

const moreMenu = [
  ...mainMenu.filter(([href]) => !["/", "/tasks", "/calendar"].includes(href)),
  ...supportMenu.filter(([href]) => href !== "/notifications"),
];

function isActive(location: string, href: string) {
  return href === "/" ? location === "/" : location.startsWith(href);
}

function NavItem({
  href,
  label,
  Icon,
}: {
  href: string;
  label: string;
  Icon: typeof LayoutDashboard;
}) {
  const [location] = useLocation();
  const active = isActive(location, href);
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 border-l-2 px-3 py-2 text-sm font-medium transition-colors ${
        active
          ? "border-[#2563a8] bg-[#e8f0f8] text-[#1f528b]"
          : "border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      }`}
    >
      <Icon size={17} strokeWidth={active ? 2.3 : 1.9} />
      <span>{label}</span>
    </Link>
  );
}

function BottomLink({
  href,
  label,
  Icon,
  count,
}: {
  href: string;
  label: string;
  Icon: typeof LayoutDashboard;
  count?: number;
}) {
  const [location] = useLocation();
  const active = isActive(location, href);
  return (
    <Link
      href={href}
      className={`relative flex min-h-12 flex-col items-center justify-center gap-1 rounded-md text-[10px] font-semibold ${
        active ? "text-[#2563a8]" : "text-slate-500"
      }`}
      aria-current={active ? "page" : undefined}
    >
      <span className="relative">
        <Icon size={20} strokeWidth={active ? 2.4 : 1.9} />
        {count ? (
          <i className="absolute -right-2 -top-2 grid h-3.5 min-w-3.5 place-items-center rounded-full bg-[#b42318] px-0.5 text-[8px] not-italic text-white">
            {count}
          </i>
        ) : null}
      </span>
      <span>{label}</span>
    </Link>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <img src="/icon.svg" alt="" className={compact ? "h-7 w-7" : "h-8 w-8"} />
      <div>
        <p className="text-base font-bold tracking-[-.02em] text-slate-900">
          StudentFlow
        </p>
        {!compact && (
          <p className="text-[11px] font-semibold tracking-[.08em] text-slate-500">
            학생회 운영실
          </p>
        )}
      </div>
    </div>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { currentUser, currentRole, notices, signOut } = useApp();
  const [moreOpen, setMoreOpen] = useState(false);
  const [location] = useLocation();
  const unread = notices.filter(notice => !notice.read).length;
  const moreActive = moreMenu.some(([href]) => isActive(location, href));

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
    setMoreOpen(false);
  }, [location]);

  useEffect(() => {
    if (!moreOpen) return;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) =>
      event.key === "Escape" && setMoreOpen(false);
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [moreOpen]);

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[268px] border-r border-slate-200 bg-white lg:flex lg:flex-col">
        <div className="flex h-[78px] items-center border-b border-slate-200 px-5">
          <Brand />
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <div className="mb-4 border-l-2 border-[#2563a8] bg-[#f8fbfe] px-3 py-2.5">
            <p className="text-[11px] font-bold tracking-[.1em] text-[#2563a8]">
              현재 운영
            </p>
            <p className="mt-1 text-sm font-bold text-slate-800">
              2026학년도 2학기
            </p>
          </div>
          <p className="px-3 pb-2 text-[11px] font-bold tracking-[.12em] text-slate-400">
            운영 흐름
          </p>
          <nav className="grid gap-0.5">
            {mainMenu.map(([href, label, Icon]) => (
              <NavItem key={href} href={href} label={label} Icon={Icon} />
            ))}
          </nav>
          <div className="my-4 border-t border-slate-200" />
          <p className="px-3 pb-2 text-[11px] font-bold tracking-[.12em] text-slate-400">
            관리
          </p>
          <nav className="grid gap-0.5">
            {supportMenu.map(([href, label, Icon]) => (
              <NavItem key={href} href={href} label={label} Icon={Icon} />
            ))}
          </nav>
        </div>
        <div className="border-t-2 border-[#2563a8] bg-[#fafcff] p-3">
          <div className="flex items-center gap-3 px-2 py-2">
            <Avatar label={currentUser.name} />
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-slate-800">
                {currentUser.name}
              </p>
              <p className="truncate text-xs text-slate-500">
                {roles[currentRole]} · {currentUser.department}
              </p>
            </div>
          </div>
          <button
            onClick={signOut}
            className="mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-xs font-semibold text-slate-500 hover:bg-slate-100"
          >
            로그아웃
          </button>
        </div>
      </aside>

      <header className="sticky top-0 z-20 flex h-[60px] items-center justify-between border-b border-slate-200 bg-white px-4 pt-[env(safe-area-inset-top)] lg:ml-[268px] lg:h-[78px] lg:px-8 lg:pt-0">
        <div className="lg:hidden">
          <Brand compact />
        </div>
        <div className="hidden lg:block">
          <p className="text-xs font-semibold text-slate-500">
            StudentFlow · 학생회 운영
          </p>
          <p className="mt-0.5 text-sm font-bold text-slate-800">
            2026학년도 2학기
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 md:inline">
            {roles[currentRole]}
          </span>
          <Link
            href="/notifications"
            className="relative hidden rounded p-2 text-slate-600 hover:bg-slate-100 lg:block"
            aria-label="알림"
          >
            <Bell size={20} />
            {unread > 0 && (
              <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-[#b42318] px-1 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </Link>
          <Avatar label={currentUser.name} size="sm" />
        </div>
      </header>

      <main className="pb-[calc(6rem+env(safe-area-inset-bottom))] lg:ml-[268px] lg:pb-10">
        {children}
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-30 grid h-[calc(68px+env(safe-area-inset-bottom))] grid-cols-5 border-t border-slate-200 bg-white px-1 pb-[env(safe-area-inset-bottom)] shadow-[0_-4px_18px_rgba(15,23,42,.05)] lg:hidden"
        aria-label="주요 메뉴"
      >
        {mobileMain.map(([href, label, Icon]) => (
          <BottomLink
            key={href}
            href={href}
            label={label}
            Icon={Icon}
            count={href === "/notifications" ? unread : undefined}
          />
        ))}
        <button
          onClick={() => setMoreOpen(true)}
          className={`relative flex min-h-12 flex-col items-center justify-center gap-1 rounded-md text-[10px] font-semibold ${moreActive ? "text-[#2563a8]" : "text-slate-500"}`}
          aria-label="더보기 열기"
          aria-expanded={moreOpen}
        >
          <Ellipsis size={21} strokeWidth={moreActive ? 2.4 : 1.9} />
          <span>더보기</span>
        </button>
      </nav>

      {moreOpen && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/35 lg:hidden"
          onMouseDown={() => setMoreOpen(false)}
        >
          <aside
            className="absolute inset-x-0 bottom-0 max-h-[76vh] overflow-y-auto rounded-t-2xl bg-white pb-[env(safe-area-inset-bottom)] shadow-2xl"
            onMouseDown={event => event.stopPropagation()}
            aria-label="더보기 메뉴"
            role="dialog"
            aria-modal="true"
          >
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-base font-bold text-slate-900">더보기</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  나머지 운영 기능을 선택하세요.
                </p>
              </div>
              <button
                className="rounded p-2 text-slate-600 hover:bg-slate-100"
                onClick={() => setMoreOpen(false)}
                aria-label="더보기 닫기"
              >
                <X size={20} />
              </button>
            </div>
            <nav className="grid grid-cols-3 gap-px bg-slate-100">
              {moreMenu.map(([href, label, Icon]) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMoreOpen(false)}
                  className={`flex min-h-[86px] flex-col items-center justify-center gap-2 bg-white px-2 text-center text-xs font-semibold ${isActive(location, href) ? "text-[#2563a8]" : "text-slate-600"}`}
                >
                  <Icon size={21} />
                  <span>{label}</span>
                </Link>
              ))}
            </nav>
            <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-800">
                  {currentUser.name}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {roles[currentRole]} · {currentUser.department}
                </p>
              </div>
              <button
                onClick={signOut}
                className="min-h-10 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600"
              >
                로그아웃
              </button>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
