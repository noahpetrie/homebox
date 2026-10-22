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
  const search = useDebounceFn(async (q: string) => {
    if (!q) {
      results.value = [];
      return;
    }
    const { data } = await api.items.getAll({ q, pageSize: 8 });
    if (query.value.trim() === q) results.value = data?.items ?? [];
  }, 200);
  watch(query, q => search(q.trim()));
  // start empty each time the menu opens
  watch(activeDialog, d => {
    if (d === DialogID.QuickMenu) {
      query.value = "";
      results.value = [];
    }
  });

  const flatLocations = useFlatLocations();
  const pathOf = (p: { id: string; name: string }) =>
    flatLocations.value.find(l => l.id === p.id)?.treeString?.replace(/ > /g, " › ") || p.name;
  const thumb = (it: EntitySummary) =>
    it.imageId ? api.authURL(`/entities/${it.id}/attachments/${it.thumbnailId || it.imageId}`) : "";

  function open(it: EntitySummary) {
    closeDialog(DialogID.QuickMenu);
    query.value = "";
    navigateTo(`/${it.entityType?.isLocation ? "location" : "item"}/${it.id}`);
  }
</script>

<template>
  <CommandDialog :dialog-id="DialogID.QuickMenu">
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
    <CommandList>
      <CommandSeparator />
      <CommandEmpty>{{ t("components.quick_menu.no_results") }}</CommandEmpty>
      <CommandGroup v-if="query.trim() && results.length" heading="Items">
        <!-- matched on the server (maybe by author or ISBN), so the text value includes the query to
             keep the menu's own text filter from hiding them -->
        <CommandItem
          v-for="it in results"
          :key="it.id"
          :value="`item-${it.id}`"
          :text-value="`${it.name} ${query}`"
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
      <CommandGroup :heading="t('global.create')">
        <CommandItem
          v-for="(create, i) in props.actions.filter(item => item.type === 'create')"
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
      <CommandSeparator />
      <CommandGroup :heading="t('global.navigate')">
        <CommandItem
          v-for="(navigate, i) in props.actions.filter(item => item.type === 'navigate')"
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
