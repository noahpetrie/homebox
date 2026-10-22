<script setup lang="ts">
  import { useI18n } from "vue-i18n";
  import { DialogID, type NoParamDialogIDs } from "@/components/ui/dialog-provider/utils";
  import {
    CommandDialog,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
    CommandSeparator,
  } from "~/components/ui/command";
  import { Shortcut } from "~/components/ui/shortcut";
  import { useDialog, useDialogHotkey } from "~/components/ui/dialog-provider";
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";
  import MdiMapMarkerOutline from "~icons/mdi/map-marker-outline";

  export type QuickMenuAction =
    | { text: string; href: string; type: "navigate" }
    | { text: string; dialogId: DialogID; shortcut: string; type: "create"; id?: number };

  const props = defineProps({
    actions: {
      type: Array as PropType<QuickMenuAction[]>,
      required: false,
      default: () => [],
    },
  });

  const { t } = useI18n();
  const { closeDialog, openDialog, activeDialog } = useDialog();

  useDialogHotkey(DialogID.QuickMenu, { code: "KeyK", mod: true });

  // Home fork: typing searches items and locations (name, author, ISBN, … as on the search page)
  const api = useUserApi();
  const query = ref("");
  const results = ref<EntitySummary[]>([]);
  // the query the shown results belong to; while it differs from what's typed a search is under way
  const resultsFor = ref("");
  const searching = computed(() => !!query.value.trim() && resultsFor.value !== query.value.trim());
  const search = useDebounceFn(async (q: string) => {
    if (!q) return;
    const { data } = await api.items.getAll({ q, pageSize: 8 });
    if (query.value.trim() !== q) return; // typed on since; a newer search will answer
    results.value = data?.items ?? [];
    resultsFor.value = q;
  }, 120);
  watch(query, q => {
    if (!q.trim()) {
      results.value = [];
      resultsFor.value = "";
    }
    search(q.trim());
  });
  // start empty each time the menu opens
  watch(activeDialog, d => {
    if (d === DialogID.QuickMenu) {
      query.value = "";
      results.value = [];
      resultsFor.value = "";
    }
  });

  const flatLocations = useFlatLocations();
  const pathOf = (p: { id: string; name: string }) =>
    flatLocations.value.find(l => l.id === p.id)?.treeString?.replace(/ > /g, " › ") || p.name;
  // locations are already loaded for the paths above, so they're matched here by name, instantly
  const locationMatches = computed(() => {
    const q = query.value.trim().toLowerCase();
    if (!q) return [];
    return flatLocations.value
      .filter(l => l.name.toLowerCase().includes(q))
      .sort((a, b) => Number(!a.name.toLowerCase().startsWith(q)) - Number(!b.name.toLowerCase().startsWith(q)))
      .slice(0, 5);
  });
  const parentPath = (treeString?: string) => treeString?.split(" > ").slice(0, -1).join(" › ") ?? "";

  const thumb = (it: EntitySummary) =>
    it.imageId ? api.authURL(`/entities/${it.id}/attachments/${it.thumbnailId || it.imageId}`) : "";

  // the menu's built-in filter is off (it remembers each row's text from when the row first
  // appeared, which hid search results as you kept typing), so actions are filtered here
  const matches = (text: string) =>
    !query.value.trim() || text.toLowerCase().includes(query.value.trim().toLowerCase());
  const createActions = computed(() => props.actions.filter(a => a.type === "create" && matches(a.text)));
  const navActions = computed(() => props.actions.filter(a => a.type === "navigate" && matches(a.text)));
  const showScanner = computed(() => matches(t("menu.scanner")));

  function open(it: EntitySummary) {
    closeDialog(DialogID.QuickMenu);
    query.value = "";
    navigateTo(`/${it.entityType?.isLocation ? "location" : "item"}/${it.id}`);
  }
</script>

