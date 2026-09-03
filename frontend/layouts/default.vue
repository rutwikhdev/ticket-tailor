<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'

const route = useRoute()
const mobileNavigationOpen = ref(false)

const navigationItems = computed<NavigationMenuItem[]>(() => {
  const period = typeof route.query.period === 'string' ? route.query.period : undefined
  const to = (path: string) => ({ path, query: period ? { period } : {} })

    return [
    {
      label: 'Overview',
      icon: 'i-lucide-house',
      to: to('/'),
      exact: true,
    },
    {
      label: 'Transactions',
      icon: 'i-lucide-receipt-text',
      to: to('/transactions'),
    },
    {
      label: 'Payouts',
      icon: 'i-lucide-landmark',
      to: to('/payouts'),
    },
  ]
})

watch(() => route.path, () => {
  mobileNavigationOpen.value = false
})
</script>

<template>
  <div class="min-h-dvh bg-default text-default">
    <aside class="fixed inset-y-0 left-0 hidden w-64 border-r border-default bg-elevated/25 lg:flex lg:flex-col">
      <div class="flex h-16 items-center gap-3 px-5">
        <span class="grid size-8 place-items-center rounded-md bg-primary">
          <UIcon name="i-lucide-ticket" class="size-4 text-inverted" />
        </span>
        <div class="leading-tight">
          <p class="text-sm font-semibold text-highlighted">Ticket Tailor</p>
          <p class="text-xs text-muted">Revenue</p>
        </div>
      </div>

      <nav aria-label="Primary" class="flex-1 px-3 py-4">
        <UNavigationMenu
          :items="navigationItems"
          orientation="vertical"
          :ui="{ link: 'py-2' }"
        />
      </nav>

      <div class="border-t border-default px-6 py-5">
        <div class="flex items-center gap-2 text-xs text-muted">
          <span class="size-1.5 rounded-full bg-primary" />
          Live financial reporting
        </div>
      </div>
    </aside>

    <header class="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-default bg-default/80 px-4 backdrop-blur lg:hidden">
      <div class="flex items-center gap-2.5">
        <span class="grid size-8 place-items-center rounded-md bg-primary">
          <UIcon name="i-lucide-ticket" class="size-4 text-inverted" />
        </span>
        <span class="text-sm font-semibold text-highlighted">Revenue</span>
      </div>
      <UButton
        icon="i-lucide-menu"
        color="neutral"
        variant="ghost"
        aria-label="Open navigation"
        @click="mobileNavigationOpen = true"
      />
    </header>

    <USlideover
      v-model:open="mobileNavigationOpen"
      side="left"
      title="Ticket Tailor Revenue"
      description="Financial reporting"
      :ui="{ overlay: 'z-40', content: 'z-50 max-w-xs', body: 'p-3 sm:p-3' }"
    >
      <template #body>
        <nav aria-label="Mobile primary">
          <UNavigationMenu
            :items="navigationItems"
            orientation="vertical"
            :ui="{ link: 'py-2.5' }"
          />
        </nav>
      </template>
    </USlideover>

    <main class="min-w-0 lg:pl-64">
      <div class="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6">
        <slot />
      </div>
    </main>
  </div>
</template>
