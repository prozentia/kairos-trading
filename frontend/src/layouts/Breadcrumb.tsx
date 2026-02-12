import { cn } from "@/lib/utils";
import { ChevronRight, House } from "lucide-react";
import { Link } from "react-router-dom";

interface BreadcrumbProps {
  title: string;
  text: string;
}

const DashboardBreadcrumb = ({ title, text }: BreadcrumbProps) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 mb-6">
      <h6 className="text-2xl font-semibold">{title}</h6>
      <nav className="flex items-center gap-1.5 text-sm">
        <Link to="/dashboard" className="flex items-center gap-1.5 text-muted-foreground hover:text-primary transition-colors">
          <House size={14} />
          Dashboard
        </Link>
        <ChevronRight size={14} className={cn("text-muted-foreground")} />
        <span className="text-foreground font-medium">{text}</span>
      </nav>
    </div>
  );
};

export default DashboardBreadcrumb;
