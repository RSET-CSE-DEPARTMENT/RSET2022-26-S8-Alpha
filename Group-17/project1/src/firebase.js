// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyASECyssLCgDp96CyU2wIl3OEz7LdibX-Q",
  authDomain: "corealign-31a0c.firebaseapp.com",
  projectId: "corealign-31a0c",
  storageBucket: "corealign-31a0c.firebasestorage.app",
  messagingSenderId: "161580398500",
  appId: "1:161580398500:web:97dd814ad8a784cbd03331",
  measurementId: "G-MT6YBM2041"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
