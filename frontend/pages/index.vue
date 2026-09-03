<script setup lang="ts">
interface HealthResponse {
  status: 'ok'
  service: string
  message: string
}

const { request } = useApi()
const { data, error, pending, refresh } = await useAsyncData('api-health', () =>
  request<HealthResponse>('/api/health'),
)
</script>

<template>
  <main class="min-h-screen overflow-hidden">
    <div class="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-8 lg:px-12 lg:py-10">
      <header class="flex items-center justify-between border-b border-black/10 pb-6">
        <div class="flex items-center gap-3">
          <span class="grid size-9 place-items-center rounded-full bg-[var(--ink)] text-sm font-bold text-[var(--lime)]">FT</span>
          <span class="font-mono text-xs font-medium uppercase tracking-[0.2em]">Fast / Nuxt</span>
        </div>
        <span class="font-mono text-xs uppercase tracking-widest text-black/50">Starter 001</span>
      </header>

      <section class="grid flex-1 items-center gap-12 py-16 lg:grid-cols-[1.15fr_0.85fr] lg:gap-24">
        <div>
          <p class="mb-6 font-mono text-xs uppercase tracking-[0.25em] text-black/50">Full-stack workspace</p>
          <h1 class="max-w-3xl text-5xl font-extrabold leading-[0.98] tracking-[-0.06em] sm:text-7xl">
            A clean line between <span class="text-[#8aa735]">idea</span> and interface.
          </h1>
          <p class="mt-8 max-w-xl text-lg leading-8 text-black/60">
            A minimal FastAPI backend and Nuxt frontend, connected through one typed request layer and ready to grow with your product.
          </p>
          <div class="mt-10 flex flex-wrap gap-3">
            <UButton to="https://fastapi.tiangolo.com" target="_blank" size="lg" color="neutral" label="Explore FastAPI" trailing-icon="i-lucide-arrow-up-right" />
            <UButton to="https://nuxt.com" target="_blank" size="lg" variant="outline" color="neutral" label="Read Nuxt docs" trailing-icon="i-lucide-arrow-up-right" />
          </div>
        </div>

        <aside class="relative rounded-3xl bg-[var(--ink)] p-7 text-white shadow-2xl shadow-black/10 sm:p-9">
          <div class="absolute -right-3 -top-3 size-16 rounded-full border-[10px] border-[var(--paper)] bg-[var(--lime)]" />
          <div class="flex items-center justify-between border-b border-white/15 pb-6">
            <span class="font-mono text-xs uppercase tracking-[0.2em] text-white/50">Connection check</span>
            <UBadge v-if="data" color="success" variant="subtle" label="Online" />
            <UBadge v-else-if="pending" color="warning" variant="subtle" label="Checking" />
            <UBadge v-else color="error" variant="subtle" label="Offline" />
          </div>

          <div class="py-12">
            <p class="font-mono text-xs uppercase tracking-[0.2em] text-white/40">GET /api/health</p>
            <p v-if="data" class="mt-5 text-2xl font-semibold tracking-tight">{{ data.message }}</p>
            <p v-else-if="pending" class="mt-5 text-2xl font-semibold tracking-tight text-white/60">Talking to the API...</p>
            <p v-else class="mt-5 text-2xl font-semibold tracking-tight text-red-300">The API could not be reached.</p>
          </div>

          <div class="flex items-center justify-between border-t border-white/15 pt-6">
            <span class="font-mono text-xs text-white/40">Typed through useApi&lt;T&gt;</span>
            <UButton v-if="error" variant="link" color="primary" label="Retry" @click="() => refresh()" />
            <span v-else class="font-mono text-xs text-[var(--lime)]">200 / OK</span>
          </div>
        </aside>
      </section>

      <footer class="flex flex-col gap-3 border-t border-black/10 pt-5 text-xs text-black/45 sm:flex-row sm:items-center sm:justify-between">
        <span>TypeScript on the client. Python on the server.</span>
        <span class="font-mono">localhost:3000 → localhost:8000</span>
      </footer>
    </div>
  </main>
</template>
