/** StudentFlow | 공지 읽음과 선착순 신청을 실제 서버 상태로 처리한다. */
import { ArrowLeft, Check, Users } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "@/components/MpaLink";
import { Button } from "@/components/primitives";
import { useApp } from "@/contexts/AppContext";
import { ApiError } from "@/lib/api";
import { documentPathId } from "@/lib/document-path";

export default function AnnouncementDetailPage() {
  const announcementId = documentPathId("/announcements");
  const { announcements, readAnnouncement, toggleAnnouncementApplication } =
    useApp();
  const announcement = announcements.find(item => item.id === announcementId);
  const marked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!announcement || announcement.read || marked.current) return;
    marked.current = true;
    void readAnnouncement(announcement.id).catch(reason => {
      marked.current = false;
      setError(
        reason instanceof ApiError
          ? reason.message
          : "읽음 상태를 저장하지 못했습니다."
      );
    });
  }, [announcement, readAnnouncement]);

  if (!announcement) return <div className="p-8">공지를 찾을 수 없어요.</div>;
  const activeAnnouncement = announcement;
  const applied = Boolean(announcement.application?.status);
  async function toggleApplication() {
    setBusy(true);
    setError("");
    try {
      await toggleAnnouncementApplication(activeAnnouncement.id, applied);
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "신청 상태를 바꾸지 못했습니다."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-[920px] px-4 py-7 sm:px-6 lg:px-8">
      <Link
        href="/announcements"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-[#2563a8]"
      >
        <ArrowLeft size={17} />
        공지 목록
      </Link>
      <article className="mt-5 bg-white">
        <header className="border-b border-slate-200 px-4 py-5 sm:px-5">
          <div className="flex flex-wrap gap-2">
            {announcement.pinned && (
              <span className="rounded bg-rose-50 px-2 py-1 text-xs font-bold text-[#a12622]">
                중요 공지
              </span>
            )}
            <span className="rounded bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
              대상: {announcement.target}
            </span>
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-[-.03em] text-slate-900">
            {announcement.title}
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            {announcement.author} · {announcement.createdAt}
          </p>
        </header>
        <div className="px-4 py-6 sm:px-5">
          <p className="whitespace-pre-line text-sm leading-8 text-slate-700">
            {announcement.body}
          </p>
          {announcement.application && (
            <section className="mt-7 border border-[#c9ddf2] bg-[#f4f8fc] p-4">
              <div className="flex items-center gap-2 text-sm font-bold text-[#1f528b]">
                <Users size={17} />
                선착순 신청
              </div>
              <p className="mt-3 text-sm text-slate-700">
                {announcement.application.applied}명 신청 ·{" "}
                {Math.max(
                  0,
                  announcement.application.capacity -
                    announcement.application.applied
                )}
                명 남음
              </p>
              <p className="mt-1 text-xs text-slate-500">
                신청 마감: {announcement.application.deadline}
              </p>
              <Button
                className="mt-4"
                variant={applied ? "secondary" : "primary"}
                onClick={() => void toggleApplication()}
                disabled={busy}
              >
                {applied && <Check size={16} />}{" "}
                {busy
                  ? "처리 중…"
                  : applied
                    ? announcement.application.status === "WAITING"
                      ? "대기 신청 취소"
                      : "신청 완료 · 취소하기"
                    : "신청하기"}
              </Button>
            </section>
          )}
          {error && (
            <p className="mt-4 text-sm font-semibold text-[#b42318]">{error}</p>
          )}
        </div>
      </article>
      <div className="mt-5">
        <Link href="/tutorial">
          <Button variant="secondary">체험 안내로 돌아가기</Button>
        </Link>
      </div>
    </div>
  );
}
