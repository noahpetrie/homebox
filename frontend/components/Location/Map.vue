<script setup lang="ts">
  // Home fork: an interactive map of a location's photo. Sub-locations with a "Region" field
  // ("x,y,w,h" in percent of the photo) are drawn as outlined areas with their name and item
  // count; hovering highlights one, clicking shows what's in it beside the photo.
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";
  import { Button } from "@/components/ui/button";
  import { Badge } from "@/components/ui/badge";
  import { packTarget, packVersion, startPacking } from "~/composables/use-packing";
  import MdiPackageVariant from "~icons/mdi/package-variant";
  import MdiPackageVariantClosed from "~icons/mdi/package-variant-closed";
  import MdiArrowRight from "~icons/mdi/arrow-right";

  const REGION_FIELD = "Region";

  const props = defineProps<{ photoSrc: string; areas: EntitySummary[] }>();
  const emit = defineEmits<{ (e: "mapped", count: number): void }>();

  const api = useUserApi();

  type Area = {
    id: string;
    name: string;
    x: number;
    y: number;
    w: number;
    h: number;
    items: EntitySummary[];
    total: number;
  };
  const mapped = ref<Area[]>([]);
  const selectedId = ref<string | null>(null);
  const hoverId = ref<string | null>(null);

  function parseRegion(v?: string | null) {
    const n = (v ?? "").split(",").map(s => Number(s.trim()));
    return n.length === 4 && n.every(x => Number.isFinite(x)) ? { x: n[0]!, y: n[1]!, w: n[2]!, h: n[3]! } : null;
  }

  async function load() {
    const out: Area[] = [];
    await Promise.all(
      props.areas.map(async a => {
        const { data } = await api.items.get(a.id);
        const region = parseRegion(data?.fields?.find(f => f.name === REGION_FIELD)?.textValue);
        if (!region) return;
        const { data: list } = await api.items.getAll({ parentIds: [a.id], pageSize: 100 });
        out.push({ id: a.id, name: a.name, ...region, items: list?.items ?? [], total: list?.total ?? 0 });
      })
    );
    mapped.value = out.sort((p, q) => p.y - q.y || p.x - q.x);
    emit("mapped", out.length);
  }

  watch(() => props.areas.map(a => a.id).join(), load, { immediate: true });
  watch(packVersion, load);

  const selected = computed(() => mapped.value.find(a => a.id === selectedId.value) ?? null);
  const thumb = (it: EntitySummary) =>
    it.imageId ? api.authURL(`/entities/${it.id}/attachments/${it.thumbnailId || it.imageId}`) : "";
</script>

<template>
  <section v-if="mapped.length" class="mt-4 grid gap-4 md:grid-cols-5">
    <div class="md:col-span-3">
      <div class="relative mx-auto w-fit overflow-hidden rounded-lg border bg-card shadow-sm">
        <img :src="photoSrc" alt="" class="block max-h-[72vh] w-auto max-w-full select-none" draggable="false" />
        <button
          v-for="a in mapped"
          :key="a.id"
          type="button"
          class="absolute rounded-md border-2 text-left transition-colors focus:outline-none"
          :class="
            selectedId === a.id
              ? 'border-primary bg-primary/25 ring-2 ring-primary/40'
              : hoverId === a.id
                ? 'border-white bg-white/20'
                : 'border-white/70 bg-black/5 hover:border-white'
          "
          :style="{ left: `${a.x}%`, top: `${a.y}%`, width: `${a.w}%`, height: `${a.h}%` }"
          :aria-label="`${a.name}, ${a.total} items`"
          @mouseenter="hoverId = a.id"
          @mouseleave="hoverId = null"
          @click="selectedId = selectedId === a.id ? null : a.id"
        >
          <span
            class="absolute left-1 top-1 inline-flex max-w-[calc(100%-0.5rem)] items-center gap-1 truncate rounded bg-black/65 px-1.5 py-0.5 text-[11px] font-medium text-white"
          >
            {{ a.name }}
            <span class="rounded bg-white/25 px-1">{{ a.total }}</span>
          </span>
        </button>
      </div>
      <p class="mt-1.5 text-center text-xs text-muted-foreground">Click a compartment to see what's in it.</p>
    </div>

    <div class="md:col-span-2">
      <div class="h-full rounded-lg border bg-card p-4 shadow-sm">
        <template v-if="selected">
          <div class="flex items-center gap-2">
            <h3 class="grow truncate text-lg font-semibold">{{ selected.name }}</h3>
            <Badge>{{ selected.total }}</Badge>
          </div>
          <ul v-if="selected.items.length" class="mt-3 flex max-h-80 flex-col gap-1 overflow-y-auto">
            <li v-for="it in selected.items" :key="it.id">
              <NuxtLink :to="`/item/${it.id}`" class="flex items-center gap-3 rounded-md p-1.5 hover:bg-accent/60">
                <img v-if="thumb(it)" :src="thumb(it)" alt="" class="size-9 shrink-0 rounded bg-muted object-contain" />
                <div v-else class="flex size-9 shrink-0 items-center justify-center rounded bg-muted">
                  <MdiPackageVariant class="size-4 opacity-50" />
                </div>
                <span class="truncate text-sm">{{ it.name }}</span>
              </NuxtLink>
            </li>
          </ul>
          <p v-else class="mt-3 text-sm text-muted-foreground">Nothing here yet.</p>
          <div class="mt-4 flex flex-wrap gap-2">
            <Button size="sm" as-child>
              <NuxtLink :to="`/location/${selected.id}`">Open <MdiArrowRight /></NuxtLink>
            </Button>
            <Button
              v-if="packTarget?.id !== selected.id"
              size="sm"
              variant="outline"
              @click="startPacking({ id: selected.id, name: selected.name })"
            >
              <MdiPackageVariantClosed /> Pack items here
            </Button>
          </div>
        </template>
        <template v-else>
          <h3 class="text-lg font-semibold">What's where</h3>
          <ul class="mt-3 flex flex-col gap-1">
            <li v-for="a in mapped" :key="a.id">
              <button
                type="button"
                class="flex w-full items-center gap-2 rounded-md p-1.5 text-left text-sm hover:bg-accent/60"
                :class="hoverId === a.id ? 'bg-accent/60' : ''"
                @mouseenter="hoverId = a.id"
                @mouseleave="hoverId = null"
                @click="selectedId = a.id"
              >
                <span class="grow truncate font-medium">{{ a.name }}</span>
                <span class="truncate text-xs text-muted-foreground">
                  {{
                    a.items
                      .slice(0, 3)
                      .map(i => i.name)
                      .join(", ") || "empty"
                  }}{{ a.total > 3 ? "…" : "" }}
                </span>
                <Badge variant="secondary">{{ a.total }}</Badge>
              </button>
            </li>
          </ul>
        </template>
      </div>
    </div>
  </section>
</template>
