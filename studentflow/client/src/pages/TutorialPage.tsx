/** StudentFlow | 실제 데이터의 현재 상태를 따라 행사 운영 전 과정을 안내한다. */
import {
  Check,
  ChevronRight,
  ClipboardCheck,
  FileUp,
  MessageSquareText,
  Route,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "@/components/MpaLink";
import { Button } from "@/components/primitives";
import { useApp } from "@/contexts/AppContext";
import { api } from "@/lib/api";
import { planningStageLabel, type ProposalListItem } from "@/lib/proposals";
import type { Task, User } from "@/types";

function taskOwner(task: Task | undefined, users: User[]) {
  return task ? users.find(user => user.id === task.assigneeId) : undefined;
}

function Step({
  number,
  title,
  description,
  done,
  active,
  children,
}: {
  number: number;
  title: string;
  description: string;
  done?: boolean;
  active?: boolean;
  children?: ReactNode;
}) {
  return (
    <li className="grid gap-3 border-b border-slate-200 py-5 last:border-b-0 sm:grid-cols-[42px_minmax(0,1fr)_auto] sm:items-start">
      <span
        className={`grid h-8 w-8 place-items-center rounded-full text-sm font-bold ${done ? "bg-[#e8f5ee] text-[#17663d]" : active ? "bg-[#e8f0f8] text-[#1f528b]" : "bg-slate-100 text-slate-500"}`}
      >
        {done ? <Check size={17} aria-label="완료" /> : number}
      </span>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-bold text-slate-900">{title}</h2>
          {done ? (
            <span className="text-xs font-semibold text-[#17663d]">완료</span>
          ) : active ? (
            <span className="text-xs font-semibold text-[#1f528b]">
              현재 단계
            </span>
          ) : null}
        </div>
        <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
      </div>
      {children ? <div>{children}</div> : null}
    </li>
  );
}

export default function TutorialPage() {
  const { currentUser, users, tasks, events, testAccounts, switchTestAccount } =
    useApp();
  const [proposals, setProposals] = useState<ProposalListItem[]>([]);
  useEffect(() => {
    api<ProposalListItem[]>("/proposals")
      .then(setProposals)
      .catch(() => setProposals([]));
  }, []);
  const formationTasks = tasks.filter(task => task.type === "TEAM_FORMATION");
  const formationTask =
    formationTasks.find(
      task => task.assignedToMe && task.title.includes("[기술 시연]")
    ) ??
    formationTasks.find(task => task.assignedToMe) ??
    formationTasks.find(task => task.title.includes("[기술 시연]")) ??
    formationTasks[0];
  const posterTask =
    tasks.find(
      task =>
        task.type === "SUBMISSION" && task.eventId === formationTask?.eventId
    ) ??
    tasks.find(
      task =>
        task.type === "SUBMISSION" &&
        task.assignedToMe &&
        /포스터/.test(task.title)
    ) ??
    tasks.find(task => task.type === "SUBMISSION" && /포스터/.test(task.title));
  const proposal = useMemo(
    () =>
      proposals.find(item => item.title.includes("[기술 시연]")) ??
      proposals.find(
        item => !["SCHEDULED", "REJECTED"].includes(item.planning_stage)
      ) ??
      proposals[0],
    [proposals]
  );
  const formationOwner = taskOwner(formationTask, users),
    posterOwner = taskOwner(posterTask, users);
  const formationDone = formationTask?.status === "DONE",
    posterDone = posterTask?.status === "DONE" || posterTask?.submitted;
  const eventCreated = Boolean(
    formationTask?.eventId ||
      events.some(event => event.id === formationTask?.eventId)
  );
  const proposalPastDiscussion = Boolean(
    proposal && proposal.planning_stage !== "DISCUSSING"
  );
  const proposalPastReview = Boolean(
    proposal &&
      ["APPROVED", "ASSIGNING_TEAMS", "SCHEDULED"].includes(
        proposal.planning_stage
      )
  );
  const completedCount = [
    proposalPastDiscussion,
    proposalPastReview || eventCreated,
    formationDone,
    posterDone,
  ].filter(Boolean).length;
  const finished = Boolean(formationDone && posterDone);
  const currentStage = proposal
    ? planningStageLabel[proposal.planning_stage]
    : formationTask
      ? "행사 실행 준비"
      : "시작할 업무 선택";
  async function enterAs(owner?: User) {
    if (
      owner &&
      owner.id !== currentUser.id &&
      testAccounts.some(account => account.id === owner.id)
    )
      await switchTestAccount(owner.id);
  }
  function taskAction(
    task: Task | undefined,
    owner: User | undefined,
    label: string
  ) {
    if (!task)
      return (
        <Link href="/event-create">
          <Button variant="secondary">
            체험 행사 만들기
            <ChevronRight size={16} />
          </Button>
        </Link>
      );
    const canSwitch =
      owner &&
      owner.id !== currentUser.id &&
      testAccounts.some(account => account.id === owner.id);
    return canSwitch ? (
      <Button variant="secondary" onClick={() => void enterAs(owner)}>
        {owner.name} 계정으로 전환
      </Button>
    ) : (
      <Link href={`/tasks/${task.id}`}>
        <Button>
          {label}
          <ChevronRight size={16} />
        </Button>
      </Link>
    );
  }
  const overview = [
    [MessageSquareText, "제안·의견", proposalPastDiscussion],
    [ClipboardCheck, "회의·기획", proposalPastReview],
    [ShieldCheck, "교사 검토", eventCreated],
    [UsersRound, "조 편성", formationDone],
    [FileUp, "제출·확인", posterDone],
  ] as const;
  return (
    <div className="mx-auto max-w-[900px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="border-b-2 border-slate-800 pb-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-[#1f528b]">
          <Route size={17} /> 실제 업무 체험
        </div>
        <h1 className="mt-2 text-2xl font-bold tracking-[-.03em]">
          행사 운영 흐름 한 바퀴
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          연습용 데이터를 만들지 않습니다. 지금 연결된 제안·행사·업무를 읽어
          전체 흐름과 다음 행동을 함께 보여 줍니다.
        </p>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
          <span>
            현재 계정{" "}
            <strong className="text-slate-700">{currentUser.name}</strong>
          </span>
          <span>
            현재 위치 <strong className="text-slate-700">{currentStage}</strong>
          </span>
          <span>
            실행 진행{" "}
            <strong className="text-slate-700">{completedCount}/4</strong>
          </span>
        </div>
      </header>
      <section
        className="mt-6 border-y border-slate-200 py-4"
        aria-label="운영 흐름 개요"
      >
        <p className="text-xs font-semibold text-slate-500">전체 흐름</p>
        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-5">
          {overview.map(([Icon, label, done]) => (
            <div
              key={label}
              className={`flex items-center gap-2 border-l-2 px-3 py-2 ${done ? "border-[#17663d] text-[#17663d]" : "border-slate-200 text-slate-500"}`}
            >
              <Icon size={16} />
              <span className="font-semibold">{label}</span>
            </div>
          ))}
        </div>
      </section>
      {!formationTask || !posterTask ? (
        <p className="mt-5 border-l-2 border-amber-400 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
          체험에 필요한 조 편성·포스터 업무가 아직 모두 만들어지지 않았습니다.
          담당 선생님 계정에서 포스터가 필요한 행사를 만들면 실제 업무가
          생성됩니다.
        </p>
      ) : null}
      <ol className="border-b border-slate-200">
        <Step
          number={1}
          title="제안과 의견 모으기"
          description={
            proposal
              ? `현재 선택된 제안: ‘${proposal.title}’ · ${planningStageLabel[proposal.planning_stage]}`
              : "제안에서 의견을 모아 회의 안건으로 발전시킵니다."
          }
          done={proposalPastDiscussion}
          active={!proposalPastDiscussion}
        >
          {proposal ? (
            <Link
              href={`/proposals/${proposal.id}`}
              className="inline-flex min-h-10 items-center text-sm font-semibold text-[#1f528b] hover:underline"
            >
              제안 열기
              <ChevronRight size={16} />
            </Link>
          ) : (
            <Link href="/proposals">
              <Button variant="secondary">제안 보기</Button>
            </Link>
          )}
        </Step>
        <Step
          number={2}
          title="기획서 검토와 행사 생성"
          description="회의 내용을 기획서로 정리해 교사 검토를 받고, 승인되면 행사와 담당 업무가 만들어집니다."
          done={proposalPastReview || eventCreated}
          active={
            proposalPastDiscussion && !(proposalPastReview || eventCreated)
          }
        >
          {currentUser.role === "TEACHER" ? (
            <Link href="/event-create">
              <Button variant="secondary">
                행사 만들기
                <ChevronRight size={16} />
              </Button>
            </Link>
          ) : null}
        </Step>
        <Step
          number={3}
          title="참여 학생 조 편성"
          description="담당자는 날짜·인원·역할 기준을 확인하고, 편성 미리보기에서 학생을 옮긴 뒤 실제로 저장합니다."
          done={formationDone}
          active={(proposalPastReview || eventCreated) && !formationDone}
        >
          {taskAction(
            formationTask,
            formationOwner,
            formationDone ? "편성 결과 보기" : "조 편성 시작"
          )}
        </Step>
        <Step
          number={4}
          title="제출물 업로드와 결과 확인"
          description="포스터 담당 계정으로 전환해 파일을 올린 뒤, 조 편성 메뉴와 업무 제출 목록에서 결과를 확인합니다."
          done={posterDone}
          active={formationDone && !posterDone}
        >
          {taskAction(
            posterTask,
            posterOwner,
            posterDone ? "제출 결과 보기" : "포스터 올리기"
          )}
        </Step>
      </ol>
      <section className="mt-7 border-t-2 border-[#2563a8] py-5">
        <div className="flex items-start gap-3">
          {finished ? (
            <Check className="mt-0.5 text-[#17663d]" size={20} />
          ) : (
            <FileUp className="mt-0.5 text-[#2563a8]" size={20} />
          )}
          <div>
            <h2 className="font-bold">
              {finished
                ? "실제 업무 체험을 마쳤습니다"
                : "각 단계는 실제 화면에서 이어집니다"}
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              조 편성 결과는 ‘조 편성’ 메뉴에, 포스터 원본은 해당 업무의 제출
              파일 목록에 남습니다. 업무가 없다면 선생님이 행사 생성부터
              시작하면 됩니다.
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <Link
                href="/teams"
                className="inline-flex items-center gap-1 text-sm font-semibold text-[#1f528b] hover:underline"
              >
                <UsersRound size={16} /> 조 편성 결과 보기
              </Link>
              {posterTask && (
                <Link
                  href={`/tasks/${posterTask.id}`}
                  className="inline-flex items-center gap-1 text-sm font-semibold text-[#1f528b] hover:underline"
                >
                  <FileUp size={16} /> 포스터 제출 확인
                </Link>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
