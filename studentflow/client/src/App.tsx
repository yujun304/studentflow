/** StudentFlow | 학기 운영 보드: 로그인 이후 모든 업무 화면을 같은 운영 선반 안에 둔다 */
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppShell from "@/components/AppShell";
import { AppProvider, useApp } from "@/contexts/AppContext";
import AnnouncementDetailPage from "@/pages/AnnouncementDetailPage";
import AnnouncementsPage from "@/pages/AnnouncementsPage";
import EventDetailPage from "@/pages/EventDetailPage";
import LoginPage from "@/pages/LoginPage";
import NotificationsPage from "@/pages/NotificationsPage";
import CalendarPage from "@/pages/CalendarPage";
import CommunityPage from "@/pages/CommunityPage";
import ProposalDetailPage from "@/pages/ProposalDetailPage";
import ProposalHomePage from "@/pages/ProposalHomePage";
import ProposalsPage from "@/pages/ProposalsPage";
import TaskDetailPage from "@/pages/TaskDetailPage";
import TasksPage from "@/pages/TasksPage";
import TeamsPage from "@/pages/TeamsPage";
import UsersPage from "@/pages/UsersPage";
import TeacherEventCreatePage from "@/pages/TeacherEventCreatePage";
import TutorialPage from "@/pages/TutorialPage";
import { currentDocumentPath } from "@/lib/document-path";
import { useEffect, type ComponentType } from "react";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";

const documentPages: Record<string, ComponentType> = {
  "/": ProposalHomePage,
  "/proposals": ProposalsPage,
  "/community": ProposalsPage,
  "/community-workspace": CommunityPage,
  "/calendar": CalendarPage,
  "/tasks": TasksPage,
  "/announcements": AnnouncementsPage,
  "/teams": TeamsPage,
  "/notifications": NotificationsPage,
  "/users": UsersPage,
  "/event-create": TeacherEventCreatePage,
  "/tutorial": TutorialPage,
};

function resolveDocumentPage(path: string) {
  if (/^\/tasks\/[^/]+$/.test(path)) return TaskDetailPage;
  if (/^\/proposals\/[^/]+$/.test(path)) return ProposalDetailPage;
  if (/^\/announcements\/[^/]+$/.test(path)) return AnnouncementDetailPage;
  if (/^\/events\/[^/]+$/.test(path)) return EventDetailPage;
  return documentPages[path];
}

function LoadingDocument() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f7f8fa] text-sm font-semibold text-slate-500">
      StudentFlow를 여는 중…
    </main>
  );
}

function DocumentRedirect({ to }: { to: string }) {
  useEffect(() => {
    window.location.replace(to);
  }, [to]);
  return <LoadingDocument />;
}

function DocumentRouter() {
  const { authReady, signedIn } = useApp();
  const path = currentDocumentPath();

  if (!authReady) return <LoadingDocument />;
  if (!signedIn) {
    return path === "/login" ? (
      <LoginPage />
    ) : (
      <DocumentRedirect to={`/login?next=${encodeURIComponent(path)}`} />
    );
  }
  if (path === "/login") return <DocumentRedirect to="/" />;

  const Page = resolveDocumentPage(path);
  return Page ? (
    <AppShell>
      <Page />
    </AppShell>
  ) : (
    <DocumentRedirect to="/" />
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
        switchable
      >
        <TooltipProvider>
          <Toaster />
          <AppProvider><DocumentRouter /></AppProvider>
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
