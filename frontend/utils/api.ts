export interface ApiError {
  detail?: string
  message?: string
}

export function useApi() {
  const config = useRuntimeConfig()

  const request = <T>(path: string, options: Parameters<typeof $fetch>[1] = {}) => {
    return $fetch<T>(path, {
      baseURL: import.meta.server ? config.apiBaseUrl : config.public.apiBaseUrl,
      ...options,
    })
  }

  return { request }
}
