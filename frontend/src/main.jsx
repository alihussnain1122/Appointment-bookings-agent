import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AdminProvider } from "./context/AdminProvider";
import { CallProvider } from "./context/CallProvider";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <CallProvider>
        <AdminProvider>
          <App />
        </AdminProvider>
      </CallProvider>
    </BrowserRouter>
  </StrictMode>
);
