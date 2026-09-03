import type { WatchSource } from 'vue'
import { normalizeApiError } from '~/lib/api'
import type { ApiRequestError } from '~/lib/api'

export function useClientData<T>(loader: () => Promise<T>, sources: WatchSource<unknown>[]) {
  const data = shallowRef<T>()
  const error = ref<ApiRequestError>()
  const pending = ref(true)
  let requestId = 0

  async function refresh() {
    const currentRequest = ++requestId
    pending.value = true
    error.value = undefined

    try {
      const response = await loader()
      if (currentRequest === requestId) data.value = response
    } catch (requestError) {
      if (currentRequest === requestId) {
        data.value = undefined
        error.value = normalizeApiError(requestError)
      }
    } finally {
      if (currentRequest === requestId) pending.value = false
    }
  }

  watch(sources, refresh, { immediate: import.meta.client })

  return {
    data,
    error,
    pending,
    refresh,
  }
}
