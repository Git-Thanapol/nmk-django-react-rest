import React from 'react'
import {BrowserRouter,Routes, Route, Navigate} from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import NotFound from './pages/NotFound'
import Home from './pages/Home'
import ProtectedRoute from './components/ProtectedRoute'

// import About from './pages/About'
// import Contact from './pages/Contact'
// import Navbar from './components/Navbar'
// import Footer from './components/Footer'

function Logout() {
  // Clear user session or token here
  // Redirect to login page
  localStorage.clear();
  return <Navigate to="/login" />;
}
// routes are declared directly in the main `Routes` below.
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path ="/" element = {<ProtectedRoute> <Home /> </ProtectedRoute> } />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/logout" element={<Logout />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
