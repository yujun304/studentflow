/** StudentFlow | 학기 운영 보드: 업무 상세에서는 요구사항과 다음 행동을 한 덩어리로 둔다 */
import { ArrowLeft, CheckCircle2, FileUp, Paperclip, Send, UserRound } from "lucide-react";
import { useState } from "react";
import { Link, useRoute } from "wouter";
import { useApp } from "@/contexts/AppContext";
import { AppModal, Button, SaveMessage, StatusBadge, TextArea, TextInput } from "@/components/primitives";

const statusLabel = { TODO: "해야 할 일", IN_PROGRESS: "진행 중", IN_REVIEW: "검토 중", DONE: "완료", REJECTED: "반려" } as const;

export default function TaskDetailPage() {
  const [, params] = useRoute("/tasks/:id");
  const { tasks, users, currentRole, currentUser, submitTask, updateTask, updateTaskStatus, submissions } = useApp();
  const foundTask = tasks.find((item) => item.id === params?.id);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [fileName, setFileName] = useState("");
  const [fileError, setFileError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editDraft, setEditDraft] = useState({ title: "", description: "" });
  if (!foundTask) return <div className="p-8">업무를 찾을 수 없어요.</div>;
  const task = foundTask;
  const assignee = users.find((user) => user.id === task.assigneeId);
  const ownTask = task.assigneeId === currentUser.id;
  const submission = submissions.find((item) => item.taskId === task.id);
  async function handleSubmit() { if (!fileName.trim()) { setFileError("제출할 파일을 선택해 주세요."); return; } setSaving(true); await submitTask(task.id, fileName); setSaving(false); setSaved(true); setSubmitOpen(false); }
  function saveEdit() { if (editDraft.title.trim().length < 4) return; updateTask(task.id, editDraft); setEditOpen(false); setSaved(true); }
  return <div className="mx-auto max-w-[1020px] px-4 py-7 sm:px-6 lg:px-8">
    <div className="flex items-center justify-between gap-3"><Link href="/tasks" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-[#2563a8]"><ArrowLeft size={17}/>업무 목록</Link>{currentRole !== "MEMBER" && <Button variant="secondary" size="sm" onClick={() => { setEditDraft({ title: task.title, description: task.description }); setEditOpen(true); }}>업무 수정</Button>}</div>
    <header className="mt-5 border-b border-slate-200 pb-6"><div className="flex flex-wrap items-center gap-2"><StatusBadge label={statusLabel[task.status]}/>{task.status === "REJECTED" && <span className="text-sm font-semibold text-[#a12622]">수정 후 다시 제출해 주세요.</span>}</div><h1 className="mt-3 text-2xl font-bold tracking-[-.03em] text-slate-900">{task.title}</h1><div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-500"><span>{task.department}</span><span>마감 {task.dueDate}</span><span>{task.priority} 우선</span><span className="flex items-center gap-1"><UserRound size={15}/>{assignee?.name}</span></div></header>
    <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_290px]"><section className="bg-white"><div className="border-b border-slate-200 px-4 py-3"><h2 className="font-bold">해야 할 내용</h2></div><div className="px-4 py-5"><p className="whitespace-pre-line text-sm leading-7 text-slate-700">{task.description}</p>{task.attachmentHint && <div className="mt-5 flex items-center gap-2 border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-600"><Paperclip size={16}/><span>{task.attachmentHint}</span><span className="ml-auto text-xs text-slate-500">참고 파일</span></div>}</div></section><aside className="border-t-2 border-[#2563a8] bg-white"><div className="border-b border-slate-200 px-4 py-3"><h2 className="font-bold">다음 행동</h2></div><div className="p-4">{saved && <SaveMessage>변경한 내용을 저장했어요.</SaveMessage>}{task.status === "IN_REVIEW" ? <><p className="text-sm leading-6 text-slate-600">제출물이 검토 중이에요. 담당자의 답변이 오면 알림으로 알려드릴게요.</p><StatusBadge label="검토 대기" className="mt-4"/></> : task.status === "DONE" ? <><CheckCircle2 size={24} className="text-[#17663d]"/><p className="mt-2 text-sm leading-6 text-slate-600">이 업무는 완료됐어요.</p></> : ownTask ? <><p className="text-sm leading-6 text-slate-600">완성한 파일을 올리면 담당자가 검토할 수 있어요.</p><Button onClick={() => setSubmitOpen(true)} className="mt-4 w-full"><FileUp size={17}/>제출물 올리기</Button></> : currentRole !== "MEMBER" ? <><p className="text-sm leading-6 text-slate-600">업무 상태를 바꾸면 담당자에게 바로 표시됩니다.</p><Button onClick={() => updateTaskStatus(task.id, "DONE")} className="mt-4 w-full"><CheckCircle2 size={17}/>완료로 처리하기</Button></> : <p className="text-sm leading-6 text-slate-600">이 업무는 {assignee?.name}님이 담당하고 있어요.</p>}{submission?.feedback && <div className="mt-5 border-t border-slate-200 pt-4"><p className="text-xs font-bold text-slate-500">검토 의견</p><p className="mt-1 text-sm leading-6 text-slate-700">{submission.feedback}</p></div>}</div></aside></div>
    <AppModal open={submitOpen} title="제출물 올리기" description="올린 파일은 담당자가 확인한 뒤 승인하거나 수정 요청을 보냅니다." onClose={() => setSubmitOpen(false)} footer={<><Button variant="secondary" onClick={() => setSubmitOpen(false)}>취소</Button><Button onClick={handleSubmit} disabled={saving}>{saving ? "올리는 중…" : "검토 요청하기"}<Send size={16}/></Button></>}><label className="grid gap-1.5"><span className="text-sm font-semibold text-slate-800">제출 파일 <span className="text-[#b42318]">*</span></span><input type="file" className="block w-full text-sm text-slate-600 file:mr-3 file:rounded file:border-0 file:bg-[#e8f0f8] file:px-3 file:py-2 file:text-sm file:font-semibold file:text-[#1f528b]" onChange={(event) => { setFileName(event.target.files?.[0]?.name ?? ""); setFileError(""); }}/>{fileError && <span className="text-xs text-[#b42318]">{fileError}</span>}<span className="text-xs leading-5 text-slate-500">파일은 이 데모 화면에만 표시되며 실제로 업로드되지는 않습니다.</span></label></AppModal>
    <AppModal open={editOpen} title="업무 수정" description="수정한 제목과 설명이 담당자에게 바로 보입니다." onClose={() => setEditOpen(false)} footer={<><Button variant="secondary" onClick={() => setEditOpen(false)}>취소</Button><Button onClick={saveEdit}>수정 내용 저장하기</Button></>}><div className="grid gap-4"><TextInput label="업무 제목" value={editDraft.title} onChange={(event) => setEditDraft({ ...editDraft, title: event.target.value })} required/><TextArea label="업무 설명" value={editDraft.description} onChange={(event) => setEditDraft({ ...editDraft, description: event.target.value })}/></div></AppModal>
  </div>;
}
