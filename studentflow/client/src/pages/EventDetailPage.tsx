import { ArrowLeft, CalendarDays, MapPin, Pencil, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "@/components/MpaLink";
import { AppModal, Button, StatusBadge, TextArea, TextInput } from "@/components/primitives";
import { useApp } from "@/contexts/AppContext";
import { documentPathId } from "@/lib/document-path";
import { ApiError } from "@/lib/api";

export default function EventDetailPage() {
  const eventId = documentPathId("/events");
  const { events, currentUser, toggleEventJoin, updateEvent, deleteEvent } = useApp();
  const event = events.find(item => item.id === eventId)!;
  const [editOpen, setEditOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "", description: "", location: "", eventDate: "", startsAt: "", endsAt: "",
  });

  if (!event) return <div className="p-8">행사를 찾을 수 없어요.</div>;
  const joined = event.participants.includes(currentUser.name);

  function openEdit() {
    const [startsAt = "", endsAt = ""] =
      event.time === "시간 미정" ? [] : event.time.split(" - ");
    setForm({
      title: event.title,
      description: event.description,
      location: event.location === "장소 미정" ? "" : event.location,
      eventDate: event.dateKey ?? "",
      startsAt,
      endsAt,
    });
    setError("");
    setEditOpen(true);
  }

  async function saveEdit() {
    if (!form.title.trim() || !form.eventDate) {
      setError("행사 이름과 날짜를 입력해 주세요.");
      return;
    }
    setSaving(true);
    try {
      await updateEvent(event.id, form);
      setEditOpen(false);
    } catch {
      setError("행사를 수정하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function removeEvent() {
    if (!window.confirm(`“${event.title}” 행사를 삭제할까요? 연결된 미완료 업무도 종료됩니다.`))
      return;
    setSaving(true);
    try {
      await deleteEvent(event.id);
      window.location.href = "/community";
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "행사를 삭제하지 못했습니다.");
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-[920px] px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-3">
        <Link href="/community" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-[#2563a8]">
          <ArrowLeft size={17} />행사 제안
        </Link>
        {event.canManage && (
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={openEdit}><Pencil size={14} />행사 수정</Button>
            <Button size="sm" variant="danger" disabled={saving} onClick={() => void removeEvent()}><Trash2 size={14} />행사 삭제</Button>
          </div>
        )}
      </div>
      <header className="mt-5 border-b border-slate-200 pb-6">
        <StatusBadge label={event.status} />
        <h1 className="mt-3 text-2xl font-bold tracking-[-.03em] text-slate-900">{event.title}</h1>
        <div className="mt-4 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
          <p className="flex items-center gap-2"><CalendarDays size={16} className="text-[#2563a8]" />{event.date} · {event.time}</p>
          <p className="flex items-center gap-2"><MapPin size={16} className="text-[#2563a8]" />{event.location}</p>
        </div>
      </header>
      <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section className="bg-white">
          <div className="border-b border-slate-200 px-4 py-3"><h2 className="font-bold">행사 안내</h2></div>
          <div className="p-4">
            <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{event.description}</p>
            <div className="mt-5 border-t border-slate-200 pt-4">
              <p className="text-xs font-bold text-slate-500">담당</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">{event.owner}</p>
            </div>
          </div>
        </section>
        <aside className="border-t-2 border-[#2563a8] bg-white">
          <div className="border-b border-slate-200 px-4 py-3"><h2 className="font-bold">참석 현황</h2></div>
          <div className="p-4">
            <div className="flex items-center gap-2"><Users size={18} className="text-[#2563a8]" /><p className="text-sm font-bold text-slate-800">{event.participants.length}명 참여</p></div>
            <p className="mt-2 text-sm leading-6 text-slate-500">{joined ? "참석 명단에 포함되어 있어요." : "참석하려면 아래 버튼을 눌러 주세요."}</p>
            <Button onClick={() => toggleEventJoin(event.id)} className="mt-4 w-full">{joined ? "신청 취소하기" : "참석 신청하기"}</Button>
            <div className="mt-5 border-t border-slate-200 pt-4">
              <p className="text-xs font-bold text-slate-500">신청한 사람</p>
              <div className="mt-2 flex flex-wrap gap-1.5">{event.participants.map(name => <span key={name} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{name}</span>)}</div>
            </div>
          </div>
        </aside>
      </div>
      <AppModal
        open={editOpen}
        title="행사 수정"
        description="담당 선생님은 등록된 모든 행사의 기본 정보를 수정할 수 있습니다."
        onClose={() => setEditOpen(false)}
        footer={<><Button variant="secondary" onClick={() => setEditOpen(false)}>취소</Button><Button disabled={saving} onClick={() => void saveEdit()}>{saving ? "저장 중…" : "행사 수정 저장"}</Button></>}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput className="sm:col-span-2" label="행사 이름" required value={form.title} onChange={e => setForm(current => ({ ...current, title: e.target.value }))} />
          <TextArea className="sm:col-span-2" label="행사 설명" rows={4} value={form.description} onChange={e => setForm(current => ({ ...current, description: e.target.value }))} />
          <TextInput className="sm:col-span-2" label="장소" value={form.location} onChange={e => setForm(current => ({ ...current, location: e.target.value }))} />
          <TextInput className="sm:col-span-2" label="행사 날짜" type="date" required value={form.eventDate} onChange={e => setForm(current => ({ ...current, eventDate: e.target.value }))} />
          <TextInput label="시작 시간" type="time" value={form.startsAt} onChange={e => setForm(current => ({ ...current, startsAt: e.target.value }))} />
          <TextInput label="종료 시간" type="time" value={form.endsAt} onChange={e => setForm(current => ({ ...current, endsAt: e.target.value }))} />
          {error && <p className="sm:col-span-2 text-sm text-[#a12622]">{error}</p>}
        </div>
      </AppModal>
    </div>
  );
}
