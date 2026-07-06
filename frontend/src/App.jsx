import { Link, Route, Routes } from "react-router-dom";
import CallBanner from "./components/CallBanner";
import { useCall } from "./context/CallProvider";
import CallPage from "./pages/CallPage";
import AdminPage from "./pages/AdminPage";

function AppShell() {
  const { isLive } = useCall();

  return (
    <>
      {isLive && <CallBanner />}
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
    </>
  );
}

export default function App() {
  return <AppShell />;
}
