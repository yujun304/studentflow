/** StudentFlow | 학기 운영 보드: 지난 기수는 읽기 전용 기록으로 명확히 구분한다 */
import { Archive, LockKeyhole, Search } from "lucide-react";
import { useState } from "react";
import { useApp } from "@/contexts/AppContext";
import { EmptyState, ErrorState, LoadingState } from "@/components/primitives";
export default function ArchivesPage() {
  const { archives } = useApp();
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"records" | "loading" | "error" | "empty">(
    "records"
  );
  const items = archives.filter(archive =>
    `${archive.semester}${archive.name}`.includes(query)
  );
  return (
    <div className="mx-auto max-w-[1050px] px-4 py-7 sm:px-6 lg:px-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-[-.03em]">기수 아카이브</h1>
      </header>
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row">
        <label className="relative block max-w-md flex-1">
          <span className="sr-only">기수 검색</span>
          <input
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="학기 또는 기수로 찾기"
            className="h-10 w-full rounded-md border border-slate-300 bg-white pl-9 pr-3 text-sm outline-none focus:border-[#2563a8] focus:ring-2 focus:ring-[#2563a8]/15"
          />
          <Search size={16} className="absolute left-3 top-3 text-slate-400" />
        </label>
        <select
          value={view}
          onChange={event => setView(event.target.value as typeof view)}
          className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-600"
        >
          <option value="records">아카이브 보기</option>
          <option value="loading">로딩 상태 보기</option>
          <option value="error">오류 상태 보기</option>
          <option value="empty">빈 상태 보기</option>
        </select>
      </div>
      {view === "loading" ? (
        <LoadingState label="기수 기록을 불러오는 중이에요." />
      ) : view === "error" ? (
        <ErrorState onRetry={() => setView("records")} />
      ) : view === "empty" || !items.length ? (
        <EmptyState
          title="조건에 맞는 기수 기록이 없어요."
          description="다른 학기나 기수 이름으로 찾아 보세요."
        />
      ) : (
        <section className="border border-slate-200 bg-white">
          <div className="divide-y divide-slate-100">
            {items.map(archive => (
              <article
                key={archive.id}
                className="flex flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-5"
              >
                <div className="flex gap-3">
                  <div className="grid h-10 w-10 shrink-0 place-items-center bg-[#e8f0f8] text-[#2563a8]">
                    <Archive size={19} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-500">
                      {archive.semester}
                    </p>
                    <h2 className="mt-1 font-bold text-slate-800">
                      {archive.name}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      구성원 {archive.members}명 · {archive.note}
                    </p>
                  </div>
                </div>
                <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                  <LockKeyhole size={14} />
                  읽기 전용
                </span>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
