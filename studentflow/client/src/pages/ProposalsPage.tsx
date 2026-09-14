import { MessageSquareText, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Link } from "@/components/MpaLink";
import { AppModal, Button, EmptyState, ErrorState, LoadingState, TextArea, TextInput } from "@/components/primitives";
import { api, jsonBody } from "@/lib/api";
import { isProposalCompleted, planningStageLabel, type ProposalDetail, type ProposalListItem } from "@/lib/proposals";

type ListFilter = "NEEDS_ME" | "ACTIVE" | "COMPLETED";

function relativeDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric" }).format(new Date(value));
}

export default function ProposalsPage() {
  const [items, setItems] = useState<ProposalListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState({ title: "", description: "", topic: "" });
  const [filter, setFilter] = useState<ListFilter>("NEEDS_ME");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setItems(await api<ProposalListItem[]>("/proposals"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "제안을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);
  const counts = useMemo(() => ({
    NEEDS_ME: items.filter(item => !isProposalCompleted(item) && item.status !== "CONFIRMED" && !item.has_current_user_feedback).length,
    ACTIVE: items.filter(item => !isProposalCompleted(item)).length,
    COMPLETED: items.filter(isProposalCompleted).length,
  }), [items]);
  const shown = useMemo(() => items.filter(item => {
    if (filter === "NEEDS_ME") return !isProposalCompleted(item) && item.status !== "CONFIRMED" && !item.has_current_user_feedback;
    if (filter === "ACTIVE") return !isProposalCompleted(item);
    return isProposalCompleted(item);
  }), [filter, items]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const created = await api<ProposalDetail>("/proposals", {
        method: "POST",
        ...jsonBody({ title: form.title.trim(), description: form.description.trim(), topic: form.topic.trim() || null }),
      });
      if (file) {
        const body = new FormData();
        body.append("upload", file);
        await api(`/proposals/${created.id}/attachments`, { method: "POST", body });
      }
      window.location.href = `/proposals/${created.id}`;
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "제안을 저장하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-[820px] px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
      <header className="mb-7 flex items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="font-bold tracking-[-.03em]">제안·의견</h1>
          <p className="mt-1 text-sm text-slate-500">아이디어를 확인하고 필요한 의견을 남깁니다.</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus size={17} />새 제안</Button>
      </header>

      {loading ? <LoadingState label="제안을 불러오는 중입니다." /> : error ? (
        <ErrorState description={error} onRetry={() => void load()} />
      ) : (
        <>
          <div className="-mx-4 mb-4 flex overflow-x-auto border-b border-slate-200 px-4 sm:mx-0 sm:px-0" role="tablist" aria-label="제안 보기">
            {([['NEEDS_ME', '내 의견 필요'], ['ACTIVE', '진행 중'], ['COMPLETED', '완료']] as const).map(([value, label]) => (
              <button key={value} type="button" role="tab" aria-selected={filter === value} onClick={() => setFilter(value)} className={`min-h-11 shrink-0 border-b-2 px-4 text-sm font-semibold ${filter === value ? "border-[#2563a8] text-[#1f528b]" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
                {label} <span className="ml-1 tabular-nums">{counts[value]}</span>
              </button>
            ))}
          </div>
          {shown.length === 0 ? (
            <EmptyState title={filter === "NEEDS_ME" ? "지금 남길 의견이 없습니다." : filter === "ACTIVE" ? "진행 중인 제안이 없습니다." : "완료된 제안이 없습니다."} description={filter === "NEEDS_ME" ? "다른 제안은 ‘진행 중’에서 확인할 수 있습니다." : filter === "COMPLETED" ? "일정 반영까지 끝나거나 반려된 제안이 여기에 표시됩니다." : "새 아이디어가 있다면 제안을 시작해 보세요."} action={filter === "ACTIVE" ? <Button onClick={() => setOpen(true)}>새 제안 만들기</Button> : undefined} />
          ) : <section className="border-t border-slate-200" aria-label="제안 목록">
          {shown.map(item => (
            <Link key={item.id} href={`/proposals/${item.id}`} className="group block border-b border-slate-200 py-4 hover:bg-slate-50 sm:px-2">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
                    <span>{planningStageLabel[item.planning_stage]} · v{item.current_version}</span>
                    {item.topic && <span>{item.topic}</span>}
                  </div>
                  <h2 className="mt-2 text-[15px] font-bold text-slate-900 group-hover:text-[#1f528b]">{item.title}</h2>
                  <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-600">{item.description}</p>
                  <p className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span className="inline-flex items-center gap-1"><MessageSquareText size={14} />의견 {item.feedback_count}</span>
                    <span>추천 {item.recommendation_count}</span>
                    <span>{relativeDate(item.updated_at)} 업데이트</span>
                  </p>
                </div>
                <span className={`shrink-0 border-l border-slate-200 pl-3 text-xs font-semibold ${item.is_current_user_feedback_required ? "text-[#b54708]" : item.has_current_user_feedback ? "text-slate-500" : "text-[#2563a8]"}`}>
                  {isProposalCompleted(item) ? "완료" : item.is_current_user_feedback_required ? "의견 요청" : item.status === "CONFIRMED" ? "기획 진행 중" : item.has_current_user_feedback ? "의견 남김" : "의견 남기기"}
                </span>
              </div>
            </Link>
          ))}
        </section>}
        </>
      )}

      <AppModal open={open} onClose={() => setOpen(false)} title="새 제안" description="제목과 짧은 설명만으로 시작할 수 있습니다."
        footer={<><Button variant="secondary" onClick={() => setOpen(false)}>취소</Button><Button form="proposal-create" type="submit" disabled={saving}>{saving ? "저장 중…" : "제안 만들기"}</Button></>}>
        <form id="proposal-create" className="grid gap-4" onSubmit={submit}>
          <TextInput label="제목" required maxLength={160} value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} />
          <TextArea label="간단한 설명" required maxLength={5000} value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} />
          <TextInput label="관련 행사 또는 주제 (선택)" maxLength={160} value={form.topic} onChange={event => setForm({ ...form, topic: event.target.value })} />
          <label className="grid gap-1.5 text-sm font-semibold text-slate-800">이미지 또는 파일 (선택)<input className="text-sm font-normal text-slate-600 file:mr-3 file:rounded file:border file:border-slate-300 file:bg-white file:px-3 file:py-2 file:text-xs file:font-semibold" type="file" onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
        </form>
      </AppModal>
    </main>
  );
}
