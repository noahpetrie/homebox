<script setup lang="ts">
  // Home fork: "Where it is" on an item page. When the item's location is an area drawn on its
  // parent's photo (a compartment with a "Region" field), show that photo with the area
  // highlighted, so you can see which compartment to open.
  import type { EntityPath } from "~~/lib/api/types/data-contracts";

  const props = defineProps<{ locationId: string; path?: EntityPath[] }>();

  const api = useUserApi();

  const view = computedAsync(async () => {
    const { data: loc } = await api.items.get(props.locationId);
    const raw = loc?.fields?.find(f => f.name === "Region")?.textValue ?? "";
    const n = raw.split(",").map(s => Number(s.trim()));
    if (!loc?.parent || n.length !== 4 || !n.every(x => Number.isFinite(x))) return null;
    const { data: parent } = await api.items.get(loc.parent.id);
    const photos = (parent?.attachments ?? []).filter(a => a.type === "photo");
    const main = photos.find(a => a.primary) ?? photos[0];
    if (!parent || !main) return null;
    return {
      src: api.authURL(`/entities/${parent.id}/attachments/${main.id}`),
      parentId: parent.id,
      parentName: parent.name,
      name: loc.name,
      x: n[0]!,
      y: n[1]!,
      w: n[2]!,
      h: n[3]!,
    };
  }, null);

  // the path from the room down, e.g. Office › IKEA ALEX Drawer Unit › Drawer 1 › Top left
  const trail = computed(() => {
    const all = props.path ?? [];
    const end = all.findIndex(p => p.id === props.locationId);
    return end >= 0 ? all.slice(0, end + 1) : all;
  });
</script>

<template>
  <div v-if="view" class="flex items-center gap-4 rounded-lg border bg-card p-3 shadow-sm">
    <NuxtLink
      :to="`/location/${view.parentId}`"
      class="relative block w-24 shrink-0 overflow-hidden rounded-md sm:w-28"
      :aria-label="`${view.name} in ${view.parentName}`"
    >
      <img :src="view.src" alt="" class="block w-full" />
      <span
        class="absolute rounded-sm border-2 border-primary bg-primary/40 ring-2 ring-white/70"
        :style="{ left: `${view.x}%`, top: `${view.y}%`, width: `${view.w}%`, height: `${view.h}%` }"
      />
    </NuxtLink>
    <div class="min-w-0">
      <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">Where it is</p>
      <p class="text-lg font-semibold leading-tight">{{ view.name }}</p>
      <p class="text-sm text-muted-foreground">
        <template v-for="(p, i) in trail" :key="p.id">
          <NuxtLink :to="`/location/${p.id}`" class="hover:underline">{{ p.name }}</NuxtLink
          ><span v-if="i < trail.length - 1"> › </span>
        </template>
      </p>
    </div>
  </div>
</template>
