import { auth } from "@/firebase";
import { Loader2 } from "lucide-react";
import { useAuthState } from "react-firebase-hooks/auth";
import { Navigate, Outlet } from "react-router-dom";

const ProtectedRoutes = () => {
    const [user, loading] = useAuthState(auth);

    if (loading) {
        return (
            <div className="fixed inset-0 flex flex-col items-center justify-center bg-background z-50">
                <Loader2 className="h-11 w-11 animate-spin text-neutral-900" />
                <p className="mt-4 text-neutral-900 font-semibold animate-pulse text-xl">Loading...</p>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/auth/login" replace />;
    }

    return (
        <Outlet />
    );
};

export default ProtectedRoutes;