import { BrowserRouter, Routes, Route } from "react-router-dom";

import Landing from "./pages/Landing/Landing";
import Login from "./pages/Auth/Login";
import Signup from "./pages/Auth/Signup";
import Projects from "./pages/Projects/Projects";
import Dashboard from "./pages/Dashboard/Dashboard";
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/projects" element={<Projects />} />
        <Route
          path="/projects/:projectId"
          element={<Dashboard />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;