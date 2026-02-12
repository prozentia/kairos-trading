import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";
import { Navigate, Outlet } from "react-router-dom";

const GuestRoutes = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex flex-col items-center justify-center bg-background z-50">
        <Loader2 className="h-11 w-11 animate-spin text-primary" />
        <p className="mt-4 text-foreground font-semibold animate-pulse text-xl">Loading...</p>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
};

export default GuestRoutes;
