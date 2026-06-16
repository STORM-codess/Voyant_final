// Voyant — Firebase initialization.
//
// SETUP (do once, in your Firebase console):
//   1. Project Settings → your web app → copy the config object below.
//   2. Authentication → Sign-in method → enable Google.
//   3. Authentication → Settings → Authorized domains → ensure
//      "localhost" is listed (it is by default).
//
// Then paste your config into firebaseConfig below.

import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

// ⚠️ REPLACE with your real config from the Firebase console:
const firebaseConfig = {
## replace with real values
}

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
