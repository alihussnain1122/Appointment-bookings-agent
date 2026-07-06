import { Link, Route, Routes } from "react-router-dom";
import CallPage from "./pages/CallPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<CallPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route
        path="*"
        element={
          <div className="page center">
            <h1>Page not found</h1>
            <Link to="/">Go home</Link>
          </div>
        }
      />
    </Routes>
  );
}
