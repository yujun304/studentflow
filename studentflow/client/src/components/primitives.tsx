/** StudentFlow | 학기 운영 보드: 공통 UI는 촘촘한 문서형 리듬과 명확한 행동을 따른다 */
import {
  AlertCircle,
  CheckCircle2,
  LoaderCircle,
  X,
} from "lucide-react";
import {
  useEffect,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
const join = (...values: Array<string | false | undefined>) =>
  values.filter(Boolean).join(" ");
export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
}) {
  const variants = {
    primary:
      "bg-[#2563a8] text-white hover:bg-[#1f528b] focus-visible:ring-[#2563a8]",
    secondary:
      "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus-visible:ring-[#2563a8]",
    danger:
      "bg-[#b42318] text-white hover:bg-[#8e1c13] focus-visible:ring-[#b42318]",
    ghost: "text-slate-600 hover:bg-slate-100 focus-visible:ring-[#2563a8]",
  };
  const sizes = {
    sm: "h-11 px-3 text-xs sm:h-8",
    md: "h-11 px-4 text-sm sm:h-10",
    lg: "h-12 px-5 text-sm sm:h-11",
  };
  return (
    <button
      className={join(
        "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
export function TextInput({
  label,
  hint,
  error,
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
}) {
  return (
    <label className={join("grid gap-1.5", className)}>
      {label && (
        <span className="text-sm font-semibold text-slate-800">
          {label}
          {props.required && <span className="ml-1 text-[#b42318]">*</span>}
        </span>
      )}
      <input
        className={join(
          "h-11 rounded-md border bg-white px-3 text-sm text-slate-900 outline-none transition-[border-color,box-shadow,background-color] duration-150 ease-[cubic-bezier(.23,1,.32,1)] focus-visible:border-[#2563a8] focus-visible:ring-2 focus-visible:ring-[#2563a8]/15 sm:h-10",
          error ? "border-[#b42318]" : "border-slate-300"
        )}
        {...props}
      />
      {error ? (
        <span className="text-xs text-[#b42318]">{error}</span>
      ) : hint ? (
        <span className="text-xs text-slate-500">{hint}</span>
      ) : null}
    </label>
  );
}
export function SelectField({
  label,
  error,
  children,
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className={join("grid gap-1.5", className)}>
      {label && (
        <span className="text-sm font-semibold text-slate-800">
          {label}
          {props.required && <span className="ml-1 text-[#b42318]">*</span>}
        </span>
      )}
      <select
        className={join(
          "h-11 rounded-md border bg-white px-3 text-sm text-slate-900 outline-none transition-[border-color,box-shadow,background-color] duration-150 ease-[cubic-bezier(.23,1,.32,1)] focus-visible:border-[#2563a8] focus-visible:ring-2 focus-visible:ring-[#2563a8]/15 sm:h-10",
          error ? "border-[#b42318]" : "border-slate-300"
        )}
        {...props}
      >
        {children}
      </select>
      {error && <span className="text-xs text-[#b42318]">{error}</span>}
    </label>
  );
}
export function TextArea({
  label,
  hint,
  error,
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  hint?: string;
  error?: string;
}) {
  return (
    <label className={join("grid gap-1.5", className)}>
      {label && (
        <span className="text-sm font-semibold text-slate-800">
          {label}
          {props.required && <span className="ml-1 text-[#b42318]">*</span>}
        </span>
      )}
      <textarea
        className={join(
          "min-h-24 rounded-md border bg-white px-3 py-2.5 text-sm leading-6 text-slate-900 outline-none transition-[border-color,box-shadow,background-color] duration-150 ease-[cubic-bezier(.23,1,.32,1)] focus-visible:border-[#2563a8] focus-visible:ring-2 focus-visible:ring-[#2563a8]/15",
          error ? "border-[#b42318]" : "border-slate-300"
        )}
        {...props}
      />
      {error ? (
        <span className="text-xs text-[#b42318]">{error}</span>
      ) : hint ? (
        <span className="text-xs text-slate-500">{hint}</span>
      ) : null}
    </label>
  );
}
const badgeStyles: Record<string, string> = {
  TODO: "bg-slate-100 text-slate-700",
  "해야 할 일": "bg-slate-100 text-slate-700",
  IN_PROGRESS: "bg-blue-50 text-[#1f528b]",
  "진행 중": "bg-blue-50 text-[#1f528b]",
  DONE: "bg-emerald-50 text-[#17663d]",
  완료: "bg-emerald-50 text-[#17663d]",
  APPROVED: "bg-emerald-50 text-[#17663d]",
  PENDING: "bg-amber-50 text-[#895d09]",
  DRAFT: "bg-slate-100 text-slate-700",
  초안: "bg-slate-100 text-slate-700",
  "모집 중": "bg-blue-50 text-[#1f528b]",
  마감: "bg-slate-100 text-slate-700",
  예정: "bg-slate-100 text-slate-700",
  ATTEND: "bg-emerald-50 text-[#17663d]",
  출석: "bg-emerald-50 text-[#17663d]",
  LATE: "bg-amber-50 text-[#895d09]",
  지각: "bg-amber-50 text-[#895d09]",
  ABSENT: "bg-rose-50 text-[#a12622]",
  결석: "bg-rose-50 text-[#a12622]",
  EXCUSED: "bg-violet-50 text-violet-700",
  인정: "bg-violet-50 text-violet-700",
};
export function StatusBadge({
  label,
  className,
}: {
  label: string;
  className?: string;
}) {
  return (
    <span
      className={join(
        "inline-flex shrink-0 items-center rounded px-2 py-1 text-xs font-semibold",
        badgeStyles[label] ?? "bg-slate-100 text-slate-700",
        className
      )}
    >
      {label}
    </span>
  );
}
export function Avatar({
  label,
  size = "md",
}: {
  label: string;
  size?: "sm" | "md";
}) {
  return (
    <span
      aria-hidden="true"
      className={join(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-[#e8f0f8] font-bold text-[#2563a8]",
        size === "sm" ? "h-7 w-7 text-xs" : "h-9 w-9 text-sm"
      )}
    >
      {label.slice(0, 1)}
    </span>
  );
}
export function AppModal({
  open,
  title,
  description,
  onClose,
  children,
  footer,
  size = "md",
}: {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  size?: "md" | "xl";
}) {
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", close);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", close);
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-slate-900/35 p-0 sm:items-center sm:justify-center sm:p-6"
      role="presentation"
      onMouseDown={onClose}
    >
      <section
        className={join(
          "flex max-h-[92dvh] w-full flex-col rounded-t-xl bg-white shadow-2xl sm:max-h-[86vh] sm:rounded-xl",
          size === "xl" ? "max-w-5xl" : "max-w-lg"
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        onMouseDown={event => event.stopPropagation()}
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h2
              id="dialog-title"
              className="text-base font-bold text-slate-900"
            >
              {title}
            </h2>
            {description && (
              <p className="mt-1 text-sm leading-5 text-slate-500">
                {description}
              </p>
            )}
          </div>
          <button
            aria-label="창 닫기"
            onClick={onClose}
            className="-mr-2 grid h-11 w-11 shrink-0 place-items-center rounded text-slate-500 hover:bg-slate-100 hover:text-slate-700 sm:h-10 sm:w-10"
          >
            <X size={20} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          {children}
        </div>
        {footer && (
          <footer className="flex shrink-0 flex-wrap justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3 pb-[calc(.75rem+env(safe-area-inset-bottom))] [&>button]:flex-1 sm:pb-3 sm:[&>button]:flex-none">
            {footer}
          </footer>
        )}
      </section>
    </div>
  );
}
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="grid min-h-44 place-items-center border-y border-slate-200 px-5 py-10 text-center">
      <div className="max-w-sm">
        <h3 className="text-sm font-bold text-slate-800">{title}</h3>
        <p className="mt-1.5 text-sm leading-6 text-slate-500">{description}</p>
        {action && <div className="mt-4">{action}</div>}
      </div>
    </div>
  );
}
export function LoadingState({
  label = "내용을 불러오는 중이에요.",
}: {
  label?: string;
}) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-sm text-slate-500">
      <LoaderCircle className="animate-spin text-[#2563a8]" size={22} />
      {label}
    </div>
  );
}
export function ErrorState({
  title = "내용을 불러오지 못했어요.",
  description = "인터넷 연결을 확인한 뒤 다시 시도해 주세요.",
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="grid min-h-48 place-items-center border border-rose-200 bg-rose-50 px-5 py-8 text-center">
      <div>
        <AlertCircle className="mx-auto mb-2 text-[#b42318]" size={22} />
        <h3 className="text-sm font-bold text-[#7a271a]">{title}</h3>
        <p className="mt-1 text-sm text-[#9a3412]">{description}</p>
        {onRetry && (
          <Button
            onClick={onRetry}
            variant="secondary"
            size="sm"
            className="mt-4"
          >
            다시 시도하기
          </Button>
        )}
      </div>
    </div>
  );
}
export function PermissionState({
  title = "이 화면은 담당 선생님만 관리할 수 있어요.",
  description = "현재 역할에서는 내용을 볼 수 있지만 변경할 수는 없습니다.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="grid min-h-44 place-items-center border-y border-slate-200 px-5 py-10 text-center">
      <div className="max-w-md">
        <h3 className="text-sm font-bold text-slate-800">{title}</h3>
        <p className="mt-1.5 text-sm leading-6 text-slate-500">{description}</p>
      </div>
    </div>
  );
}
export function SaveMessage({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-center gap-1.5 text-sm text-[#17663d]">
      <CheckCircle2 size={16} />
      {children}
    </p>
  );
}
