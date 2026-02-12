import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import {
  Activity,
  BarChart3,
  Bot,
  Briefcase,
  ChevronDown,
  ClipboardList,
  Gauge,
  LayoutDashboard,
  LogOut,
  ScrollText,
  Settings,
  Target,
  TrendingUp,
  User,
} from "lucide-react";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

interface NavItem {
  label: string;
  icon: React.ReactNode;
  href?: string;
  children?: { label: string; href: string }[];
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const navigation: NavGroup[] = [
  {
    title: "TRADING",
    items: [
      { label: "Overview", icon: <LayoutDashboard className="w-5 h-5" />, href: "/dashboard" },
      { label: "Portfolio", icon: <Briefcase className="w-5 h-5" />, href: "/portfolio" },
      { label: "Trade History", icon: <ClipboardList className="w-5 h-5" />, href: "/trades" },
    ],
  },
  {
    title: "STRATEGIES",
    items: [
      { label: "Strategy Builder", icon: <Target className="w-5 h-5" />, href: "/strategies" },
    ],
  },
  {
    title: "MONITORING",
    items: [
      { label: "Bot Control", icon: <Bot className="w-5 h-5" />, href: "/bot" },
      {
        label: "Bot Logs",
        icon: <ScrollText className="w-5 h-5" />,
        href: "/bot/logs",
      },
    ],
  },
  {
    title: "ANALYTICS",
    items: [
      { label: "Statistics", icon: <BarChart3 className="w-5 h-5" />, href: "/trades?tab=stats" },
      { label: "Performance", icon: <TrendingUp className="w-5 h-5" />, href: "/portfolio" },
    ],
  },
];

const Sidebar = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const isActive = (href?: string) => {
    if (!href) return false;
    if (href === "/dashboard") return location.pathname === "/dashboard" || location.pathname === "/";
    return location.pathname.startsWith(href.split("?")[0]);
  };

  return (
    <div className="flex flex-col h-full bg-sidebar text-sidebar-foreground">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-sidebar-border">
        <Link to="/dashboard" className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Gauge className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">KAIROS</h1>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground -mt-1">Trading</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-6 scrollbar-thin">
        {navigation.map((group) => (
          <div key={group.title}>
            <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-3 mb-2">
              {group.title}
            </p>
            <ul className="space-y-1">
              {group.items.map((item) => (
                <li key={item.label}>
                  {item.children ? (
                    <>
                      <button
                        onClick={() => toggleGroup(item.label)}
                        className={cn(
                          "flex items-center w-full gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                          "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                        )}
                      >
                        {item.icon}
                        <span className="flex-1 text-left">{item.label}</span>
                        <ChevronDown className={cn("w-4 h-4 transition-transform", expandedGroups.has(item.label) && "rotate-180")} />
                      </button>
                      {expandedGroups.has(item.label) && (
                        <ul className="ml-8 mt-1 space-y-1">
                          {item.children.map((child) => (
                            <li key={child.href}>
                              <Link
                                to={child.href}
                                className={cn(
                                  "block px-3 py-1.5 rounded-md text-sm transition-colors",
                                  isActive(child.href)
                                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                                    : "hover:bg-sidebar-accent/50"
                                )}
                              >
                                {child.label}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  ) : (
                    <Link
                      to={item.href!}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                        isActive(item.href)
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      )}
                    >
                      {item.icon}
                      <span>{item.label}</span>
                      {item.href === "/bot" && (
                        <Activity className="w-3 h-3 ml-auto text-green-500 animate-pulse" />
                      )}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer / User */}
      <div className="border-t border-sidebar-border p-3 space-y-2">
        <Link
          to="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
            isActive("/settings")
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          )}
        >
          <Settings className="w-5 h-5" />
          <span>Settings</span>
        </Link>
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
            <User className="w-4 h-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.username || "User"}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email || ""}</p>
          </div>
          <button onClick={logout} className="text-muted-foreground hover:text-foreground transition-colors" title="Logout">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
