/** StudentFlow | 승인된 조 편성과 개인 배정 내용을 확인한다. */
import { Crown, UsersRound } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { Link } from "@/components/MpaLink";

function scheduleLabel(value?: string) {
  if (!value) return "일정 미정";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function TeamsPage() {
  const { teams, currentRole, currentUser, events } = useApp();
  const seesAllManagedTeams = currentRole !== "MEMBER";
  const myTeamCount = teams.filter(team => team.memberIds.includes(currentUser.id)).length;

  return (
    <div className="mx-auto max-w-[1120px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-[-.03em]">조 편성</h1>
        <p className="mt-1 text-sm text-slate-500">{seesAllManagedTeams ? "관리 중인 조와 참여 중인 조를 날짜별로 확인합니다." : "내가 참여하는 조와 역할을 확인합니다."}</p>
        {teams.length > 0 && <div className="mt-4 flex gap-5 border-y border-slate-200 py-3 text-xs text-slate-600"><span>전체 <strong className="text-slate-900">{teams.length}개 조</strong></span><span>내 참여 <strong className="text-[#1f528b]">{myTeamCount}개 조</strong></span></div>}
      </header>

      {teams.length ? (
        <section className="border-y border-slate-200">
          {teams.map(team => {
            const isMine = team.memberIds.includes(currentUser.id);
            const event = events.find(item => item.id === team.eventId);
            return (
            <article key={team.id} className={`border-b border-slate-200 py-5 last:border-b-0 ${isMine ? "border-l-2 border-l-[#2563a8] pl-4" : ""}`}>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div><h2 className="text-base font-bold text-slate-900">{team.name}</h2>{event && <p className="mt-1 text-xs text-slate-500">{event.title} · {event.location}</p>}</div>
                <div className="flex items-center gap-2"><p className="text-sm text-slate-500">{scheduleLabel(team.scheduleAt)}</p>{isMine && <span className="bg-[#e8f0f8] px-2 py-1 text-xs font-bold text-[#1f528b]">내 조</span>}</div>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {team.roleDescription ?? team.purpose}
              </p>
              <p className="mt-3 flex items-center gap-2 text-sm text-slate-700"><Crown size={15} className="text-amber-600" /><b>조장 {team.leader}</b><span className="text-xs text-slate-500">총 {team.members.length}명</span></p>
              <div className="mt-2 flex flex-wrap gap-1.5">{team.members.map(member => <span key={member} className="border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">{member}</span>)}</div>
              {team.taskId && seesAllManagedTeams && <Link href={`/tasks/${team.taskId}`} className="mt-4 inline-flex text-xs font-semibold text-[#1f528b] hover:underline">원본 조 편성 업무 보기</Link>}
            </article>
          );})}
        </section>
      ) : (
        <div className="grid min-h-52 place-items-center border-y border-slate-200 px-5 py-10 text-center">
          <div className="max-w-sm">
            <UsersRound className="mx-auto text-slate-400" size={24} />
            <h2 className="mt-3 text-sm font-bold text-slate-800">아직 저장된 조 편성이 없습니다.</h2>
            <p className="mt-2 text-xs leading-5 text-slate-500">담당자가 조 편성 업무에서 결과를 저장하면 날짜별 운영표가 여기에 표시됩니다.</p>
          </div>
        </div>
      )}
    </div>
  );
}
