/** StudentFlow | 인앱 알림 확인, 브라우저 푸시 설정, 권한 범위 내 알림 전송을 한 화면에서 처리한다. */
import { Bell, BellOff, BellRing, CheckCheck, ChevronRight, Plus, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "@/components/MpaLink";
import { useApp } from "@/contexts/AppContext";
import { disablePush, enablePush, getPushState, type PushState } from "@/lib/push";
import { AppModal, Button, EmptyState, SaveMessage, SelectField, TextArea, TextInput } from "@/components/primitives";

const pushCopy: Record<PushState, { title: string; description: string }> = {
  loading: { title: "푸시 알림 확인 중", description: "이 기기의 알림 설정을 확인하고 있어요." },
  unsupported: { title: "이 브라우저에서는 푸시를 지원하지 않아요", description: "설치한 PWA나 최신 브라우저에서 다시 시도해 주세요." },
  unconfigured: { title: "푸시 서버 설정이 필요해요", description: "관리자가 VAPID 키를 설정하면 이 기기에서 알림을 받을 수 있어요." },
  denied: { title: "브라우저 알림이 차단되어 있어요", description: "브라우저 사이트 설정에서 알림 권한을 허용해 주세요." },
  available: { title: "이 기기에서 푸시 알림 받기", description: "새 업무와 공지가 생기면 앱을 열지 않아도 알려드려요." },
  enabled: { title: "이 기기에서 푸시 알림을 받고 있어요", description: "새 업무와 중요 공지를 바로 알려드려요." },
};

export default function NotificationsPage() {
  const {
    notices,
    users,
    currentRole,
    currentUser,
    markNoticeRead,
    markAllNoticesRead,
    sendNotification,
  } = useApp();
  const unread = notices.filter(notice => !notice.read);
  const [pushState, setPushState] = useState<PushState>("loading");
  const [pushBusy, setPushBusy] = useState(false);
  const [pushError, setPushError] = useState("");
  const [composeOpen, setComposeOpen] = useState(false);
  const [recipient, setRecipient] = useState("all");
  const [form, setForm] = useState({ title: "", content: "" });
  const [formError, setFormError] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const canSend = currentRole !== "MEMBER";
  const recipients = useMemo(
    () => currentRole === "DEPARTMENT_HEAD" ? users.filter(user => user.department === currentUser.department) : users,
    [currentRole, currentUser.department, users],
  );

  useEffect(() => {
    getPushState().then(setPushState).catch(error => {
      setPushState("unconfigured");
      setPushError(error instanceof Error ? error.message : "푸시 설정을 확인하지 못했습니다.");
    });
  }, []);

  async function togglePush() {
    setPushBusy(true);
    setPushError("");
    try {
      if (pushState === "enabled") await disablePush();
      else await enablePush();
      setPushState(await getPushState());
    } catch (error) {
      setPushError(error instanceof Error ? error.message : "푸시 알림 설정을 변경하지 못했습니다.");
      setPushState(await getPushState().catch(() => pushState));
    } finally {
      setPushBusy(false);
    }
  }

  async function submitNotification(event: React.FormEvent) {
    event.preventDefault();
    if (form.title.trim().length < 2) return setFormError("알림 제목을 2자 이상 적어 주세요.");
    const recipientIds = recipient === "all" ? recipients.map(user => user.id) : [recipient];
    if (!recipientIds.length) return setFormError("알림을 받을 사용자가 없습니다.");
    setSending(true);
    setFormError("");
    try {
      await sendNotification({ title: form.title.trim(), content: form.content.trim(), recipientIds });
      setComposeOpen(false);
      setForm({ title: "", content: "" });
      setRecipient("all");
      setSent(true);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "알림을 보내지 못했습니다.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-[900px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-[-.03em]">알림</h1>
          {unread.length > 0 && <p className="mt-1 text-sm font-semibold text-[#2563a8]">읽지 않음 {unread.length}</p>}
        </div>
        {canSend && <Button className="w-full sm:w-auto" onClick={() => { setSent(false); setComposeOpen(true); }}><Plus size={17} />알림 보내기</Button>}
      </header>

      {sent && <SaveMessage>알림을 저장하고 수신자의 등록된 기기로 전송했습니다.</SaveMessage>}

      <section className="mt-4 border-y border-slate-200 py-4 sm:flex sm:items-center sm:justify-between sm:gap-5">
        <div className="flex gap-3">
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${pushState === "enabled" ? "bg-[#e8f0f8] text-[#2563a8]" : "bg-slate-100 text-slate-500"}`}>
            {pushState === "enabled" ? <BellRing size={19} /> : pushState === "denied" || pushState === "unsupported" ? <BellOff size={19} /> : <Bell size={19} />}
          </span>
          <div>
            <h2 className="text-sm font-bold text-slate-800">{pushCopy[pushState].title}</h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">{pushCopy[pushState].description}</p>
            {pushError && <p className="mt-1 text-xs font-semibold text-[#b42318]">{pushError}</p>}
          </div>
        </div>
        {(pushState === "available" || pushState === "enabled") && (
          <Button className="mt-4 w-full sm:mt-0 sm:w-auto" variant={pushState === "enabled" ? "secondary" : "primary"} onClick={togglePush} disabled={pushBusy}>
            {pushBusy ? "변경 중…" : pushState === "enabled" ? "이 기기에서 끄기" : "푸시 알림 켜기"}
          </Button>
        )}
      </section>

      <div className="mb-3 mt-7 flex items-center justify-between gap-3">
        <h2 className="text-base font-bold text-slate-800">받은 알림</h2>
        {unread.length > 0 && <Button variant="ghost" size="sm" onClick={() => void markAllNoticesRead()}><CheckCheck size={16} />모두 읽음</Button>}
      </div>

      {notices.length ? (
        <section className="border-y border-slate-200">
          <div className="divide-y divide-slate-100">
            {notices.map(notice => (
              <Link
                key={notice.id}
                href={notice.link}
                onClick={() => void markNoticeRead(notice.id)}
                className={`flex min-h-20 gap-3 px-4 py-4 hover:bg-slate-50 sm:px-5 ${notice.read ? "" : "bg-[#f8fbfe]"}`}
              >
                <div className={`mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full ${notice.read ? "bg-slate-100 text-slate-500" : "bg-[#e8f0f8] text-[#2563a8]"}`}><Bell size={16} /></div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className={`text-sm ${notice.read ? "font-semibold text-slate-700" : "font-bold text-slate-900"}`}>{notice.title}</h3>
                    {!notice.read && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#2563a8]" aria-label="읽지 않음" />}
                  </div>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{notice.body}</p>
                  <p className="mt-1.5 text-xs text-slate-500">{notice.time}</p>
                </div>
                <ChevronRight className="mt-2 shrink-0 text-slate-400" size={17} />
              </Link>
            ))}
          </div>
        </section>
      ) : <EmptyState title="새 알림이 없어요." description="새 업무나 중요 공지가 생기면 이곳에 표시됩니다." />}

      <AppModal
        open={composeOpen}
        title="알림 보내기"
        description="수신자의 알림함에 저장되고, 푸시를 켠 기기에는 즉시 전송됩니다."
        onClose={() => setComposeOpen(false)}
        footer={<><Button variant="secondary" onClick={() => setComposeOpen(false)}>취소</Button><Button form="send-notification" type="submit" disabled={sending}>{sending ? "보내는 중…" : "알림 보내기"}<Send size={16} /></Button></>}
      >
        <form id="send-notification" className="grid gap-4" onSubmit={submitNotification}>
          <SelectField label="수신 대상" value={recipient} onChange={event => setRecipient(event.target.value)}>
            <option value="all">관리 범위 전체 ({recipients.length}명)</option>
            {recipients.map(user => <option key={user.id} value={user.id}>{user.name} · {[user.grade, user.department].filter(Boolean).join(" · ")}</option>)}
          </SelectField>
          <TextInput label="알림 제목" value={form.title} onChange={event => { setForm({ ...form, title: event.target.value }); setFormError(""); }} required error={formError} placeholder="예: 축제 운영표가 변경되었습니다" />
          <TextArea label="알림 내용" value={form.content} onChange={event => setForm({ ...form, content: event.target.value })} placeholder="받는 사람이 바로 이해할 수 있도록 다음 행동을 적어 주세요." />
        </form>
      </AppModal>
    </div>
  );
}
