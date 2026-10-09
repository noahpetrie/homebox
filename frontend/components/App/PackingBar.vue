<script setup lang="ts">
  // Home fork: shown on every page while packing mode is on (see composables/use-packing.ts).
  import { Button } from "@/components/ui/button";
  import { DialogID, useDialog } from "~/components/ui/dialog-provider/utils";
  import { packedLog, packTarget, stopPacking } from "~/composables/use-packing";
  import MdiPackageVariantClosed from "~icons/mdi/package-variant-closed";
  import MdiCameraOutline from "~icons/mdi/camera-outline";

  const { openDialog } = useDialog();
  const recent = computed(() => packedLog.value.slice(0, 3));
</script>

<template>
  <div
    v-if="packTarget"
    class="sticky top-[var(--header-height-mobile)] z-10 border-b border-primary/30 bg-primary/10 px-3 py-2 sm:top-[var(--header-height)]"
    role="status"
  >
    <div class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-2">
      <MdiPackageVariantClosed class="size-5 shrink-0 text-primary" />
      <div class="min-w-0 grow">
        <p class="text-sm font-medium">
          Packing into
          <NuxtLink :to="`/location/${packTarget.id}`" class="underline">{{ packTarget.name }}</NuxtLink>
          · {{ packedLog.length }} added
        </p>
        <p class="truncate text-xs text-muted-foreground">
          <template v-if="recent.length">Last: {{ recent.map(r => r.name).join(" · ") }}</template>
          <template v-else>Scan each item with the barcode scanner, or use the camera.</template>
        </p>
      </div>
      <Button size="sm" variant="outline" class="h-8" @click="openDialog(DialogID.Scanner)">
        <MdiCameraOutline class="mr-1 size-4" /> Camera
      </Button>
      <Button size="sm" class="h-8" @click="stopPacking">Done</Button>
    </div>
  </div>
</template>
