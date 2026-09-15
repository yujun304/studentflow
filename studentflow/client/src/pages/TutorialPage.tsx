/** StudentFlow | 신규 계정이 실제 API 상태를 따라 핵심 흐름을 끝까지 체험한다. */
import {
  CalendarDays,
  Check,
  ChevronRight,
  Circle,
  Loader2,
  Route,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "@/components/MpaLink";
import { Button } from "@/components/primitives";
import { useApp } from "@/contexts/AppContext";
import { ApiError, api } from "@/lib/api";

type TutorialStep = {
  key: string;
  title: string;
  description: string;
  href: string;
  action_label: string;
  done: boolean;
};
type TutorialStatus = {
  started: boolean;
  completed: boolean;
  completed_count: number;
  total_count: number;
  steps: TutorialStep[];
};

export default function TutorialPage() {
  const { currentUser, currentRole } = useApp();
  const [status, setStatus] = useState<TutorialStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    return api<TutorialStatus>("/tutorial", { cache: "no-store" })
      .then(setStatus)
      .catch(reason =>
        setError(
          reason instanceof ApiError
            ? reason.message
            : "체험 진행 상태를 불러오지 못했습니다."
        )
      );
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  async function start() {
    setBusy(true);
    setError("");
    try {
      setStatus(
        await api<TutorialStatus>("/tutorial/start", { method: "POST" })
      );
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "체험 환경을 준비하지 못했습니다."
      );
    } finally {
      setBusy(false);
    }
  }
  async function finish() {
    setBusy(true);
    setError("");
    try {
      await api<TutorialStatus>("/tutorial/complete", { method: "POST" });
      window.location.assign("/");
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "튜토리얼을 완료하지 못했습니다."
      );
      setBusy(false);
    }
  }

  const nextStep = status?.steps.find(step => !step.done);
  const allDone = Boolean(
    status?.started && status.completed_count === status.total_count
  );
  const manager = currentRole !== "MEMBER";
  return (
    <div className="mx-auto max-w-[920px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="border-b-2 border-slate-800 pb-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-[#1f528b]">
          <Route size={17} /> 처음 사용하는 분을 위한 실제 기능 체험
        </div>
        <h1 className="mt-2 text-2xl font-bold tracking-[-.03em]">
          {currentUser.name}님의 StudentFlow 시작 안내
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          설명만 읽는 안내가 아닙니다. 이 계정에만 보이는 행사·공지·업무를
          준비하고, 실제 저장 결과를 확인해 다음 단계가 자동으로 열립니다.
        </p>
        {status?.started && (
          <div className="mt-5">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
              <span>핵심 기능 진행률</span>
              <span>
                {status.completed_count}/{status.total_count}
              </span>
            </div>
            <div
              className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"
              aria-label={`진행률 ${status.completed_count}/${status.total_count}`}
            >
              <div
                className="h-full bg-[#2563a8] transition-[width]"
                style={{
                  width: `${(status.completed_count / status.total_count) * 100}%`,
                }}
              />
            </div>
          </div>
        )}
      </header>
      {error && (
        <p className="mt-5 border-l-2 border-[#b42318] bg-red-50 px-4 py-3 text-sm text-[#8f1d18]">
          {error}
        </p>
      )}
      {!status ? (
        <div className="grid min-h-52 place-items-center text-sm text-slate-500">
          <Loader2 className="animate-spin" size={20} />
        </div>
      ) : !status.started ? (
        <section className="py-10">
          <h2 className="text-lg font-bold text-slate-900">
            체험할 내용을 준비할까요?
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            개인 체험 행사 1개, 업무 3개, 선착순 공지 1개를 만듭니다. 다른
            계정의 기존 업무와 제출물은 바꾸지 않으며, 같은 계정에서 다시 눌러도
            중복 생성되지 않습니다.
          </p>
          <Button className="mt-5" onClick={() => void start()} disabled={busy}>
            {busy ? "준비하는 중…" : "실제 기능 체험 시작"}
            {!busy && <ChevronRight size={16} />}
          </Button>
        </section>
      ) : (
        <>
          <ol className="border-b border-slate-200">
            {status.steps.map((step, index) => {
              const active = nextStep?.key === step.key;
              return (
                <li
                  key={step.key}
                  className="grid gap-3 border-b border-slate-200 py-5 last:border-b-0 sm:grid-cols-[42px_minmax(0,1fr)_auto] sm:items-center"
                >
                  <span
                    className={`grid h-8 w-8 place-items-center rounded-full text-sm font-bold ${step.done ? "bg-[#e8f5ee] text-[#17663d]" : active ? "bg-[#e8f0f8] text-[#1f528b]" : "bg-slate-100 text-slate-500"}`}
                  >
                    {step.done ? (
                      <Check size={17} aria-label="완료" />
                    ) : (
                      index + 1
                    )}
                  </span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-bold text-slate-900">{step.title}</h2>
                      <span
                        className={`text-xs font-semibold ${step.done ? "text-[#17663d]" : active ? "text-[#1f528b]" : "text-slate-400"}`}
                      >
                        {step.done ? "완료" : active ? "다음 단계" : "대기"}
                      </span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-600">
                      {step.description}
                    </p>
                  </div>
                  <Link href={step.href}>
                    <Button
                      variant={active ? "primary" : "secondary"}
                      disabled={!active && !step.done}
                    >
                      {step.done ? "결과 보기" : step.action_label}
                      <ChevronRight size={16} />
                    </Button>
                  </Link>
                </li>
              );
            })}
          </ol>
          <section className="mt-7 border-y border-slate-200 py-5">
            <h2 className="text-sm font-bold text-slate-800">저장 결과 확인</h2>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-3 text-sm">
              <Link
                href="/calendar"
                className="inline-flex items-center gap-2 font-semibold text-[#1f528b] hover:underline"
              >
                <CalendarDays size={16} /> 일정에서 체험 행사 보기
              </Link>
              <Link
                href="/teams"
                className="inline-flex items-center gap-2 font-semibold text-[#1f528b] hover:underline"
              >
                <UsersRound size={16} /> 저장된 조 편성 보기
              </Link>
            </div>
          </section>
          {manager && (
            <section className="mt-7 border-l-2 border-slate-300 pl-4">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
                <ShieldCheck size={17} />{" "}
                {currentRole === "TEACHER" ? "교사" : "관리"} 권한 기능
              </div>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                핵심 체험을 마친 뒤 행사 제작, 업무·공지 배정, 알림 전송도 현재
                권한 범위에서 실행할 수 있습니다.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {currentRole === "TEACHER" && (
                  <Link href="/event-create">
                    <Button variant="secondary">행사 제작</Button>
                  </Link>
                )}
                <Link href="/operations">
                  <Button variant="secondary">행사 운영</Button>
                </Link>
                <Link href="/tasks?create=SIMPLE">
                  <Button variant="secondary">업무 만들기</Button>
                </Link>
                <Link href="/announcements">
                  <Button variant="secondary">공지 작성</Button>
                </Link>
                <Link href="/notifications">
                  <Button variant="secondary">알림 보내기</Button>
                </Link>
              </div>
            </section>
          )}
          <section className="mt-8 border-t-2 border-[#2563a8] pt-5">
            <div className="flex items-start gap-3">
              {allDone ? (
                <Check className="mt-0.5 text-[#17663d]" size={21} />
              ) : (
                <Circle className="mt-0.5 text-slate-400" size={21} />
              )}
              <div className="flex-1">
                <h2 className="font-bold text-slate-900">
                  {allDone
                    ? "모든 핵심 기능을 실제로 저장했습니다"
                    : "완료한 뒤 이 화면으로 돌아오세요"}
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  진행률은 화면 방문이 아니라 서버에 남은
                  제안·읽음·신청·업무·조·파일·알림 상태로 계산됩니다.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => void load()}
                    disabled={busy}
                  >
                    진행 상태 새로고침
                  </Button>
                  <Button
                    onClick={() => void finish()}
                    disabled={!allDone || busy}
                  >
                    튜토리얼 마치고 홈으로
                  </Button>
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
