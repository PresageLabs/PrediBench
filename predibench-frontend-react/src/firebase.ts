import { initializeApp } from 'firebase/app';
import { getAnalytics } from 'firebase/analytics';
import type { Analytics } from 'firebase/analytics';

const firebaseConfig = {
  apiKey: "AIzaSyBDarsWHLp76j1HgSo22mS8JlzR0AtNZ_w",
  authDomain: "predibench.firebaseapp.com",
  projectId: "predibench",
  storageBucket: "predibench.firebasestorage.app",
  messagingSenderId: "273710233257",
  appId: "1:273710233257:web:7a07a9c0d76370d85cdbb8",
  measurementId: "G-KJFQSXN9S9"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Analytics
let analytics: Analytics | null = null;
if (typeof window !== 'undefined') {
  analytics = getAnalytics(app);

  // Enable analytics debug mode in development
  if (import.meta.env.DEV) {
    console.log('Firebase Analytics initialized in development mode');
  }
}

export { analytics };