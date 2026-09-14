/** StudentFlow | 데스크톱 운영 선반과 휴대폰 5탭 하단 바가 같은 길찾기 문법을 사용한다. */
import {
  Bell,
  CalendarDays,
  CheckSquare,
  ClipboardPlus,
  Ellipsis,
  LayoutDashboard,
  Megaphone,
  MessageCircle,
  Route,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { Link } from "@/components/MpaLink";
import { useApp } from "@/contexts/AppContext";
import { currentDocumentPath } from "@/lib/document-path";
import ThemeToggle from "@/components/ThemeToggle";
import { roles } from "@/lib/sample-data";
import type { User } from "@/types";
import { Avatar } from "./primitives";

const primaryMenu = [
  ["/", "홈", LayoutDashboard],
  ["/tasks", "업무", CheckSquare],
  ["/proposals", "제안·의견", MessageCircle],
  ["/calendar", "일정", CalendarDays],
] as const;

const supportingMenu = [
  ["/tutorial", "체험 안내", Route],
  ["/announcements", "공지", Megaphone],
  ["/notifications", "알림", Bell],
  ["/teams", "조 편성", UsersRound],
  ["/event-create", "행사 제작", ClipboardPlus],
  ["/users", "구성원", ShieldCheck],
] as const;

const mobileMain = [
  ["/", "홈", LayoutDashboard],
  ["/tasks", "업무", CheckSquare],
  ["/proposals", "제안", MessageCircle],
  ["/calendar", "일정", CalendarDays],
] as const;

function isActive(location: string, href: string) {
  return href === "/" ? location === "/" : location.startsWith(href);
}

function accountDescription(user: Pick<User, "department" | "grade" | "role">) {
  return [user.grade, user.department, roles[user.role]].filter(Boolean).join(" · ");
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
  const location = currentDocumentPath();
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
  const location = currentDocumentPath();
  const active = isActive(location, href);
  return (
    <Link
      href={href}
      className={`relative flex min-h-12 flex-col items-center justify-center gap-1 rounded-md text-[11px] font-semibold ${
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
      <p className="text-base font-bold tracking-[-.02em] text-slate-900">
        StudentFlow
      </p>
    </div>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const {
    currentUser,
    currentRole,
    notices,
    signOut,
    testAccounts,
    switchTestAccount,
  } = useApp();
  const [moreOpen, setMoreOpen] = useState(false);
  const [switchingAccount, setSwitchingAccount] = useState(false);
  const location = currentDocumentPath();
  const unread = notices.filter(notice => !notice.read).length;
  const visibleSupportingMenu = supportingMenu.filter(
    ([href]) => !["/event-create", "/users"].includes(href) || currentRole === "TEACHER"
  );
  const moreActive = visibleSupportingMenu.some(([href]) =>
    isActive(location, href)
  );
  const pageLabel =
    [...primaryMenu, ...supportingMenu].find(([href]) =>
      isActive(location, href)
    )?.[1] ?? "StudentFlow";

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

  async function selectTestAccount(userId: string) {
    if (!userId || userId === currentUser.id) return;
    setSwitchingAccount(true);
    try {
      await switchTestAccount(userId);
      toast.success("선택한 계정으로 전환했습니다.");
    } catch {
      toast.error("계정을 전환하지 못했습니다.");
    } finally {
      setSwitchingAccount(false);
    }
  }

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[232px] border-r border-slate-200 bg-slate-50 md:flex md:flex-col">
        <div className="flex h-16 items-center border-b border-slate-200 px-5">
          <Brand />
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <div className="mb-3 px-3 py-1.5">
            <p className="text-xs font-semibold text-slate-500">
              2026학년도 2학기
            </p>
          </div>
          <nav className="grid gap-0.5">
            {primaryMenu.map(([href, label, Icon]) => (
              <NavItem key={href} href={href} label={label} Icon={Icon} />
            ))}
          </nav>
          {visibleSupportingMenu.length > 0 && (
            <nav className="mt-4 grid gap-0.5 border-t border-slate-200 pt-4">
              {visibleSupportingMenu.map(([href, label, Icon]) => (
                <NavItem key={href} href={href} label={label} Icon={Icon} />
              ))}
            </nav>
          )}
        </div>
        <div className="border-t border-slate-200 bg-[#fafcff] p-3">
          <div className="flex items-center gap-3 px-2 py-2">
            <Avatar label={currentUser.name} />
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-slate-800">
                {currentUser.name}
              </p>
              <p className="truncate text-xs text-slate-500">
                {accountDescription(currentUser)}
              </p>
            </div>
          </div>
          {testAccounts.length > 1 && (
            <label className="mt-1 grid gap-1 px-2">
              <span className="text-[11px] font-semibold text-slate-500">
                테스트 계정으로 보기
              </span>
              <select
                aria-label="테스트 계정으로 보기"
                value={currentUser.id}
                disabled={switchingAccount}
                onChange={event => selectTestAccount(event.target.value)}
                className="h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-700 outline-none focus-visible:border-[#2563a8] focus-visible:ring-2 focus-visible:ring-[#2563a8]/15 disabled:cursor-wait disabled:bg-slate-100"
              >
                {testAccounts.map(account => (
                  <option key={account.id} value={account.id}>
                    {account.name} · {accountDescription(account)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button
            onClick={signOut}
            className="mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-xs font-semibold text-slate-500 hover:bg-slate-100"
          >
            로그아웃
          </button>
        </div>
      </aside>

      <header className="sticky top-0 z-20 flex h-[60px] items-center justify-between border-b border-slate-200 bg-white/95 px-4 pt-[env(safe-area-inset-top)] backdrop-blur-sm md:ml-[232px] md:h-16 md:px-6 md:pt-0">
        <div className="md:hidden">
          <Brand compact />
        </div>
        <div className="hidden min-w-0 md:block">
          <p className="truncate text-sm font-semibold text-slate-600">{pageLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link
            href="/notifications"
            className="relative hidden rounded p-2 text-slate-600 hover:bg-slate-100 md:block"
            aria-label="알림"
          >
            <Bell size={20} />
            {unread > 0 && (
              <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-[#b42318] px-1 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </Link>
        </div>
      </header>

      <main className="pb-[calc(6rem+env(safe-area-inset-bottom))] md:ml-[232px] md:pb-10">
        {children}
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-30 grid h-[calc(68px+env(safe-area-inset-bottom))] grid-cols-5 border-t border-slate-200 bg-white px-1 pb-[env(safe-area-inset-bottom)] shadow-[0_-4px_18px_rgba(15,23,42,.05)] md:hidden"
        aria-label="주요 메뉴"
      >
        {mobileMain.map(([href, label, Icon]) => (
          <BottomLink
            key={href}
            href={href}
            label={label}
            Icon={Icon}
          />
        ))}
        <button
          onClick={() => setMoreOpen(true)}
          className={`relative flex min-h-12 flex-col items-center justify-center gap-1 rounded-md text-[11px] font-semibold ${moreActive ? "text-[#2563a8]" : "text-slate-500"}`}
          aria-label="더보기 열기"
          aria-expanded={moreOpen}
        >
          <span className="relative">
            <Ellipsis size={21} strokeWidth={moreActive ? 2.4 : 1.9} />
            {unread > 0 && (
              <i className="absolute -right-2 -top-2 grid h-3.5 min-w-3.5 place-items-center rounded-full bg-[#b42318] px-0.5 text-[8px] not-italic text-white">
                {unread}
              </i>
            )}
          </span>
          <span>더보기</span>
        </button>
      </nav>

      {moreOpen && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/35 md:hidden"
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
              <p className="text-base font-bold text-slate-900">더보기</p>
              <button
                className="grid h-11 w-11 place-items-center rounded text-slate-600 hover:bg-slate-100"
                onClick={() => setMoreOpen(false)}
                aria-label="더보기 닫기"
              >
                <X size={20} />
              </button>
            </div>
            <nav className="divide-y divide-slate-100">
              {visibleSupportingMenu.map(([href, label, Icon]) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMoreOpen(false)}
                  className={`flex min-h-14 items-center gap-3 px-5 text-sm font-semibold ${isActive(location, href) ? "bg-[#f8fbfe] text-[#2563a8]" : "text-slate-600"}`}
                >
                  <Icon size={21} />
                  <span>{label}</span>
                  {href === "/notifications" && unread > 0 && (
                    <span className="ml-auto text-xs font-bold text-[#b42318]">읽지 않음 {unread}</span>
                  )}
                </Link>
              ))}
            </nav>
            {testAccounts.length > 1 && (
              <label className="grid gap-1.5 border-t border-slate-200 px-5 py-4">
                <span className="text-xs font-semibold text-slate-500">
                  테스트 계정으로 보기
                </span>
                <select
                  aria-label="모바일 테스트 계정으로 보기"
                  value={currentUser.id}
                  disabled={switchingAccount}
                  onChange={event => selectTestAccount(event.target.value)}
                  className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-xs text-slate-700 outline-none focus-visible:border-[#2563a8] focus-visible:ring-2 focus-visible:ring-[#2563a8]/15 disabled:cursor-wait disabled:bg-slate-100"
                >
                  {testAccounts.map(account => (
                    <option key={account.id} value={account.id}>
                      {account.name} · {accountDescription(account)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-800">
                  {currentUser.name}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {accountDescription(currentUser)}
                </p>
              </div>
              <button
                onClick={signOut}
                className="min-h-11 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600"
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
