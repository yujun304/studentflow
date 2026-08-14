/** StudentFlow | 학기 운영 보드: 행사 상세에서 일정 맥락과 참석 행동을 한 화면에 둔다 */
import { ArrowLeft, CalendarDays, MapPin, Users } from "lucide-react";
import { Link, useRoute } from "wouter";
import { useApp } from "@/contexts/AppContext";
import { Button, StatusBadge } from "@/components/primitives";

export default function EventDetailPage() {
  const [, params] = useRoute("/events/:id");
  const { events, currentUser, toggleEventJoin } = useApp();
  const event = events.find((item) => item.id === params?.id);
  if (!event) return <div className="p-8">행사를 찾을 수 없어요.</div>;
  const joined = event.participants.includes(currentUser.name);
  return <div className="mx-auto max-w-[920px] px-4 py-7 sm:px-6 lg:px-8"><Link href="/events" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-[#2563a8]"><ArrowLeft size={17}/>행사 목록</Link><header className="mt-5 border-b border-slate-200 pb-6"><StatusBadge label={event.status}/><h1 className="mt-3 text-2xl font-bold tracking-[-.03em] text-slate-900">{event.title}</h1><div className="mt-4 grid gap-2 text-sm text-slate-600 sm:grid-cols-2"><p className="flex items-center gap-2"><CalendarDays size={16} className="text-[#2563a8]"/>{event.date} · {event.time}</p><p className="flex items-center gap-2"><MapPin size={16} className="text-[#2563a8]"/>{event.location}</p></div></header><div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]"><section className="bg-white"><div className="border-b border-slate-200 px-4 py-3"><h2 className="font-bold">행사 안내</h2></div><div className="p-4"><p className="text-sm leading-7 text-slate-700">{event.description}</p><div className="mt-5 border-t border-slate-200 pt-4"><p className="text-xs font-bold text-slate-500">담당</p><p className="mt-1 text-sm font-semibold text-slate-800">{event.owner}</p></div></div></section><aside className="border-t-2 border-[#2563a8] bg-white"><div className="border-b border-slate-200 px-4 py-3"><h2 className="font-bold">참석 현황</h2></div><div className="p-4"><div className="flex items-center gap-2"><Users size={18} className="text-[#2563a8]"/><p className="text-sm font-bold text-slate-800">{event.participants.length} / {event.capacity}명 신청</p></div><p className="mt-2 text-sm leading-6 text-slate-500">{joined ? "참석 신청을 완료했어요." : "참석하려면 아래 버튼을 눌러 주세요."}</p><Button onClick={() => toggleEventJoin(event.id)} className="mt-4 w-full">{joined ? "신청 취소하기" : "참석 신청하기"}</Button><div className="mt-5 border-t border-slate-200 pt-4"><p className="text-xs font-bold text-slate-500">신청한 사람</p><div className="mt-2 flex flex-wrap gap-1.5">{event.participants.map((name) => <span key={name} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{name}</span>)}</div></div></div></aside></div></div>;
}
