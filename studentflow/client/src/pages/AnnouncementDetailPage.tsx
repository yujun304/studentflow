/** StudentFlow | 학기 운영 보드: 공지 상세에서 대상·마감·내용을 차례로 확인한다 */
import { ArrowLeft, Users } from "lucide-react";
import { Link, useRoute } from "wouter";
import { useApp } from "@/contexts/AppContext";

export default function AnnouncementDetailPage() {
  const [, params] = useRoute("/announcements/:id");
  const { announcements } = useApp();
  const announcement = announcements.find((item) => item.id === params?.id);
  if (!announcement) return <div className="p-8">공지를 찾을 수 없어요.</div>;
  return <div className="mx-auto max-w-[920px] px-4 py-7 sm:px-6 lg:px-8"><Link href="/announcements" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-[#2563a8]"><ArrowLeft size={17}/>공지 목록</Link><article className="mt-5 bg-white"><header className="border-b border-slate-200 px-4 py-5 sm:px-5"><div className="flex flex-wrap gap-2">{announcement.pinned && <span className="rounded bg-rose-50 px-2 py-1 text-xs font-bold text-[#a12622]">중요 공지</span>}<span className="rounded bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">대상: {announcement.target}</span></div><h1 className="mt-4 text-2xl font-bold tracking-[-.03em] text-slate-900">{announcement.title}</h1><p className="mt-3 text-sm text-slate-500">{announcement.author} · {announcement.createdAt}</p></header><div className="px-4 py-6 sm:px-5"><p className="whitespace-pre-line text-sm leading-8 text-slate-700">{announcement.body}</p>{announcement.application && <section className="mt-7 border border-[#c9ddf2] bg-[#f4f8fc] p-4"><div className="flex items-center gap-2 text-sm font-bold text-[#1f528b]"><Users size={17}/>선착순 신청 현황</div><p className="mt-3 text-sm text-slate-700">{announcement.application.applied}명 신청 · {announcement.application.capacity - announcement.application.applied}명 남음</p><p className="mt-1 text-xs text-slate-500">신청 마감: {announcement.application.deadline}</p></section>}</div></article></div>;
}
