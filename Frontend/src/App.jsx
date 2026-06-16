import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { AuthProvider } from "./AuthContext";
import ProtectedRoute from "./ProtectedRoute";
import AIPeekTab from "./AIPeekTab";

import VoyantHero from "./VoyantHero";
import { ProblemSection, CTABand } from "./VoyantProblemCTA";
import VoyantHowItWorks from "./VoyantHowItWorks";
import VoyantFooter from "./VoyantFooter";
import VoyantAuth from "./VoyantAuth";
import VoyantDashboard from "./VoyantDashboard";
import VoyantTripDetail from "./VoyantTripDetail";
import VoyantPlanDetail from "./VoyantPlanDetail";
import VoyantCreateTrip from "./VoyantCreateTrip";
import VoyantHowAI from "./VoyantHowAI";

// ─────────────────────────────────────────────────────────────
// Voyant — App routing.
//
// Public routes:   /  /auth  /how-ai
// Protected routes (require sign-in, else redirect to /auth):
//                   /dashboard  /create  /trip/:id  /plan/:id
//
// The whole app is wrapped in <AuthProvider> so the Firebase user +
// backend profile are available everywhere via useAuth().
// ─────────────────────────────────────────────────────────────

function LandingPage() {
  return (
    <>
      <VoyantHero />
      <ProblemSection />
      <VoyantHowItWorks />
      <CTABand />
      <VoyantFooter />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AIPeekTab />
        <Routes>
          {/* public */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<VoyantAuth />} />
          <Route path="/how-ai" element={<VoyantHowAI />} />

          {/* protected */}
          <Route path="/dashboard" element={<ProtectedRoute><VoyantDashboard /></ProtectedRoute>} />
          <Route path="/create" element={<ProtectedRoute><VoyantCreateTrip /></ProtectedRoute>} />
          <Route path="/trip/:id" element={<ProtectedRoute><VoyantTripDetail /></ProtectedRoute>} />
          <Route path="/plan/:tripId/:recId" element={<ProtectedRoute><VoyantPlanDetail /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}