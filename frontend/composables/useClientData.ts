import type { WatchSource } from 'vue'
import { getApiErrorMessage } from '~/lib/api'

export function useClientData<T>(loader: () => Promise<T>, sources: WatchSource<unknown>[]) {
  const data = shallowRef<T>()
  const error = ref<string>()
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
        error.value = getApiErrorMessage(requestError)
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
