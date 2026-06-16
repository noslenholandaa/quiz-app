import { describe, it, expect, beforeEach } from 'vitest'

describe('handleApiError', () => {
  function handleApiError(err) {
    const messages = {
      400: 'Dados inválidos. Verifique as informações e tente novamente.',
      401: 'Sessão expirada. Faça login novamente.',
      403: 'Acesso negado. Você não tem permissão para esta ação.',
      404: 'Recurso não encontrado.',
      422: 'Dados inválidos. Verifique os campos e tente novamente.',
      429: 'Muitas requisições. Aguarde alguns segundos e tente novamente.',
      500: 'Erro interno do servidor. Tente novamente mais tarde.',
      502: 'Servidor temporariamente indisponível. Tente novamente mais tarde.',
      503: 'Serviço indisponível no momento. Tente novamente mais tarde.',
    }
    if (err.status && messages[err.status]) {
      return messages[err.status]
    }
    if (err.message === 'Failed to fetch' || err.message === 'NetworkError') {
      return 'Erro de conexão. Verifique sua internet e tente novamente.'
    }
    if (err.message?.includes('timeout') || err.message?.includes('timed out')) {
      return 'A requisição excedeu o tempo limite. Tente novamente.'
    }
    return err.message || 'Erro desconhecido. Tente novamente.'
  }

  it('should return 401 message for status 401', () => {
    const err = { status: 401, message: 'Unauthorized' }
    expect(handleApiError(err)).toBe('Sessão expirada. Faça login novamente.')
  })

  it('should return 403 message for status 403', () => {
    const err = { status: 403, message: 'Forbidden' }
    expect(handleApiError(err)).toBe('Acesso negado. Você não tem permissão para esta ação.')
  })

  it('should return 404 message for status 404', () => {
    const err = { status: 404, message: 'Not Found' }
    expect(handleApiError(err)).toBe('Recurso não encontrado.')
  })

  it('should return 429 message for status 429', () => {
    const err = { status: 429, message: 'Too Many Requests' }
    expect(handleApiError(err)).toBe('Muitas requisições. Aguarde alguns segundos e tente novamente.')
  })

  it('should return 500 message for status 500', () => {
    const err = { status: 500, message: 'Internal Server Error' }
    expect(handleApiError(err)).toBe('Erro interno do servidor. Tente novamente mais tarde.')
  })

  it('should return network error message for Failed to fetch', () => {
    const err = { message: 'Failed to fetch' }
    expect(handleApiError(err)).toBe('Erro de conexão. Verifique sua internet e tente novamente.')
  })

  it('should return network error message for NetworkError', () => {
    const err = { message: 'NetworkError' }
    expect(handleApiError(err)).toBe('Erro de conexão. Verifique sua internet e tente novamente.')
  })

  it('should return timeout message for timeout errors', () => {
    const err = { message: 'The request timed out' }
    expect(handleApiError(err)).toBe('A requisição excedeu o tempo limite. Tente novamente.')
  })

  it('should return fallback message for unknown error', () => {
    const err = { message: 'Algo estranho aconteceu' }
    expect(handleApiError(err)).toBe('Algo estranho aconteceu')
  })

  it('should return default message when no message', () => {
    const err = {}
    expect(handleApiError(err)).toBe('Erro desconhecido. Tente novamente.')
  })

  it('should prefer status code over message', () => {
    const err = { status: 403, message: 'Failed to fetch' }
    expect(handleApiError(err)).toBe('Acesso negado. Você não tem permissão para esta ação.')
  })
})
