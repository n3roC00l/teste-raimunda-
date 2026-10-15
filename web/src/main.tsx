import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { iniciarConsulta } from "./api";
import App from "./App";
import "./estilo.css";

iniciarConsulta();
createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
