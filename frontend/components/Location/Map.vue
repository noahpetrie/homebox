<script setup lang="ts">
  // Home fork: an interactive map of a location's photo. Sub-locations with a "Region" field
  // ("x,y,w,h" in percent of the photo) are drawn as outlined areas showing thumbnails of what's
  // in them. Beside the map, a contents list has a section per area (plus anything loose in the
  // location itself); hovering either side highlights the other, clicking an area scrolls to it.
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";
  import { Button } from "@/components/ui/button";
  import { Badge } from "@/components/ui/badge";
  import { packTarget, packVersion, startPacking } from "~/composables/use-packing";
  import MdiPackageVariant from "~icons/mdi/package-variant";
  import MdiPackageVariantClosed from "~icons/mdi/package-variant-closed";
  import MdiArrowRight from "~icons/mdi/arrow-right";

  const REGION_FIELD = "Region";

  const props = defineProps<{
    photoSrc: string;
    areas: EntitySummary[];
    /** items directly in this location (not in any area) */
    loose?: EntitySummary[];
    locationName?: string;
  }>();
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
  const activeId = ref<string | null>(null); // hovered on either side
  const selectedId = ref<string | null>(null); // clicked on the map
  const sectionEls: Record<string, HTMLElement | null> = {};

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
    // reading order: rows top to bottom, then left to right
    mapped.value = out.sort((p, q) => (Math.abs(p.y - q.y) > 8 ? p.y - q.y : p.x - q.x));
    emit("mapped", out.length);
  }

  watch(() => props.areas.map(a => a.id).join(), load, { immediate: true });
  watch(packVersion, load);

  function selectArea(id: string) {
    selectedId.value = selectedId.value === id ? null : id;
    if (selectedId.value) sectionEls[id]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function setSectionEl(id: string, el: unknown) {
    sectionEls[id] = (el as HTMLElement | null) ?? null;
  }

  const thumb = (it: EntitySummary) =>
    it.imageId ? api.authURL(`/entities/${it.id}/attachments/${it.thumbnailId || it.imageId}`) : "";

  // how many thumbnails fit in an area: roughly one per 7.5% x 8% of the photo
  const capacity = (a: Area) => Math.max(1, Math.floor(a.w / 7.5) * Math.max(1, Math.floor((a.h - 6) / 8)));
  const shown = (a: Area) => a.items.slice(0, a.total > capacity(a) ? capacity(a) - 1 : capacity(a));
  const highlight = (id: string) => activeId.value === id || selectedId.value === id;
</script>

<template>
  <section v-if="mapped.length" class="mt-4 grid items-start gap-4 lg:grid-cols-5">
    <!-- the map -->
    <div class="lg:col-span-3">
      <div class="relative mx-auto w-fit overflow-hidden rounded-lg border bg-card shadow-sm">
        <img :src="photoSrc" alt="" class="block max-h-[68vh] w-auto max-w-full select-none" draggable="false" />
        <div
          v-for="a in mapped"
          :key="a.id"
          role="button"
          tabindex="0"
          class="absolute flex cursor-pointer flex-col rounded-md border-2 p-1 transition-colors"
          :class="
            highlight(a.id)
              ? 'border-primary bg-primary/20 ring-2 ring-primary/40'
              : 'border-white/60 hover:border-white'
          "
          :style="{ left: `${a.x}%`, top: `${a.y}%`, width: `${a.w}%`, height: `${a.h}%` }"
          :aria-label="`${a.name}, ${a.total} items`"
          @mouseenter="activeId = a.id"
          @mouseleave="activeId = null"
          @click="selectArea(a.id)"
          @keydown.enter="selectArea(a.id)"
        >
          <span
            class="inline-flex max-w-full items-center gap-1 self-start truncate rounded bg-black/65 px-1.5 py-0.5 text-[11px] font-medium text-white"
          >
            {{ a.name }} <span class="rounded bg-white/25 px-1">{{ a.total }}</span>
          </span>
          <!-- what's in it -->
          <div class="mt-1 flex min-h-0 flex-wrap content-start gap-1 overflow-hidden">
            <NuxtLink
              v-for="it in shown(a)"
              :key="it.id"
              :to="`/item/${it.id}`"
              :title="it.name"
              class="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded bg-white/90 shadow-sm ring-1 ring-black/10 hover:ring-2 hover:ring-primary sm:size-11"
              @click.stop
            >
              <img v-if="thumb(it)" :src="thumb(it)" alt="" class="max-h-full max-w-full object-contain p-0.5" />
              <MdiPackageVariant v-else class="size-4 opacity-50" />
            </NuxtLink>
            <span
              v-if="a.total > shown(a).length"
              class="flex size-9 shrink-0 items-center justify-center rounded bg-black/60 text-xs font-medium text-white sm:size-11"
            >
              +{{ a.total - shown(a).length }}
            </span>
          </div>
        </div>
      </div>
      <p class="mt-1.5 text-center text-xs text-muted-foreground">
        Click a compartment to jump to its contents, or a thumbnail to open that item.
      </p>
    </div>

    <!-- contents, one section per area -->
    <div class="lg:col-span-2">
      <div class="flex max-h-[72vh] flex-col overflow-y-auto rounded-lg border bg-card shadow-sm">
        <div
          v-for="a in mapped"
          :key="a.id"
          :ref="el => setSectionEl(a.id, el)"
          class="border-b p-3 transition-colors last:border-b-0"
          :class="highlight(a.id) ? 'bg-primary/10' : ''"
          @mouseenter="activeId = a.id"
          @mouseleave="activeId = null"
        >
          <div class="flex items-center gap-2">
            <button type="button" class="grow text-left font-semibold hover:underline" @click="selectArea(a.id)">
              {{ a.name }}
            </button>
            <Badge :variant="a.total ? 'default' : 'secondary'">{{ a.total }}</Badge>
            <Button size="sm" variant="ghost" class="h-7 px-2" as-child>
              <NuxtLink :to="`/location/${a.id}`" :aria-label="`Open ${a.name}`"><MdiArrowRight /></NuxtLink>
            </Button>
          </div>
          <ul v-if="a.items.length" class="mt-1.5 flex flex-col">
            <li v-for="it in a.items" :key="it.id">
              <NuxtLink :to="`/item/${it.id}`" class="flex items-center gap-2.5 rounded-md p-1 hover:bg-accent/60">
                <img v-if="thumb(it)" :src="thumb(it)" alt="" class="size-8 shrink-0 rounded bg-muted object-contain" />
                <span v-else class="flex size-8 shrink-0 items-center justify-center rounded bg-muted">
                  <MdiPackageVariant class="size-4 opacity-50" />
                </span>
                <span class="text-sm leading-snug">{{ it.name }}</span>
              </NuxtLink>
            </li>
          </ul>
          <div v-else class="mt-1 flex items-center gap-2">
            <span class="text-sm text-muted-foreground">Empty</span>
            <Button
              v-if="packTarget?.id !== a.id"
              size="sm"
              variant="link"
              class="h-auto p-0 text-xs"
              @click="startPacking({ id: a.id, name: a.name })"
            >
              <MdiPackageVariantClosed class="mr-1 size-3.5" /> Pack items here
            </Button>
          </div>
        </div>

        <!-- things sitting directly in this location -->
        <div v-if="loose && loose.length" class="border-t-2 p-3">
          <div class="flex items-center gap-2">
            <span class="grow font-semibold">Loose in {{ locationName || "here" }}</span>
            <Badge>{{ loose.length }}</Badge>
          </div>
          <ul class="mt-1.5 flex flex-col">
            <li v-for="it in loose" :key="it.id">
              <NuxtLink :to="`/item/${it.id}`" class="flex items-center gap-2.5 rounded-md p-1 hover:bg-accent/60">
                <img v-if="thumb(it)" :src="thumb(it)" alt="" class="size-8 shrink-0 rounded bg-muted object-contain" />
                <span v-else class="flex size-8 shrink-0 items-center justify-center rounded bg-muted">
                  <MdiPackageVariant class="size-4 opacity-50" />
                </span>
                <span class="text-sm leading-snug">{{ it.name }}</span>
              </NuxtLink>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
