import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const nextThemeLabel = theme === "light" ? "다크 테마" : "화이트 테마";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`inline-flex h-11 min-w-11 items-center justify-center gap-2 border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:h-9 sm:min-w-0 ${className}`}
      aria-label={`${nextThemeLabel}로 전환`}
      title={`${nextThemeLabel}로 전환`}
    >
      {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
      <span className="hidden sm:inline">{theme === "light" ? "다크" : "화이트"}</span>
    </button>
  );
}
