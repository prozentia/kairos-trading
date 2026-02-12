import { useRouteError, Link } from "react-router-dom";

const RouteErrorBoundary = () => {
  const error = useRouteError() as { statusText?: string; message?: string };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background">
      <h1 className="text-4xl font-bold text-destructive mb-4">Oops!</h1>
      <p className="text-lg text-muted-foreground mb-2">Something unexpected happened.</p>
      <p className="text-sm text-muted-foreground mb-6">
        {error?.statusText || error?.message || "Unknown error"}
      </p>
      <Link
        to="/dashboard"
        className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
      >
        Go to Dashboard
      </Link>
    </div>
  );
};

export default RouteErrorBoundary;
