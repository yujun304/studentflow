/** StudentFlow | 학기 운영 보드: 권한 변경은 결과를 설명하고 한 번 더 확인한 뒤 적용한다 */
import { History, ShieldCheck, UserCog } from "lucide-react";
import { useEffect, useState } from "react";
import { roles } from "@/lib/sample-data";
import { useApp } from "@/contexts/AppContext";
import type { Role, User } from "@/types";
import {
  AppModal,
  Button,
  PermissionState,
  SelectField,
} from "@/components/primitives";
import { api } from "@/lib/api";

type AuditLog = {
  id: string;
  actor_name: string;
  action: string;
  entity_type: string;
  created_at: string;
};

const auditActionLabel: Record<string, string> = {
  ATTENDANCE_UPDATED: "출석 정보를 변경함",
};

export default function UsersPage() {
  const { users, currentRole, changeUserRole } = useApp();
  const [selected, setSelected] = useState<User | null>(null);
  const [newRole, setNewRole] = useState<Role>("MEMBER");
  const [changed, setChanged] = useState("");
  const [changeError, setChangeError] = useState("");
  const [savingRole, setSavingRole] = useState(false);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  useEffect(() => {
    if (currentRole !== "TEACHER") return;
    api<AuditLog[]>("/audit-logs?limit=20")
      .then(setAuditLogs)
      .catch(() => setAuditLogs([]));
  }, [currentRole]);
  if (currentRole !== "TEACHER")
    return (
      <div className="mx-auto max-w-[900px] px-4 py-7 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-2xl font-bold tracking-[-.03em]">사용자 및 권한</h1>
        </header>
        <PermissionState
          title="사용자와 역할은 담당 선생님만 변경할 수 있어요."
          description="역할에 따라 업무 관리, 출석 저장, 공지 게시 권한이 달라집니다."
        />
      </div>
    );
  function open(user: User) {
    setSelected(user);
    setNewRole(user.role);
    setChangeError("");
  }
  async function apply() {
    if (!selected) return;
    setSavingRole(true);
    setChangeError("");
    try {
      await changeUserRole(selected.id, newRole);
      setChanged(`${selected.name}님의 역할을 ${roles[newRole]}으로 바꿨어요.`);
      setSelected(null);
    } catch (error) {
      setChangeError(error instanceof Error ? error.message : "역할을 변경하지 못했습니다.");
    } finally {
      setSavingRole(false);
    }
  }
  return (
    <div className="mx-auto max-w-[1050px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-[-.03em]">사용자 및 권한</h1>
      </header>
      {changed && (
        <p className="mb-4 border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-[#17663d]">
          {changed}
        </p>
      )}
      <section className="border-y border-slate-200">
        <div className="hidden grid-cols-[1.2fr_1fr_1fr_120px] gap-4 border-b border-slate-200 bg-slate-50 px-5 py-3 text-xs font-bold text-slate-500 md:grid">
          <span>이름</span>
          <span>학년</span>
          <span>소속 · 역할</span>
          <span />
        </div>
        <div className="divide-y divide-slate-100">
          {users.map(user => (
            <div
              key={user.id}
              className="grid gap-3 px-4 py-4 md:grid-cols-[1.2fr_1fr_1fr_120px] md:items-center md:gap-4 md:px-5"
            >
              <div>
                <p className="font-bold text-slate-800">{user.name}</p>
                <p className="mt-1 text-xs text-slate-500 md:hidden">
                  {user.grade}
                </p>
              </div>
              <p className="hidden text-sm text-slate-600 md:block">
                {user.grade}
              </p>
              <p className="text-sm text-slate-600">
                {user.department}
                <span className="mx-1.5 text-slate-300">·</span>
                <b className="text-[#1f528b]">{roles[user.role]}</b>
              </p>
              <Button variant="secondary" size="sm" onClick={() => open(user)}>
                <UserCog size={15} />
                역할 변경
              </Button>
            </div>
          ))}
        </div>
      </section>
      <section className="mt-9">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
          <History size={17} className="text-[#2563a8]" />
          <h2 className="font-bold">최근 관리 기록</h2>
        </div>
        {auditLogs.length ? (
          <div className="divide-y divide-slate-100">
            {auditLogs.map(log => (
              <div key={log.id} className="flex flex-col gap-1 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <p className="text-slate-700">
                  <b>{log.actor_name}</b> · {auditActionLabel[log.action] ?? log.action}
                  <span className="ml-2 text-xs text-slate-400">{log.entity_type}</span>
                </p>
                <time className="text-xs text-slate-500">
                  {new Intl.DateTimeFormat("ko-KR", {
                    year: "numeric",
                    month: "numeric",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  }).format(new Date(log.created_at))}
                </time>
              </div>
            ))}
          </div>
        ) : (
          <p className="py-5 text-sm text-slate-500">아직 기록된 관리 변경이 없습니다.</p>
        )}
      </section>
      <AppModal
        open={Boolean(selected)}
        title="사용자 역할 변경"
        description="변경 후에는 새 역할에 맞는 메뉴와 처리 권한이 적용됩니다."
        onClose={() => setSelected(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSelected(null)} disabled={savingRole}>
              취소
            </Button>
            <Button onClick={() => void apply()} disabled={savingRole || newRole === selected?.role}>
              <ShieldCheck size={16} />
              {savingRole ? "변경 중…" : "역할 변경하기"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4">
          {selected && (
            <p className="border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              <b>{selected.name}</b> · {selected.grade || "학년 미정"} · {selected.department}
              {" · "}현재 {roles[selected.role]}
            </p>
          )}
          <SelectField
            label="새 역할"
            value={newRole}
            onChange={event => setNewRole(event.target.value as Role)}
          >
            {(Object.keys(roles) as Role[]).map(role => (
              <option key={role} value={role}>
                {roles[role]}
              </option>
            ))}
          </SelectField>
          {changeError && <p className="text-sm font-semibold text-[#b42318]">{changeError}</p>}
          <p className="text-xs leading-5 text-slate-500">
            예: 담당 선생님은 출석 저장과 사용자 역할 변경을 할 수 있고, 임원은
            본인의 업무와 제출물을 중심으로 사용합니다.
          </p>
        </div>
      </AppModal>
    </div>
  );
}
