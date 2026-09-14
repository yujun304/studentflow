/** StudentFlow | 학기 운영 보드: 행사 정보와 선착순 신청 상태를 같은 자리에 보여 준다 */
import { CalendarDays, MapPin } from "lucide-react";
import { useState } from "react";
import { useApp } from "@/contexts/AppContext";
import type { EventItem } from "@/types";
import { AppModal, Button, StatusBadge } from "@/components/primitives";
export default function EventsPage() {
  const { events, currentUser, toggleEventJoin } = useApp();
  const [selected, setSelected] = useState<EventItem | null>(null);
  return (
    <div className="mx-auto max-w-[1120px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-[-.03em]">행사</h1>
      </header>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {events.map(event => (
          <button
            key={event.id}
            onClick={() => setSelected(event)}
            className="border border-slate-200 bg-white p-5 text-left transition hover:border-slate-300 hover:bg-slate-50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="grid h-11 w-11 shrink-0 place-items-center border border-slate-200 bg-slate-50 text-center">
                <b className="text-xs text-[#2563a8]">
                  {event.date.split(" ")[0]}
                </b>
                <span className="-mt-2 text-[10px] text-slate-500">
                  {event.date.split(" ")[1]}
                </span>
              </div>
              <StatusBadge label={event.status} />
            </div>
            <h2 className="mt-5 text-base font-bold leading-6 text-slate-800">
              {event.title}
            </h2>
            <p className="mt-2 flex items-center gap-1.5 text-sm text-slate-500">
              <CalendarDays size={15} />
              {event.time}
            </p>
            <p className="mt-1.5 flex items-center gap-1.5 text-sm text-slate-500">
              <MapPin size={15} />
              {event.location}
            </p>
            <div className="mt-5 border-t border-slate-200 pt-3 text-sm">
              <span className="font-semibold text-slate-700">
                {event.participants.length}명 참여
              </span>
            </div>
          </button>
        ))}
      </div>
      <AppModal
        open={Boolean(selected)}
        title={selected?.title ?? "행사"}
        description={
          selected
            ? `${selected.date} · ${selected.time} · ${selected.location}`
            : undefined
        }
        onClose={() => setSelected(null)}
        footer={
          selected && selected.status !== "마감" ? (
            <Button
              onClick={async () => {
                await toggleEventJoin(selected.id);
                setSelected(null);
              }}
            >
              {selected.participants.includes(currentUser.name)
                ? "참여 취소하기"
                : "행사 참여하기"}
            </Button>
          ) : undefined
        }
      >
        {selected && (
          <div className="grid gap-5">
            <p className="text-sm leading-7 text-slate-700">
              {selected.description}
            </p>
            <div className="grid grid-cols-2 border border-slate-200">
              <div className="p-3">
                <p className="text-xs font-bold text-slate-500">담당</p>
                <p className="mt-1 text-sm font-semibold">{selected.owner}</p>
              </div>
              <div className="border-l border-slate-200 p-3">
                <p className="text-xs font-bold text-slate-500">참여 현황</p>
                <p className="mt-1 text-sm font-semibold">
                  {selected.participants.length}명
                </p>
              </div>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-500">참여자</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {selected.participants.length ? (
                  selected.participants.map(name => (
                    <span
                      key={name}
                      className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700"
                    >
                      {name}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-slate-500">
                    아직 참여자가 없습니다.
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </AppModal>
    </div>
  );
}
