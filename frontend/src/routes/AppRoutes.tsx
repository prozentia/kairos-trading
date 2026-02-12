import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import NotFound from "@/error/404";
import RouteErrorBoundary from "@/error/RouteErrorBoundary";
import MainLayout from "@/layouts/MainLayout";
import GuestRoutes from "./GuestRoutes";
import ProtectedRoutes from "./ProtectedRoutes";

// Auth pages
import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import ForgotPassword from "@/pages/auth/ForgotPassword";

// Lazy-loaded pages
const Dashboard = lazy(() => import("@/pages/dashboard/Dashboard"));
const TradesList = lazy(() => import("@/pages/trades/TradesList"));
const TradeDetail = lazy(() => import("@/pages/trades/TradeDetail"));
const StrategiesList = lazy(() => import("@/pages/strategies/StrategiesList"));
const StrategyBuilder = lazy(() => import("@/pages/strategies/StrategyBuilder"));
const StrategyDetail = lazy(() => import("@/pages/strategies/StrategyDetail"));
const Portfolio = lazy(() => import("@/pages/portfolio/Portfolio"));
const BotControl = lazy(() => import("@/pages/bot/BotControl"));
const BotLogs = lazy(() => import("@/pages/bot/BotLogs"));
const Settings = lazy(() => import("@/pages/settings/Settings"));
const Profile = lazy(() => import("@/pages/settings/Profile"));

export const router = createBrowserRouter([
  // Guest routes (login, register, etc.)
  {
    element: <GuestRoutes />,
    errorElement: <RouteErrorBoundary />,
    children: [
      { path: "/auth/login", element: <Login /> },
      { path: "/auth/register", element: <Register /> },
      { path: "/auth/forgot-password", element: <ForgotPassword /> },
    ],
  },

  // Protected routes (authenticated)
  {
    element: <ProtectedRoutes />,
    children: [
      {
        path: "/",
        element: <MainLayout />,
        errorElement: <RouteErrorBoundary />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: "dashboard", element: <Dashboard /> },
          { path: "trades", element: <TradesList /> },
          { path: "trades/:tradeId", element: <TradeDetail /> },
          { path: "strategies", element: <StrategiesList /> },
          { path: "strategies/new", element: <StrategyBuilder /> },
          { path: "strategies/:id", element: <StrategyDetail /> },
          { path: "strategies/:id/edit", element: <StrategyBuilder /> },
          { path: "portfolio", element: <Portfolio /> },
          { path: "bot", element: <BotControl /> },
          { path: "bot/logs", element: <BotLogs /> },
          { path: "settings", element: <Settings /> },
          { path: "settings/profile", element: <Profile /> },
        ],
      },
    ],
  },

  // 404
  { path: "*", element: <NotFound />, errorElement: <RouteErrorBoundary /> },
]);
