// ============================================================
// Lentis Gallery — Protected Route Component
// ============================================================
// A wrapper that checks if the user is authenticated before
// rendering the child component. If not, it redirects to the
// appropriate login page.
//
// HOW IT WORKS:
//   <ProtectedRoute requiredRole="ADMIN">
//     <AdminConsolePage />
//   </ProtectedRoute>
//
//   If the user is not logged in -> redirect to /admin/login
//   If the user has wrong role   -> redirect to /host (or /)
//
// SECURITY NOTE:
//   This is a FRONTEND convenience. The backend independently
//   enforces authentication on every protected API endpoint.
//   Even if someone bypasses this component (e.g. by modifying
//   the JS), the API calls will fail with 401 Unauthorized.
// ============================================================

import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated, getUserRole, isLoggedOut } from "../services/auth";

interface ProtectedRouteProps {
  /** The role required to access this route (ADMIN or HOST). */
  requiredRole?: "ADMIN" | "HOST";
  /** The component to render if authenticated. */
  children: React.ReactNode;
}

/**
 * Route guard: redirects to login if not authenticated,
 * or to the wrong page if the role does not match.
 */
export default function ProtectedRoute({
  requiredRole,
  children,
}: ProtectedRouteProps) {
  const location = useLocation();

  // If the user just logged out, block back-button navigation.
  if (isLoggedOut()) {
    const loginPath = requiredRole === "ADMIN" ? "/admin/login" : "/";
    return <Navigate to={loginPath} replace />;
  }

  // Not authenticated at all -> redirect to appropriate login.
  if (!isAuthenticated()) {
    const loginPath =
      requiredRole === "ADMIN" ? "/admin/login" : "/";
    return <Navigate to={loginPath} state={{ from: location }} replace />;
  }

  // Authenticated but wrong role -> redirect to home.
  const role = getUserRole();
  if (requiredRole && role !== requiredRole) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
