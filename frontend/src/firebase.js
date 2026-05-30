import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyD44QiMcoAIm72F7PGAq9p452JKrd2m2Fo",
  authDomain: "react-auth-project-ed555.firebaseapp.com",
  projectId: "react-auth-project-ed555",
  storageBucket: "react-auth-project-ed555.firebasestorage.app",
  messagingSenderId: "327592581786",
  appId: "1:327592581786:web:91105316253e996d669d23",
  measurementId: "G-DWBEDK59Y3"
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
