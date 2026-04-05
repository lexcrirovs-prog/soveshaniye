import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Calls from './pages/Calls'
import CallDetail from './pages/CallDetail'
import Employees from './pages/Employees'
import EmployeeDetail from './pages/EmployeeDetail'
import Scripts from './pages/Scripts'
import Exports from './pages/Exports'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/calls" element={<Calls />} />
        <Route path="/calls/:id" element={<CallDetail />} />
        <Route path="/employees" element={<Employees />} />
        <Route path="/employees/:id" element={<EmployeeDetail />} />
        <Route path="/scripts" element={<Scripts />} />
        <Route path="/exports" element={<Exports />} />
      </Routes>
    </Layout>
  )
}
