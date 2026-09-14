import { ArrowLeft, Download, FileText, Heart, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Link } from "@/components/MpaLink";
import ProposalWorkflowPanel from "@/components/ProposalWorkflowPanel";
import { AppModal, Button, ErrorState, LoadingState, TextArea, TextInput } from "@/components/primitives";
import { api, jsonBody } from "@/lib/api";
import { categoryLabel, proposalIdFromPath, statusLabel, type FeedbackCategory, type ProposalDetail, type ProposalFeedback, type ProposalSummary } from "@/lib/proposals";

const categories = Object.entries(categoryLabel) as [FeedbackCategory, string][];
const summarySections: Array<[keyof ProposalSummary, string]> = [
  ["strengths", "좋게 평가된 부분"], ["concerns", "주요 우려"], ["changes", "변경 제안"],
  ["new_ideas", "새로운 아이디어"], ["open_questions", "아직 결정되지 않은 쟁점"],
];
const dateTime = (value: string) => new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

export default function ProposalDetailPage() {
  const proposalId = proposalIdFromPath();
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [category, setCategory] = useState<FeedbackCategory | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [editing, setEditing] = useState<ProposalFeedback | null>(null);
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [versionOpen, setVersionOpen] = useState(false);
  const [versionForm, setVersionForm] = useState({ title: "", description: "", topic: "", change_summary: "" });
  const [savingVersion, setSavingVersion] = useState(false);
  const [summarizing, setSummarizing] = useState(false);

  const load = useCallback(async () => {
    if (!proposalId) return setError("제안 주소가 올바르지 않습니다.");
    setLoading(true); setError("");
    try { setProposal(await api<ProposalDetail>(`/proposals/${proposalId}`)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "제안을 불러오지 못했습니다."); }
    finally { setLoading(false); }
  }, [proposalId]);

  useEffect(() => { void load(); }, [load]);
  const currentFeedback = useMemo(() => proposal?.feedback.filter(item => item.version_number === proposal.current_version) ?? [], [proposal]);
  const pastFeedback = useMemo(() => proposal?.feedback.filter(item => item.version_number !== proposal.current_version) ?? [], [proposal]);
  const hasSummaryItems = proposal?.summary ? summarySections.some(([key]) => {
    const values = proposal.summary?.[key];
    return Array.isArray(values) && values.length > 0;
  }) : false;
  async function saveFeedback(event: React.FormEvent) {
    event.preventDefault();
    if (!proposalId || !category || !feedbackText.trim()) return;
    setSavingFeedback(true);
    try {
      const path = editing ? `/proposals/${proposalId}/feedback/${editing.id}` : `/proposals/${proposalId}/feedback`;
      await api(path, { method: editing ? "PATCH" : "POST", headers: editing ? undefined : { "Idempotency-Key": crypto.randomUUID() }, ...jsonBody({ category, content: feedbackText.trim() }) });
      setFeedbackText(""); setCategory(null); setEditing(null);
      await load();
      toast.success(editing ? "의견을 수정했습니다." : "현재 버전에 의견을 남겼습니다.");
    } catch (reason) { toast.error(reason instanceof Error ? reason.message : "의견을 저장하지 못했습니다."); }
    finally { setSavingFeedback(false); }
  }

  function startEdit(item: ProposalFeedback) { setEditing(item); setCategory(item.category); setFeedbackText(item.content); window.scrollTo({ top: 180, behavior: "smooth" }); }
  async function removeFeedback(item: ProposalFeedback) {
    if (!proposalId || !window.confirm("이 의견을 삭제할까요?")) return;
    try { await api(`/proposals/${proposalId}/feedback/${item.id}`, { method: "DELETE" }); await load(); }
    catch (reason) { toast.error(reason instanceof Error ? reason.message : "의견을 삭제하지 못했습니다."); }
  }

  function openVersion() {
    if (!proposal) return;
    setVersionForm({ title: proposal.current.title, description: proposal.current.description, topic: proposal.current.topic ?? "", change_summary: "" });
    setVersionOpen(true);
  }
  async function createVersion(event: React.FormEvent) {
    event.preventDefault(); if (!proposalId || !proposal) return;
    setSavingVersion(true);
    try {
      await api(`/proposals/${proposalId}/versions`, { method: "POST", ...jsonBody({ ...versionForm, topic: versionForm.topic.trim() || null, base_version: proposal.current_version }) });
      setVersionOpen(false); await load(); toast.success("새 버전을 만들고 재검토를 시작했습니다.");
    } catch (reason) { toast.error(reason instanceof Error ? reason.message : "새 버전을 만들지 못했습니다."); }
    finally { setSavingVersion(false); }
  }
  async function summarize() {
    if (!proposalId) return; setSummarizing(true);
    try { const summary = await api<ProposalSummary>(`/proposals/${proposalId}/summary`, { method: "POST" }); setProposal(current => current ? { ...current, summary } : current); }
    catch (reason) { toast.error(reason instanceof Error ? reason.message : "의견을 정리하지 못했습니다."); }
    finally { setSummarizing(false); }
  }
  async function confirm() {
    if (!proposalId || !proposal || !window.confirm("현재 버전을 최종안으로 확정할까요?")) return;
    try { setProposal(await api<ProposalDetail>(`/proposals/${proposalId}/confirm`, { method: "POST", ...jsonBody({ base_version: proposal.current_version }) })); }
    catch (reason) { toast.error(reason instanceof Error ? reason.message : "제안을 확정하지 못했습니다."); }
  }
  async function recommend() {
    if (!proposalId) return;
    try { setProposal(await api<ProposalDetail>(`/proposals/${proposalId}/recommendation`, { method: "PUT" })); }
    catch (reason) { toast.error(reason instanceof Error ? reason.message : "추천을 반영하지 못했습니다."); }
  }
  async function deleteProposal() {
    if (!proposalId || !window.confirm("이 제안을 삭제할까요? 의견과 버전 기록도 함께 삭제됩니다.")) return;
    try {
      await api(`/proposals/${proposalId}`, { method: "DELETE" });
      window.location.assign("/proposals");
    } catch (reason) { toast.error(reason instanceof Error ? reason.message : "제안을 삭제하지 못했습니다."); }
  }

  if (loading) return <main className="mx-auto max-w-[900px] px-4 py-8"><LoadingState /></main>;
  if (error || !proposal) return <main className="mx-auto max-w-[900px] px-4 py-8"><ErrorState description={error} onRetry={() => void load()} /></main>;

  return (
    <main className="mx-auto max-w-[900px] px-4 py-7 sm:px-6 lg:px-8">
      <Link href="/proposals" className="mb-6 inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-900"><ArrowLeft size={16} />제안 목록</Link>
      <header className="border-b border-slate-200 pb-7">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500"><span>{statusLabel[proposal.status]}</span><span>현재 v{proposal.current_version}</span>{proposal.topic && <span>{proposal.topic}</span>}</div>
        <h1 className="mt-3 text-2xl font-bold tracking-[-.03em] text-slate-900">{proposal.current.title}</h1>
        <p className="mt-4 whitespace-pre-wrap text-[15px] leading-7 text-slate-700">{proposal.current.description}</p>
        {proposal.feedback_required && (
          <div className="mt-5 border-l-2 border-[#b54708] bg-[#fffaeb] px-4 py-3 text-sm text-slate-700">
            <p className="font-bold text-[#93370d]">추천 {proposal.required_feedback_recommendation_threshold}개 이상 · 의견 참여 요청</p>
            <p className="mt-1">
              현재 버전 참여 {proposal.completed_required_feedback_count}/{proposal.required_feedback_count}명
              {" · 전원 응답을 기다리지 않고 다음 단계로 진행할 수 있습니다."}
            </p>
          </div>
        )}
        {proposal.current.attachments.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{proposal.current.attachments.map(file => <a key={file.id} href={file.download_path} className="inline-flex items-center gap-1.5 border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700"><Download size={14} />{file.original_name}</a>)}</div>}
        <div className="mt-5 flex flex-wrap gap-2"><Button variant="secondary" onClick={() => void recommend()}><Heart size={16} fill={proposal.recommended_by_me ? "currentColor" : "none"} />추천 {proposal.recommendation_count}</Button>{proposal.can_edit && <Button variant="secondary" onClick={openVersion}><Pencil size={16} />{proposal.status === "CONFIRMED" ? "교사 수정" : "새 버전 만들기"}</Button>}{proposal.can_confirm && proposal.status !== "CONFIRMED" && <Button onClick={() => void confirm()}>최종안 확정</Button>}{proposal.can_delete && <Button variant="danger" onClick={() => void deleteProposal()}><Trash2 size={16} />제안 삭제</Button>}</div>
      </header>

      <section className="border-b border-slate-200 py-5" aria-label="다음 행동">
        <p className="text-xs font-bold text-slate-500">다음 행동</p>
        {proposal.status === "CONFIRMED" ? (
          <p className="mt-1 text-sm font-semibold text-slate-800">확정된 제안입니다. 아래에서 최종 내용과 변경 기록을 확인하세요.</p>
        ) : !proposal.has_current_user_feedback ? (
          <div className="mt-1 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-semibold text-slate-800">이 제안에 대한 내 의견을 아직 남기지 않았습니다.</p>
            <a href="#feedback" className="inline-flex min-h-10 shrink-0 items-center justify-center bg-[#2563a8] px-4 text-sm font-semibold text-white hover:bg-[#1f528b]">의견 남기기</a>
          </div>
        ) : proposal.can_confirm ? (
          <p className="mt-1 text-sm font-semibold text-slate-800">의견을 확인한 뒤 위의 ‘최종안 확정’을 눌러 다음 단계로 진행할 수 있습니다.</p>
        ) : (
          <p className="mt-1 text-sm font-semibold text-slate-800">내 의견을 남겼습니다. 다른 의견과 새 버전을 확인해 주세요.</p>
        )}
      </section>

      <ProposalWorkflowPanel proposalId={proposal.id} />

      {proposal.status !== "CONFIRMED" && <section id="feedback" className="scroll-mt-24 border-b border-slate-200 py-7">
        <h2 className="text-lg font-bold">{proposal.is_current_user_feedback_required ? "의견 참여하기" : "의견 남기기"}</h2><p className="mt-1 text-sm text-slate-500">현재 v{proposal.current_version}에 대한 의견입니다.{proposal.is_current_user_feedback_required ? " 참여를 부탁드리지만 전원 응답이 다음 단계의 조건은 아닙니다." : ""}</p>
        <form className="mt-4" onSubmit={saveFeedback}>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="의견 성격">{categories.map(([value, label]) => <button key={value} type="button" role="radio" aria-checked={category === value} onClick={() => setCategory(value)} className={`min-h-11 border px-2 text-sm font-semibold ${category === value ? "border-[#2563a8] bg-[#e8f0f8] text-[#1f528b]" : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"}`}>{label}</button>)}</div>
          {category && <div className="mt-3"><TextArea aria-label="의견 내용" value={feedbackText} maxLength={1000} onChange={event => setFeedbackText(event.target.value)} placeholder={`${categoryLabel[category]}을 짧게 적어 주세요.`} /><div className="mt-2 flex justify-end gap-2">{editing && <Button type="button" variant="ghost" onClick={() => { setEditing(null); setCategory(null); setFeedbackText(""); }}>수정 취소</Button>}<Button type="submit" disabled={savingFeedback || !feedbackText.trim()}>{savingFeedback ? "저장 중…" : editing ? "의견 수정" : "의견 등록"}</Button></div></div>}
        </form>
      </section>}

      <section className="border-b border-slate-200 py-7">
        <div className="flex items-center justify-between gap-4"><div><h2 className="text-lg font-bold">현재 의견 정리</h2><p className="mt-1 text-xs text-slate-500">LLM이 비슷한 의견을 합쳐 제한된 형식으로 정리합니다. 최종 판단은 사람이 합니다.</p></div><Button variant="ghost" size="sm" onClick={() => void summarize()} disabled={summarizing}><RefreshCw size={15} className={summarizing ? "animate-spin" : ""} />{proposal.summary ? "다시 정리" : "의견 정리"}</Button></div>
        {!proposal.summary ? <p className="mt-5 border-l-2 border-slate-300 pl-4 text-sm text-slate-500">정리된 내용이 없습니다. 원본 의견은 아래에서 언제든 확인할 수 있습니다.</p> : hasSummaryItems ? <div className="mt-5 grid gap-5 sm:grid-cols-2">{summarySections.map(([key, label]) => { const values = proposal.summary?.[key]; if (!Array.isArray(values) || values.length === 0) return null; return <div key={key}><h3 className="text-sm font-bold text-slate-800">{label}</h3><ul className="mt-2 space-y-1.5 text-sm leading-6 text-slate-600">{values.map((value, index) => <li key={`${value}-${index}`} className="flex gap-2"><span aria-hidden="true">·</span><span>{value}</span></li>)}</ul></div>; })}</div> : <p className="mt-5 border-l-2 border-slate-300 pl-4 text-sm text-slate-500">현재 버전에 정리할 의견이 없습니다.</p>}
        {proposal.summary && <p className="mt-5 text-xs text-slate-400">{proposal.summary.provider === "ai" ? "AI로 구조화됨" : "기본 규칙으로 정리됨"} · 원본 의견을 대체하지 않음</p>}
      </section>

      <section className="border-b border-slate-200 py-7"><h2 className="text-lg font-bold">개별 의견 <span className="text-sm font-normal text-slate-500">{currentFeedback.length}</span></h2>
        {currentFeedback.length === 0 ? <p className="mt-4 text-sm text-slate-500">현재 버전에 등록된 의견이 없습니다.</p> : <div className="mt-3 divide-y divide-slate-200">{currentFeedback.map(item => <article key={item.id} className="py-4"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold text-[#2563a8]">{categoryLabel[item.category]}</p><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{item.content}</p><p className="mt-2 text-xs text-slate-400">{item.author_name} · {dateTime(item.created_at)}</p></div>{item.is_mine && <div className="flex"><button aria-label="의견 수정" className="p-2 text-slate-400 hover:text-slate-700" onClick={() => startEdit(item)}><Pencil size={15} /></button><button aria-label="의견 삭제" className="p-2 text-slate-400 hover:text-[#b42318]" onClick={() => void removeFeedback(item)}><Trash2 size={15} /></button></div>}</div></article>)}</div>}
      </section>

      <section className="py-7"><h2 className="text-lg font-bold">이전 버전과 변경 기록</h2><div className="mt-3 divide-y divide-slate-200 border-t border-slate-200">{proposal.versions.map(version => <details key={version.id} className="py-4" open={version.version_number === proposal.current_version}><summary className="flex cursor-pointer list-none items-center justify-between gap-4"><span className="font-semibold text-slate-800">v{version.version_number} · {version.change_summary || "내용 수정"}</span><span className="shrink-0 text-xs text-slate-400">{version.author_name} · {dateTime(version.created_at)}</span></summary><div className="mt-4 border-l-2 border-slate-200 pl-4"><h3 className="text-sm font-bold">{version.title}</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{version.description}</p></div></details>)}</div>
        {pastFeedback.length > 0 && <details className="mt-6"><summary className="cursor-pointer text-sm font-semibold text-slate-600">이전 버전 의견 {pastFeedback.length}개 보기</summary><div className="mt-3 divide-y divide-slate-200">{pastFeedback.map(item => <p key={item.id} className="py-3 text-sm text-slate-600"><span className="mr-2 text-xs font-semibold text-slate-400">v{item.version_number} · {categoryLabel[item.category]}</span>{item.content}</p>)}</div></details>}
      </section>

      <AppModal open={versionOpen} onClose={() => setVersionOpen(false)} title={`v${proposal.current_version + 1} 만들기`} description="현재 제안을 수정하면 새 버전에서 의견 수렴이 다시 시작됩니다." footer={<><Button variant="secondary" onClick={() => setVersionOpen(false)}>취소</Button><Button form="proposal-version" type="submit" disabled={savingVersion}>{savingVersion ? "저장 중…" : "새 버전 저장"}</Button></>}>
        <form id="proposal-version" className="grid gap-4" onSubmit={createVersion}><TextInput label="제목" required value={versionForm.title} onChange={event => setVersionForm({ ...versionForm, title: event.target.value })} /><TextArea label="제안 내용" required value={versionForm.description} onChange={event => setVersionForm({ ...versionForm, description: event.target.value })} /><TextInput label="관련 행사 또는 주제 (선택)" value={versionForm.topic} onChange={event => setVersionForm({ ...versionForm, topic: event.target.value })} /><TextInput label="무엇을 바꿨나요?" required maxLength={500} value={versionForm.change_summary} onChange={event => setVersionForm({ ...versionForm, change_summary: event.target.value })} /></form>
      </AppModal>
    </main>
  );
}
