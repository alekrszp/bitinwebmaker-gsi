import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="p-6 text-center text-gray-500">Carregando...</div>
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}
