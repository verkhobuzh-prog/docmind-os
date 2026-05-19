import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  FileText,
  MessageSquare,
  Settings,
  LogOut,
  Shield,
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useSettingsStore, TRUST_LEVEL_INFO } from "@/stores/settingsStore";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/dashboard", icon: FileText, label: "Documents" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function AppLayout() {
  const navigate = useNavigate();
  const { user, signOut } = useAuthStore();
  const trustLevel = useSettingsStore((s) => s.trustLevel);
  const trust = TRUST_LEVEL_INFO[trustLevel];

  const handleSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen bg-surface">
      <aside className="flex w-64 flex-col border-r border-slate-700/50 bg-surface-raised">
        <div className="border-b border-slate-700/50 p-5">
          <h1 className="text-lg font-bold text-white">DocMind OS</h1>
          <p className="mt-1 text-xs text-slate-400">Enterprise Document AI</p>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent/20 text-accent"
                    : "text-slate-400 hover:bg-surface-overlay hover:text-slate-200"
                )
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-700/50 p-4 space-y-3">
          <div className="flex items-center gap-2 rounded-lg bg-surface-overlay px-3 py-2 text-xs">
            <Shield className={cn("h-4 w-4", trust.color)} />
            <span className="text-slate-400">
              Trust: <span className={trust.color}>{trust.label}</span>
            </span>
          </div>
          <p className="truncate text-xs text-slate-500">{user?.email}</p>
          <Button variant="ghost" size="sm" className="w-full justify-start" onClick={handleSignOut}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
