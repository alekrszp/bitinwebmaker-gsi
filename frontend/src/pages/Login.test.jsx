import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../context/AuthContext'
import { ThemeProvider } from '../context/ThemeContext'
import { api } from '../lib/api'
import Login from './Login'

// api é mockado inteiro -- este é um smoke test de UI/UX (o que a tela redesenhada promete:
// campos com ícone, mostrar/esconder senha, erro visível, tema), não um teste de integração
// contra o backend real (isso já é coberto pelos testes Python + validação manual).
vi.mock('../lib/api', () => ({
  api: { post: vi.fn(), get: vi.fn() },
  getToken: vi.fn(() => null),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}))

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <ThemeProvider>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  it('renderiza os campos de e-mail e senha e o botão de entrar', () => {
    renderLogin()
    expect(screen.getByLabelText('E-mail')).toBeInTheDocument()
    expect(screen.getByLabelText('Senha')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
  })

  it('alterna a visibilidade da senha', async () => {
    const user = userEvent.setup()
    renderLogin()
    const senha = screen.getByLabelText('Senha')
    expect(senha).toHaveAttribute('type', 'password')

    await user.click(screen.getByLabelText('Mostrar senha'))
    expect(senha).toHaveAttribute('type', 'text')

    await user.click(screen.getByLabelText('Esconder senha'))
    expect(senha).toHaveAttribute('type', 'password')
  })

  it('mostra erro estruturado quando o login falha', async () => {
    api.post.mockRejectedValueOnce({ response: { data: { detail: 'E-mail ou senha incorretos' } } })
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('E-mail'), 'usuario@example.com')
    await user.type(screen.getByLabelText('Senha'), 'senhaerrada')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha incorretos')
  })

  it('alterna entre tema claro e escuro', async () => {
    const user = userEvent.setup()
    renderLogin()
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    await user.click(screen.getByLabelText('Mudar pro tema escuro'))
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    await user.click(screen.getByLabelText('Mudar pro tema claro'))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
