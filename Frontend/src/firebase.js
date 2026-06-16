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
  apiKey: "AIzaSyBCrm5WLtGb1xwMhyA1dFSljkq_FmqiAlM",
  authDomain: "voyant-ca071.firebaseapp.com",
  projectId: "voyant-ca071",
  storageBucket: "voyant-ca071.firebasestorage.app",
  messagingSenderId: "811970755331",
  appId: "1:811970755331:web:c4e49d76f565c156214736"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
