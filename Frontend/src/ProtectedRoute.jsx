// Voyant — ProtectedRoute. Redirects to /auth if not signed in.
// Shows a tiny loading state while the initial auth check resolves.

import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", fontFamily: "'Inter', system-ui, sans-serif", color: "#6B7872", background: "#F3EEE3" }}>
        Loading…
      </div>
    );
  }
  return user ? children : <Navigate to="/auth" replace />;
}
