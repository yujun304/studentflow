/** StudentFlow | 학기 운영 보드: 로그인 이후 모든 업무 화면을 같은 운영 선반 안에 둔다 */
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppShell from "@/components/AppShell";
import { AppProvider, useApp } from "@/contexts/AppContext";
import AnnouncementsPage from "@/pages/AnnouncementsPage";
import AnnouncementDetailPage from "@/pages/AnnouncementDetailPage";
import ArchivesPage from "@/pages/ArchivesPage";
import AttendancePage from "@/pages/AttendancePage";
import CalendarPage from "@/pages/CalendarPage";
import DashboardPage from "@/pages/DashboardPage";
import EventsPage from "@/pages/EventsPage";
import EventDetailPage from "@/pages/EventDetailPage";
import LoginPage from "@/pages/LoginPage";
import MinutesPage from "@/pages/MinutesPage";
import NotificationsPage from "@/pages/NotificationsPage";
import SubmissionsPage from "@/pages/SubmissionsPage";
import TaskDetailPage from "@/pages/TaskDetailPage";
import TasksPage from "@/pages/TasksPage";
import TeamsPage from "@/pages/TeamsPage";
import UsersPage from "@/pages/UsersPage";
import { Redirect, Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
function Router() { const { signedIn } = useApp(); if (!signedIn) return <Switch><Route path="/login" component={LoginPage}/><Route><Redirect to="/login"/></Route></Switch>; return <AppShell><Switch><Route path="/" component={DashboardPage}/><Route path="/tasks/:id" component={TaskDetailPage}/><Route path="/tasks" component={TasksPage}/><Route path="/submissions" component={SubmissionsPage}/><Route path="/events/:id" component={EventDetailPage}/><Route path="/events" component={EventsPage}/><Route path="/announcements/:id" component={AnnouncementDetailPage}/><Route path="/announcements" component={AnnouncementsPage}/><Route path="/calendar" component={CalendarPage}/><Route path="/teams" component={TeamsPage}/><Route path="/attendance" component={AttendancePage}/><Route path="/minutes" component={MinutesPage}/><Route path="/notifications" component={NotificationsPage}/><Route path="/users" component={UsersPage}/><Route path="/archives" component={ArchivesPage}/><Route><Redirect to="/"/></Route></Switch></AppShell>; }

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
        // switchable
      >
        <TooltipProvider>
          <Toaster />
          <AppProvider><Router /></AppProvider>
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
