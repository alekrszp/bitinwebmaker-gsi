import { useTheme } from '../context/ThemeContext'

// Botão sol/lua reutilizável -- extraído de Layout.jsx pra também aparecer no login (a
// escolha de tema deve valer antes de autenticar, não só depois). `className` deixa cada
// lugar ajustar a cor de contraste (branco sobre navy no cabeçalho, tom neutro no login).
export default function ThemeToggle({ className = '' }) {
  const { theme, toggleTheme } = useTheme()
  const escuro = theme === 'dark'
  return (
    <button
      type="button"
      onClick={toggleTheme}
      title={escuro ? 'Mudar pro tema claro' : 'Mudar pro tema escuro'}
      aria-label={escuro ? 'Mudar pro tema claro' : 'Mudar pro tema escuro'}
      className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${className}`}
    >
      {escuro ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 1020.354 15.354z" />
        </svg>
      )}
    </button>
  )
}
