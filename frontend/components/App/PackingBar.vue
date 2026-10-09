<script setup lang="ts">
  // Home fork: shown on every page while packing mode is on (see composables/use-packing.ts).
  // Besides scanning, things without a barcode can be found by name and packed, or created
  // straight into the box.
  import { Button } from "@/components/ui/button";
  import { Input } from "@/components/ui/input";
  import { DialogID, useDialog } from "~/components/ui/dialog-provider/utils";
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";
  import { packedLog, packItem, packTarget, stopPacking } from "~/composables/use-packing";
  import MdiPackageVariantClosed from "~icons/mdi/package-variant-closed";
  import MdiPackageVariant from "~icons/mdi/package-variant";
  import MdiCameraOutline from "~icons/mdi/camera-outline";
  import MdiMagnify from "~icons/mdi/magnify";
  import MdiPlus from "~icons/mdi/plus";

  const api = useUserApi();
  const { openDialog } = useDialog();
  const recent = computed(() => packedLog.value.slice(0, 3));

  const query = ref("");
  const results = ref<EntitySummary[]>([]);
  const searching = ref(false);
  const search = useDebounceFn(async (q: string) => {
    if (!q.trim()) {
      results.value = [];
      return;
    }
    searching.value = true;
    const { data } = await api.items.getAll({ q: q.trim(), pageSize: 8 });
    // only things that aren't already in the box
    results.value = (data?.items ?? []).filter(it => it.parent?.id !== packTarget.value?.id);
    searching.value = false;
  }, 250);
  watch(query, q => search(q));

  async function pick(item: EntitySummary) {
    query.value = "";
    results.value = [];
    await packItem(api, item);
  }

  function newItem() {
    openDialog(DialogID.CreateEntity, { params: { baseType: "item" } });
  }

  const thumb = (it: EntitySummary) =>
    it.imageId ? api.authURL(`/entities/${it.id}/attachments/${it.thumbnailId || it.imageId}`) : "";
</script>

<template>
  <div
    v-if="packTarget"
    class="sticky top-[var(--header-height-mobile)] z-10 border-b border-primary/30 bg-primary/10 px-3 py-2 sm:top-[var(--header-height)]"
    role="status"
  >
    <div class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-2">
      <MdiPackageVariantClosed class="size-5 shrink-0 text-primary" />
      <div class="min-w-0 grow basis-48">
        <p class="text-sm font-medium">
          Packing into
          <NuxtLink :to="`/location/${packTarget.id}`" class="underline">{{ packTarget.name }}</NuxtLink>
          · {{ packedLog.length }} added
        </p>
        <p class="truncate text-xs text-muted-foreground">
          <template v-if="recent.length">Last: {{ recent.map(r => r.name).join(" · ") }}</template>
          <template v-else>Scan barcodes or item labels, or find things by name.</template>
        </p>
      </div>

      <!-- find something without a barcode -->
      <div class="relative w-full sm:w-64">
        <MdiMagnify class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 opacity-60" />
        <Input
          v-model="query"
          type="search"
          placeholder="Add by name…"
          class="h-8 bg-background pl-8"
          @keydown.esc="query = ''"
        />
        <div
          v-if="query.trim()"
          class="absolute inset-x-0 top-9 z-30 max-h-80 overflow-y-auto rounded-md border bg-popover p-1 shadow-md"
        >
          <button
            v-for="it in results"
            :key="it.id"
            type="button"
            class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent"
            @click="pick(it)"
          >
            <img v-if="thumb(it)" :src="thumb(it)" alt="" class="size-8 shrink-0 rounded bg-muted object-contain" />
            <span v-else class="flex size-8 shrink-0 items-center justify-center rounded bg-muted">
              <MdiPackageVariant class="size-4 opacity-50" />
            </span>
            <span class="min-w-0 grow">
              <span class="block truncate">{{ it.name }}</span>
              <span v-if="it.parent" class="block truncate text-xs text-muted-foreground">{{ it.parent.name }}</span>
            </span>
          </button>
          <p v-if="!searching && !results.length" class="px-2 py-1.5 text-sm text-muted-foreground">Nothing found.</p>
          <button
            type="button"
            class="mt-1 flex w-full items-center gap-2 rounded-sm border-t px-2 py-1.5 text-left text-sm hover:bg-accent"
            @click="
              query = '';
              newItem();
            "
          >
            <MdiPlus class="size-4" /> New item in {{ packTarget.name }}
          </button>
        </div>
      </div>

      <Button size="sm" variant="outline" class="h-8" @click="newItem"><MdiPlus class="mr-1 size-4" /> New item</Button>
      <Button size="sm" variant="outline" class="h-8" @click="openDialog(DialogID.Scanner)">
        <MdiCameraOutline class="mr-1 size-4" /> Camera
      </Button>
      <Button size="sm" class="h-8" @click="stopPacking">Done</Button>
    </div>
  </div>
</template>