<template>
  <CommandDialog :dialog-id="DialogID.QuickMenu" ignore-filter>
    <CommandInput
      placeholder="Search items, or pick an action…"
      @input="(e: Event) => (query = (e.target as HTMLInputElement).value)"
      @keydown="
        (e: KeyboardEvent) => {
          // number keys pick an action only before anything is typed, so '1984' can be searched
          const item = query
            ? undefined
            : props.actions.filter(item => 'shortcut' in item).find(item => item.shortcut === e.key);
          if (item) {
            e.preventDefault();
            if (item.dialogId === DialogID.CreateEntity) {
              if (item.id === 0) {
                openDialog(DialogID.CreateEntity, { params: { baseType: 'item' } });
              } else if (item.id === 1) {
                openDialog(DialogID.CreateEntity, { params: { baseType: 'location' } });
              }
            } else {
              openDialog(item.dialogId as NoParamDialogIDs);
            }
          }
          // if esc is pressed, close the dialog
          if (e.key === 'Escape') {
            e.preventDefault();
            closeDialog(DialogID.QuickMenu);
          }
        }
      "
    />
    <!-- fixed height, so the menu doesn't shrink and grow while typing -->
    <CommandList class="h-[300px]">
      <CommandSeparator />
      <CommandEmpty v-if="!searching">{{ t("components.quick_menu.no_results") }}</CommandEmpty>
      <!-- until the first results arrive: placeholder rows where they will appear -->
      <CommandGroup v-if="locationMatches.length" heading="Locations">
        <CommandItem
          v-for="l in locationMatches"
          :key="l.id"
          :value="`location-${l.id}`"
          class="gap-3"
          @select="
            (e: Event) => {
              e.preventDefault();
              closeDialog(DialogID.QuickMenu);
              query = '';
              navigateTo(`/location/${l.id}`);
            }
          "
        >
          <div class="flex size-8 shrink-0 items-center justify-center rounded bg-muted text-muted-foreground">
            <MdiMapMarkerOutline class="size-4" />
          </div>
          <div class="min-w-0">
            <div class="truncate">{{ l.name }}</div>
            <div v-if="parentPath(l.treeString)" class="truncate text-xs text-muted-foreground">
              {{ parentPath(l.treeString) }}
            </div>
          </div>
        </CommandItem>
      </CommandGroup>
      <div v-if="searching && !results.length" class="px-2 pb-1" aria-busy="true">
        <div class="px-2 py-1.5 text-xs font-medium text-muted-foreground">Items</div>
        <div v-for="n in 3" :key="n" class="flex items-center gap-3 px-2 py-1.5">
          <div class="size-8 shrink-0 animate-pulse rounded bg-muted" />
          <div class="grow space-y-1.5">
            <div class="h-3 animate-pulse rounded bg-muted" :style="{ width: `${70 - n * 12}%` }" />
            <div class="h-2.5 w-1/4 animate-pulse rounded bg-muted/70" />
          </div>
        </div>
      </div>
      <CommandGroup
        v-if="query.trim() && results.length"
        heading="Items"
        class="duration-150 animate-in fade-in-0"
        :class="searching ? 'opacity-60 transition-opacity' : 'transition-opacity'"
      >
        <CommandItem
          v-for="it in results"
          :key="it.id"
          :value="`item-${it.id}`"
          class="gap-3"
          @select="
            (e: Event) => {
              e.preventDefault();
              open(it);
            }
          "
        >
          <img v-if="thumb(it)" :src="thumb(it)" alt="" class="size-8 shrink-0 rounded object-cover" />
          <div v-else class="size-8 shrink-0 rounded bg-muted" />
          <div class="min-w-0">
            <div class="truncate">{{ it.name }}</div>
            <div v-if="it.parent" class="truncate text-xs text-muted-foreground">{{ pathOf(it.parent) }}</div>
          </div>
        </CommandItem>
      </CommandGroup>
      <CommandGroup v-if="createActions.length" :heading="t('global.create')">
        <CommandItem
          v-for="(create, i) in createActions"
          :key="`$global.create_${i + 1}`"
          :value="create.text"
          @select="
            e => {
              e.preventDefault();
              openDialog(create.dialogId as NoParamDialogIDs);
            }
          "
        >
          {{ create.text }}
          <Shortcut v-if="'shortcut' in create" class="ml-auto" size="sm" :keys="[create.shortcut]" />
        </CommandItem>
      </CommandGroup>
      <CommandSeparator v-if="createActions.length && (navActions.length || showScanner)" />
      <CommandGroup v-if="navActions.length || showScanner" :heading="t('global.navigate')">
        <CommandItem
          v-for="(navigate, i) in navActions"
          :key="navigate.text"
          :value="`global.navigate_${i + 1}`"
          @select="
            () => {
              closeDialog(DialogID.QuickMenu);
              navigateTo(navigate.href);
            }
          "
        >
          {{ navigate.text }}
        </CommandItem>
        <CommandItem
          v-if="showScanner"
          value="scanner"
          @select="
            () => {
              closeDialog(DialogID.QuickMenu);
              openDialog(DialogID.Scanner);
            }
          "
        >
          {{ t("menu.scanner") }}
        </CommandItem>
      </CommandGroup>
    </CommandList>
  </CommandDialog>
</template>
