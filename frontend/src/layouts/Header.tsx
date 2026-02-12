import BotStatusBadge from "@/components/shared/BotStatusBadge";
import { ModeToggle } from "@/components/shared/ModeToggle";
import { useBotStatus } from "@/hooks/useBot";
import { Bell, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  onToggleSidebar: () => void;
}

const Header = ({ onToggleSidebar }: HeaderProps) => {
  const { status } = useBotStatus();

  return (
    <div className="bg-card border-b border-neutral-200 dark:border-slate-700 flex items-center justify-between h-14 shrink-0 gap-2 px-4 md:px-6 sticky top-0 z-[2]">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onToggleSidebar} className="md:hidden">
          <Menu className="w-5 h-5" />
        </Button>
        {status && (
          <BotStatusBadge running={status.running} mode={status.mode} />
        )}
      </div>

      <div className="flex items-center gap-3">
        <ModeToggle />

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="w-5 h-5" />
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-destructive text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            3
          </span>
        </Button>
      </div>
    </div>
  );
};

export default Header;
