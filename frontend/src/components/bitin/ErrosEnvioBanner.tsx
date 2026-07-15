interface ErroEnvio {
  field: string
  code: string
  message: string
}

export default function ErrosEnvioBanner({ erros }: { erros: ErroEnvio[] }) {
  if (erros.length === 0) return null
  return (
    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
      <p className="text-sm font-medium text-red-700">Não foi possível enviar:</p>
      <ul className="mt-1.5 list-inside list-disc text-sm text-red-700">
        {erros.map((e, i) => (
          <li key={i}>{e.message}</li>
        ))}
      </ul>
    </div>
  )
}
