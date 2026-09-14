/** StudentFlow | 학기 운영 보드: 회의 핵심 결정과 첨부 파일을 한 줄에서 찾게 한다 */
import { FileText, Paperclip, Plus } from "lucide-react";
import { useState } from "react";
import { useApp } from "@/contexts/AppContext";
import { AppModal, Button, TextArea, TextInput } from "@/components/primitives";
export default function MinutesPage() {
  const { meetings, currentRole, createMeeting } = useApp();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    date: "2026. 08. 14.",
    summary: "",
    attachment: "",
  });
  const [error, setError] = useState("");
  const canCreate = currentRole !== "MEMBER";
  function save(event: React.FormEvent) {
    event.preventDefault();
    if (form.title.length < 5)
      return setError("회의 제목을 5자 이상 적어 주세요.");
    if (form.summary.length < 15)
      return setError("회의에서 결정한 내용을 15자 이상 적어 주세요.");
    createMeeting(form);
    setOpen(false);
    setForm({ title: "", date: "2026. 08. 14.", summary: "", attachment: "" });
    setError("");
  }
  return (
    <div className="mx-auto max-w-[1050px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-[-.03em]">회의록</h1>
        </div>
        {canCreate && (
          <Button onClick={() => setOpen(true)}>
            <Plus size={17} />
            회의록 작성하기
          </Button>
        )}
      </header>
      <section className="border border-slate-200 bg-white">
        <div className="divide-y divide-slate-100">
          {meetings.map(meeting => (
            <article key={meeting.id} className="px-4 py-5 sm:px-5">
              <div className="flex flex-col justify-between gap-2 sm:flex-row">
                <div>
                  <div className="flex items-center gap-2">
                    <FileText size={18} className="text-[#2563a8]" />
                    <h2 className="font-bold text-slate-800">
                      {meeting.title}
                    </h2>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    {meeting.date} · 작성 {meeting.author}
                  </p>
                </div>
                <span className="text-xs text-slate-500">
                  첨부 {meeting.attachments.length}개
                </span>
              </div>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-700">
                {meeting.summary}
              </p>
              {meeting.attachments.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {meeting.attachments.map(attachment => (
                    <span
                      key={attachment}
                      className="inline-flex items-center gap-1.5 border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600"
                    >
                      <Paperclip size={14} />
                      {attachment}
                    </span>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
      <AppModal
        open={open}
        title="회의록 작성하기"
        description="회의에서 결정된 내용이 다음 업무로 이어질 수 있게 짧고 구체적으로 적어 주세요."
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              취소
            </Button>
            <Button form="meeting-form" type="submit">
              회의록 저장하기
            </Button>
          </>
        }
      >
        <form id="meeting-form" onSubmit={save} className="grid gap-4">
          <TextInput
            label="회의 제목"
            value={form.title}
            onChange={event => setForm({ ...form, title: event.target.value })}
            error={error}
            placeholder="예: 8월 3주차 부장단 회의"
            required
          />
          <TextInput
            label="회의 날짜"
            value={form.date}
            onChange={event => setForm({ ...form, date: event.target.value })}
            required
          />
          <TextArea
            label="결정한 내용"
            value={form.summary}
            onChange={event =>
              setForm({ ...form, summary: event.target.value })
            }
            placeholder="예: 축제 안내팀 인원을 1명 늘리고, 18일까지 지원자를 받기로 했습니다."
            required
          />
          <label className="grid gap-1.5">
            <span className="text-sm font-semibold text-slate-800">
              첨부 파일{" "}
              <span className="font-normal text-slate-500">(선택)</span>
            </span>
            <input
              type="file"
              className="text-sm text-slate-600"
              onChange={event =>
                setForm({
                  ...form,
                  attachment: event.target.files?.[0]?.name ?? "",
                })
              }
            />
          </label>
        </form>
      </AppModal>
    </div>
  );
}
