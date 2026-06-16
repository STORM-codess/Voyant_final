// Voyant — Auth context. Tracks the Firebase user across the app,
// exposes signInWithGoogle() / signOutUser(), and ensures the user
// exists in our backend (try GET /users/me, else POST /users/register).

import React, { createContext, useContext, useEffect, useState } from "react";
import { signInWithPopup, signOut, onAuthStateChanged } from "firebase/auth";
import { auth, googleProvider } from "./firebase";
import { fetchMe, registerUser } from "./api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);     // Firebase user
  const [profile, setProfile] = useState(null); // our backend's user row
  const [loading, setLoading] = useState(true); // still resolving initial auth state

  // keep the Firebase user in sync across reloads
  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (fbUser) => {
      setUser(fbUser);
      if (fbUser) {
        // make sure the backend knows this user
        try {
          let me = await fetchMe();
          if (!me) {
            // new (or freshly-wiped) user — create the backend row, then
            // re-fetch so `profile` always has the full, canonical shape
            // ({ id, name, email }) rather than register's partial response.
            await registerUser({
              name: fbUser.displayName || "Traveler",
              email: fbUser.email,
            });
            me = await fetchMe();
          }
          setProfile(me);
        } catch (e) {
          console.error("Backend user sync failed:", e);
          // user is signed in to Firebase but backend sync failed;
          // keep them signed in, surface the error to the UI as needed
        }
      } else {
        setProfile(null);
      }
      setLoading(false);
    });
    return unsub;
  }, []);

  const signInWithGoogle = async () => {
    // popup → onAuthStateChanged above handles the backend sync
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  };

  const signOutUser = () => signOut(auth);

  return (
    <AuthContext.Provider value={{ user, profile, loading, signInWithGoogle, signOutUser }}>
      {children}
    </AuthContext.Provider>
  );
}