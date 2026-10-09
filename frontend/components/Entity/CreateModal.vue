<template>
  <BaseModal :dialog-id="DialogID.CreateEntity">
    <template #title>
      <div class="flex items-center gap-2 text-nowrap">
        <span>Create</span>
        <EntitySelector
          :selected-entity-type="selectedEntityType?.id"
          :entity-types="subItemCreate ? entityTypes.filter(t => !t.isLocation) : entityTypes"
          size="sm"
          @entity-type-changed="onEntityTypeChanged"
        />
      </div>
    </template>
    <template #header-actions>
      <div class="flex gap-2">
        <TooltipProvider :delay-duration="0">
          <!-- Template selector button -->
          <Tooltip v-if="!selectedEntityType?.isLocation">
            <TooltipTrigger>
              <TemplateSelector v-model="selectedTemplate" compact @template-selected="handleTemplateSelected" />
            </TooltipTrigger>
            <TooltipContent>
              <p>{{ $t("components.template.apply_template") }}</p>
            </TooltipContent>
          </Tooltip>

          <ButtonGroup>
            <Tooltip>
              <TooltipTrigger>
                <Button variant="outline" :disabled="loading" size="icon" data-pos="start" @click="openQrScannerPage()">
                  <MdiBarcodeScan class="size-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{{ $t("components.entity.create_modal.product_tooltip_scan_barcode") }}</p>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger>
                <Button variant="outline" :disabled="loading" size="icon" data-pos="end" @click="openBarcodeDialog()">
                  <MdiBarcode class="size-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{{ $t("components.entity.create_modal.product_tooltip_input_barcode") }}</p>
              </TooltipContent>
            </Tooltip>
          </ButtonGroup>
        </TooltipProvider>
      </div>
    </template>

    <form class="flex min-w-0 flex-col gap-2" @submit.prevent="create()">
      <LocationSelector v-model="form.location" />

      <div
        v-if="duplicates.length"
        class="rounded-lg border-l-4 border-l-amber-500 bg-amber-500/10 p-3 text-sm"
        role="status"
      >
        <p class="font-medium">You already have this</p>
        <ul class="mt-1">
          <li v-for="d in duplicates" :key="d.id">
            <NuxtLink :to="`/item/${d.id}`" class="underline" @click="closeDialog(DialogID.CreateEntity)">
              {{ d.name }}
            </NuxtLink>
            <span v-if="d.parent" class="text-muted-foreground"> · {{ d.parent.name }}</span>
          </li>
        </ul>
        <p class="mt-1 text-muted-foreground">Saving will add another one.</p>
      </div>

      <!-- Template Info Display - Collapsible banner with distinct styling -->
      <div v-if="templateData" class="rounded-lg border-l-4 border-l-primary bg-primary/5 p-3">
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-1 items-start gap-2">
            <MdiFileDocumentOutline class="mt-0.5 size-4 shrink-0 text-primary" />
            <div class="flex-1">
              <h4 class="text-sm font-medium text-foreground">
                {{ $t("components.template.using_template", { name: templateData.name }) }}
              </h4>
              <button
                type="button"
                class="mt-1 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                @click="showTemplateDetails = !showTemplateDetails"
              >
                <span v-if="!showTemplateDetails">{{ $t("components.template.show_defaults") }}</span>
                <span v-else>{{ $t("components.template.hide_defaults") }}</span>
                <MdiChevronDown class="size-4 transition-transform" :class="{ 'rotate-180': showTemplateDetails }" />
              </button>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="size-7 shrink-0"
            :aria-label="$t('components.entity.create_modal.clear_template')"
            @click="clearTemplate"
          >
            <MdiClose class="size-4" />
          </Button>
        </div>

        <!-- Collapsible details section -->
        <div v-if="showTemplateDetails" class="mt-3 border-t border-primary/20 pt-3">
          <div class="flex flex-col gap-2 text-xs text-muted-foreground">
            <p v-if="templateData.description" class="text-foreground/80">{{ templateData.description }}</p>
            <div class="grid grid-cols-2 gap-x-4 gap-y-1">
              <div v-if="templateData.defaultName">
                <span class="font-medium">{{ $t("global.name") }}:</span> {{ templateData.defaultName }}
              </div>
              <div>
                <span class="font-medium">{{ $t("global.quantity") }}:</span> {{ templateData.defaultQuantity }}
              </div>
              <div>
                <span class="font-medium">{{ $t("global.insured") }}:</span>
                {{ templateData.defaultInsured ? $t("global.yes") : $t("global.no") }}
              </div>
              <div v-if="templateData.defaultManufacturer">
                <span class="font-medium">{{ $t("components.template.form.manufacturer") }}:</span>
                {{ templateData.defaultManufacturer }}
              </div>
              <div v-if="templateData.defaultModelNumber">
                <span class="font-medium">{{ $t("components.template.form.model_number") }}:</span>
                {{ templateData.defaultModelNumber }}
              </div>
              <div v-if="templateData.defaultLifetimeWarranty">
                <span class="font-medium">{{ $t("components.template.form.lifetime_warranty") }}:</span>
                {{ $t("global.yes") }}
              </div>
              <div v-if="templateData.defaultLocation">
                <span class="font-medium">{{ $t("components.template.form.location") }}:</span>
                {{ templateData.defaultLocation.name }}
              </div>
            </div>
            <div v-if="templateData.defaultTags && templateData.defaultTags.length > 0" class="mt-1">
              <span class="font-medium">{{ $t("global.tags") }}:</span>
              {{ templateData.defaultTags.map((t: any) => t.name).join(", ") }}
            </div>
            <div v-if="templateData.defaultDescription" class="mt-1">
              <p class="font-medium">{{ $t("components.template.form.item_description") }}:</p>
              <p class="ml-2">{{ templateData.defaultDescription }}</p>
            </div>
            <div v-if="templateData.fields && templateData.fields.length > 0" class="mt-1">
              <p class="font-medium">{{ $t("components.template.form.custom_fields") }}:</p>
              <ul class="ml-4 flex list-none flex-col gap-1">
                <li v-for="field in templateData.fields" :key="field.id">
                  <span class="font-medium">{{ field.name }}:</span>
                  <span> {{ field.textValue || $t("components.template.empty_value") }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <ItemSelector
        v-if="subItemCreate"
        v-model="parent"
        v-model:search="query"
        :label="$t('components.entity.create_modal.parent_item')"
        :items="results"
        item-text="name"
        :no-results-text="$t('components.entity.create_modal.item_selector_no_results_text')"
        :is-loading="isLoading"
        :trigger-search="triggerSearch"
      />
      <FormTextField
        ref="nameInput"
        v-model="form.name"
        :trigger-focus="focused"
        :autofocus="true"
        :label="
          $t('components.entity.create_modal.entity_name', {
            type: selectedEntityType ? t(selectedEntityType.name) : '',
          })
        "
        :max-length="255"
        :min-length="1"
      />
      <p v-if="bookDetails?.summary" class="-mt-1 px-1 text-sm text-muted-foreground">
        {{ bookDetails.summary }} <span class="opacity-70">· from Open Library</span>
      </p>
      <PhotoUploader
        camera
        label="Photos"
        :button-label="$t('components.entity.create_modal.upload_photos')"
        :existing-count="form.photos.length"
        @selected="appendPhotos"
      />
      <PhotoUploaderPreview
        :photos="form.photos"
        @delete="deletePhotoAt"
        @rotate="rotatePhotoAt"
        @set-primary="setPrimaryPhotoAt"
      />
      <FormTextField
        v-if="!selectedEntityType?.isLocation"
        v-model.number="form.quantity"
        :label="
          $t('components.entity.create_modal.entity_quantity', {
            type: t(selectedEntityType ? selectedEntityType.name : 'global.entity'),
          })
        "
        type="number"
        step="any"
      />
      <FormTextArea
        v-model="form.description"
        :label="
          $t('components.entity.create_modal.entity_description', {
            type: t(selectedEntityType ? selectedEntityType.name : 'global.entity'),
          })
        "
        :max-length="1000"
      />
      <TagSelector v-model="form.tags" :tags="tags ?? []" />
      <div class="mt-4 flex flex-row-reverse">
        <ButtonGroup>
          <Button :disabled="loading" type="submit" class="group">
            <div class="relative mx-2">
              <div
                class="absolute inset-0 flex items-center justify-center transition-transform duration-300 group-hover:rotate-[360deg]"
              >
                <MdiPackageVariant class="size-5 group-hover:hidden" />
                <MdiPackageVariantClosed class="hidden size-5 group-hover:block" />
              </div>
            </div>
            {{ $t("global.create") }}
          </Button>
          <Button variant="outline" :disabled="loading" type="button" @click="create(false)">
            {{ $t("global.create_and_add") }}
          </Button>
        </ButtonGroup>
      </div>
    </form>
  </BaseModal>
</template>

<script setup lang="ts">
  import { useI18n } from "vue-i18n";
  import { DialogID } from "@/components/ui/dialog-provider/utils";
  import { toast } from "@/components/ui/sonner";
  import { Button, ButtonGroup } from "~/components/ui/button";
  import BaseModal from "@/components/App/CreateModal.vue";
  import type {
    BarcodeProduct,
    EntityCreate,
    EntityFieldData,
    EntityUpdate,
    EntityTemplateOut,
    EntityTemplateSummary,
    EntityOut,
    EntitySummary,
    EntityTypeSummary,
  } from "~~/lib/api/types/data-contracts";
  import { useTagStore } from "~/stores/tags";
  import { useLocationStore } from "~~/stores/locations";
  import MdiBarcode from "~icons/mdi/barcode";
  import MdiBarcodeScan from "~icons/mdi/barcode-scan";
  import MdiPackageVariant from "~icons/mdi/package-variant";
  import MdiPackageVariantClosed from "~icons/mdi/package-variant-closed";
  import MdiFileDocumentOutline from "~icons/mdi/file-document-outline";
  import MdiChevronDown from "~icons/mdi/chevron-down";
  import MdiClose from "~icons/mdi/close";
  import { AttachmentTypes } from "~~/lib/api/types/non-generated";
  import { useDialog, useDialogHotkey } from "~/components/ui/dialog-provider";
  import TagSelector from "~/components/Tag/Selector.vue";
  import ItemSelector from "~/components/Item/Selector.vue";
  import TemplateSelector from "~/components/Template/Selector.vue";
  import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "~/components/ui/tooltip";
  import LocationSelector from "~/components/Location/Selector.vue";
  import FormTextField from "~/components/Form/TextField.vue";
  import FormTextArea from "~/components/Form/TextArea.vue";
  import PhotoUploader from "~/components/Form/PhotoUploader.vue";
  import PhotoUploaderPreview from "~/components/Form/PhotoUploaderPreview.vue";
  import {
    deletePhoto,
    dataURLtoFile,
    rotatePhotoPreview,
    setPrimaryPhoto,
    type PhotoPreview,
  } from "~/components/Form/photo-uploader";
  import { useEntityTypeStore } from "~~/stores/entityTypes";
  import EntitySelector from "~/components/Entity/Selector.vue";

  const { t } = useI18n();
  const { openDialog, closeDialog, registerOpenDialogCallback } = useDialog();

  useDialogHotkey(DialogID.CreateEntity, { code: "Digit1", shift: true }, () => ({
    baseType: "item",
  }));
  useDialogHotkey(DialogID.CreateEntity, { code: "Digit2", shift: true }, () => ({
    baseType: "location",
  }));

  const entityTypeStore = useEntityTypeStore();

  const api = useUserApi();

  const locationsStore = useLocationStore();
  const locations = computed(() => locationsStore.allLocations);

  const tagStore = useTagStore();
  const tags = computed(() => tagStore.tags);

  const route = useRoute();

  const parent = ref();
  const { query, results, isLoading, triggerSearch } = useItemSearch(api, { immediate: false });
  const subItemCreate = ref();

  const tagId = computed(() => {
    if (route.fullPath.includes("/tag/")) {
      return route.params.id;
    }
    return null;
  });

  const locationId = computed(() => {
    if (route.fullPath.includes("/location/")) {
      return route.params.id;
    }
    return null;
  });

  const itemId = computed(() => {
    if (route.fullPath.includes("/item/")) {
      return route.params.id;
    }
    return null;
  });

  const nameInput = ref<HTMLInputElement | null>(null);

  // Entity type selection
  const entityTypes = computed(() => entityTypeStore.allTypes);
  const selectedEntityType = ref<EntityTypeSummary | null>(null);
  const scannedProduct = ref<BarcodeProduct | null>(null);

  // Home fork: remember the last type and location used, so adding several things in a row
  // (or scan after scan) doesn't mean picking them again each time.
  const LAST_TYPE_KEY = "homebox:create.lastTypeId";
  const LAST_LOCATION_KEY = "homebox:create.lastLocationId";
  const readLast = (key: string) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };
  const writeLast = (key: string, value: string) => {
    try {
      localStorage.setItem(key, value);
    } catch {
      // storage unavailable; nothing is remembered
    }
  };

  // Home fork: an ISBN scan is a book, so switch to the Book type and fill its details from
  // Open Library (title without the store's ": A Novel" suffixes, author, publisher, year,
  // pages, format, and a cover when the product lookup had no image). The details are saved
  // as custom fields next to the ISBN. A type picked this way isn't remembered as "last used".
  type BookDetails = { title: string; fields: [string, string][]; summary: string };
  const bookDetails = ref<BookDetails | null>(null);
  const autoTyped = ref(false);
  const isIsbn = (code: string) => /^97[89]\d{10}$/.test(code);

  async function fetchJson(url: string) {
    const res = await fetch(url);
    return res.ok ? res.json() : null;
  }

  async function lookupBook(isbn: string): Promise<BookDetails | null> {
    const ed = await fetchJson(`https://openlibrary.org/isbn/${isbn}.json`);
    if (!ed) return null;
    let authorKeys: string[] = (ed.authors ?? []).map((a: { key: string }) => a.key);
    if (!authorKeys.length && ed.works?.[0]?.key) {
      const work = await fetchJson(`https://openlibrary.org${ed.works[0].key}.json`);
      authorKeys = (work?.authors ?? []).map((a: { author: { key: string } }) => a.author?.key).filter(Boolean);
    }
    const authors = (await Promise.all(authorKeys.slice(0, 4).map(k => fetchJson(`https://openlibrary.org${k}.json`))))
      .map(a => a?.name as string | undefined)
      .filter(Boolean) as string[];
    const year = String(ed.publish_date ?? "").match(/\b(1[5-9]|20)\d{2}\b/)?.[0] ?? "";
    const publisher = (ed.publishers ?? [])[0] ?? "";
    const pages = ed.number_of_pages ? String(ed.number_of_pages) : "";
    const format = ed.physical_format ? String(ed.physical_format).replace(/^./, c => c.toUpperCase()) : "";
    const subtitle = ed.subtitle ? String(ed.subtitle).replace(/^./, c => c.toUpperCase()) : "";
    const fields: [string, string][] = (
      [
        ["Subtitle", subtitle],
        ["Author", authors.join(" and ")],
        ["Publisher", publisher],
        ["Published", year],
        ["Pages", pages],
        ["Format", format],
      ] as [string, string][]
    ).filter(([, v]) => v);
    const summary = [authors.join(", "), publisher, year, pages && `${pages} pages`].filter(Boolean).join(" · ");
    return { title: String(ed.title ?? "").trim(), fields, summary };
  }

  async function coverFromOpenLibrary(isbn: string) {
    const res = await fetch(`https://covers.openlibrary.org/b/isbn/${isbn}-L.jpg?default=false`);
    if (!res.ok) return null;
    const blob = await res.blob();
    if (blob.size < 2000) return null; // a placeholder, not a cover
    return await new Promise<string>(resolve => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.readAsDataURL(blob);
    });
  }

  async function applyBookScan(isbn: string) {
    const book = entityTypes.value.find(t => !t.isLocation && t.name === "Book");
    if (book && selectedEntityType.value?.id !== book.id) {
      await onEntityTypeChanged(book.id);
      autoTyped.value = true;
    }
    try {
      const details = await lookupBook(isbn);
      if (!details || scannedProduct.value?.barcode?.trim() !== isbn) return;
      bookDetails.value = details;
      if (details.title) form.name = details.title;
      if (!form.photos.length) {
        const cover = await coverFromOpenLibrary(isbn);
        if (cover && !form.photos.length) {
          appendPhotos([
            { photoName: "cover.jpg", fileBase64: cover, primary: true, file: dataURLtoFile(cover, "cover.jpg") },
          ]);
        }
      }
    } catch (err) {
      console.warn("Open Library lookup failed", err);
    }
  }

  // Home fork: things you already have with the scanned barcode (checked when a scan opens this).
  const duplicates = ref<EntitySummary[]>([]);
  async function checkDuplicates(code: string) {
    duplicates.value = [];
    const fieldName = /^97[89]\d{10}$/.test(code) ? "ISBN" : "Barcode";
    const [byField, bySearch] = await Promise.all([
      api.items.getAll({ fields: [`${fieldName}=${code}`], pageSize: 10 }),
      api.items.getAll({ q: code, pageSize: 10 }),
    ]);
    const seen = new Map<string, EntitySummary>();
    for (const it of [...(byField.data?.items ?? []), ...(bySearch.data?.items ?? [])]) seen.set(it.id, it);
    duplicates.value = [...seen.values()];
  }

  async function onEntityTypeChanged(typeId: string) {
    const et = entityTypes.value.find(t => t.id === typeId);
    selectedEntityType.value = et || null;

    // A template the user picked explicitly takes precedence over the entity
    // type's default template, so don't overwrite it when the type changes.
    // (Locations don't use templates, so they still clear it below.)
    if (templateUserSelected.value && !et?.isLocation) {
      return;
    }

    // If the selected type has a default template and is not a location, auto-apply it
    if (et?.isLocation || !et?.defaultTemplateId || !et.defaultTemplate) {
      clearTemplate();
    } else {
      const { data, error } = await api.templates.get(et.defaultTemplateId);
      if (!error && data) {
        selectedTemplate.value = {
          id: data.id,
          name: data.name,
          description: data.description,
        } as EntityTemplateSummary;
        templateData.value = data;
        form.quantity = data.defaultQuantity;
        if (data.defaultName) form.name = data.defaultName;
        if (data.defaultDescription) form.description = data.defaultDescription;
        if (data.defaultLocation) {
          const found = locations.value.find(l => l.id === data.defaultLocation!.id);
          if (found) form.location = found;
        }
        if (data.defaultTags && data.defaultTags.length > 0) {
          form.tags = data.defaultTags.map(l => l.id);
        }
        toast.success(t("components.template.toast.applied", { name: data.name }));
      }
    }
  }

  const LAST_TEMPLATE_KEY = "homebox:lastUsedTemplate";

  const loading = ref(false);
  const focused = ref(false);
  const selectedTemplate = ref<EntityTemplateSummary | null>(null);
  const templateData = ref<EntityTemplateOut | null>(null);
  // Tracks whether the current template was chosen explicitly by the user (vs.
  // auto-applied from an entity type's default template). User selections win.
  const templateUserSelected = ref(false);
  const showTemplateDetails = ref(false);
  const form = reactive({
    location: locations.value && locations.value.length > 0 ? locations.value[0] : ({} as EntityOut),
    parentId: null,
    name: "",
    quantity: 1,
    description: "",
    color: "",
    tags: [] as string[],
    photos: [] as PhotoPreview[],
  });

  async function handleTemplateSelected(template: EntityTemplateSummary | null) {
    if (!template) {
      // Template was deselected, clear template data and remove from storage
      templateData.value = null;
      templateUserSelected.value = false;
      form.quantity = 1;
      localStorage.removeItem(LAST_TEMPLATE_KEY);
      return;
    }

    templateUserSelected.value = true;

    // Load full template details
    const { data, error } = await api.templates.get(template.id);
    if (error || !data) {
      toast.error(t("components.template.toast.load_failed"));
      return;
    }

    // Store template data for display and item creation
    templateData.value = data;

    // Pre-fill form with template defaults
    form.quantity = data.defaultQuantity;
    if (data.defaultName) {
      form.name = data.defaultName;
    }
    if (data.defaultDescription) {
      form.description = data.defaultDescription;
    }
    // Pre-fill location if template has one and current form doesn't
    if (data.defaultLocation && !form.location?.id) {
      const found = locations.value.find(l => l.id === data.defaultLocation!.id);
      if (found) {
        form.location = found;
      }
    }
    // Pre-fill tags from template
    if (data.defaultTags && data.defaultTags.length > 0) {
      form.tags = data.defaultTags.map(l => l.id);
    }

    // Save template ID to localStorage for persistence
    localStorage.setItem(LAST_TEMPLATE_KEY, template.id);

    toast.success(t("components.template.toast.applied", { name: data.name }));
  }

  async function restoreLastTemplate() {
    const lastTemplateId = localStorage.getItem(LAST_TEMPLATE_KEY);
    if (!lastTemplateId) return;

    // Load the template details
    const { data, error } = await api.templates.get(lastTemplateId);
    if (error || !data) {
      // Template might have been deleted, clear the stored ID
      localStorage.removeItem(LAST_TEMPLATE_KEY);
      return;
    }

    // Set the template. A restored template reflects the user's last explicit
    // choice, so treat it as user-selected for override purposes.
    selectedTemplate.value = { id: data.id, name: data.name, description: data.description } as EntityTemplateSummary;
    templateData.value = data;
    templateUserSelected.value = true;
    form.quantity = data.defaultQuantity;
    if (data.defaultName) {
      form.name = data.defaultName;
    }
    if (data.defaultDescription) {
      form.description = data.defaultDescription;
    }
    // Pre-fill location if template has one
    if (data.defaultLocation) {
      const found = locations.value.find(l => l.id === data.defaultLocation!.id);
      if (found) {
        form.location = found;
      }
    }
    // Pre-fill tags from template
    if (data.defaultTags && data.defaultTags.length > 0) {
      form.tags = data.defaultTags.map(l => l.id);
    }
  }

  function clearTemplate() {
    selectedTemplate.value = null;
    templateData.value = null;
    templateUserSelected.value = false;
    showTemplateDetails.value = false;
    form.quantity = 1;
    localStorage.removeItem(LAST_TEMPLATE_KEY);
  }

  watch(
    parent,
    newParent => {
      if (newParent && newParent.id && subItemCreate.value) {
        form.parentId = newParent.id;
      } else {
        form.parentId = null;
      }
    },
    { immediate: true }
  );

  const { shift } = useMagicKeys();
  function appendPhotos(photos: PhotoPreview[]) {
    form.photos.push(...photos);
  }

  function deletePhotoAt(index: number) {
    form.photos = deletePhoto(form.photos, index);
  }

  function setPrimaryPhotoAt(index: number) {
    form.photos = setPrimaryPhoto(form.photos, index);
  }

  async function rotatePhotoAt(index: number) {
    const photo = form.photos[index];
    if (!photo) return;

    try {
      form.photos[index] = await rotatePhotoPreview(photo);
    } catch (error) {
      toast.error(t("components.entity.create_modal.toast.rotate_process_failed"));
      console.error(error);
    }
  }

  onMounted(() => {
    const cleanup = registerOpenDialogCallback(DialogID.CreateEntity, async params => {
      subItemCreate.value = false;
      scannedProduct.value = null;
      duplicates.value = [];
      bookDetails.value = null;
      autoTyped.value = false;
      let parentItemLocationId = null;
      parent.value = {};
      form.parentId = null;

      if (params.baseType === "item") {
        const lastType = entityTypes.value.find(t => t.id === readLast(LAST_TYPE_KEY) && !t.isLocation);
        selectedEntityType.value =
          lastType ||
          entityTypes.value.find(t => !t.isLocation && t.name === "Item") ||
          entityTypes.value.find(t => !t.isLocation) ||
          null;
        // apply the type's default template (its fields), as picking it by hand would
        if (lastType?.defaultTemplateId && !params.subItem) await onEntityTypeChanged(lastType.id);

        subItemCreate.value = params.subItem;

        if (subItemCreate.value && itemId.value) {
          const itemIdRead = typeof itemId.value === "string" ? (itemId.value as string) : itemId.value[0]!;
          const { data, error } = await api.items.get(itemIdRead);
          if (error || !data) {
            toast.error(t("components.entity.create_modal.toast.failed_load_parent"));
            console.error("Parent item fetch error:", error);
          }

          if (data) {
            parent.value = data;
          }

          if (data.parent) {
            const loc = data.parent;
            parentItemLocationId = loc.id;
          }
        }

        if (params.product) {
          scannedProduct.value = params.product;
          if (params.product.barcode) checkDuplicates(params.product.barcode.trim());
          form.name = params.product.item.name;
          form.description = params.product.item.description;

          // only when the server actually fetched the image (a failed fetch leaves it empty)
          if (params.product.imageURL && params.product.imageBase64?.startsWith("data:")) {
            appendPhotos([
              {
                photoName: "product_view.jpg",
                fileBase64: params.product.imageBase64,
                primary: form.photos.length === 0,
                file: dataURLtoFile(params.product.imageBase64, "product_view.jpg"),
              },
            ]);
          }
        }

        // Restore last used template if available
        await restoreLastTemplate();
        // after the template, so a book scan still ends up as a Book with its own details
        const scannedCode = params.product?.barcode?.trim() ?? "";
        if (isIsbn(scannedCode)) applyBookScan(scannedCode);
      } else {
        selectedEntityType.value = entityTypes.value.find(t => t.isLocation) || null;
      }

      const locId =
        (locationId.value ? locationId.value : parentItemLocationId) ||
        (params.baseType === "item" ? readLast(LAST_LOCATION_KEY) : null);

      if (locId) {
        const found = locations.value.find(l => l.id === locId);
        if (found) {
          form.location = found;
        }
      }

      if (tagId.value) {
        form.tags = tags.value.filter(l => l.id === tagId.value).map(l => l.id);
      }
    });

    onUnmounted(cleanup);
  });

  async function create(close = true) {
    // An empty entityTypeId serializes to "" and fails UUID unmarshalling on the
    // backend, so block creation up front rather than firing a doomed request.
    if (!selectedEntityType.value?.id) {
      toast.error(t("components.entity.create_modal.toast.please_select_entity_type"));
      return;
    }

    // Items must live somewhere, but a top-level location has no parent, so the
    // parent location selector is optional when creating a location.
    if (!selectedEntityType.value?.isLocation && !form.location?.id) {
      toast.error(t("components.entity.create_modal.toast.please_select_location"));
      return;
    }

    if (loading.value) {
      toast.error(
        t("components.entity.create_modal.toast.already_creating", {
          type: t(selectedEntityType.value ? selectedEntityType.value.name : "global.entity"),
        })
      );
      return;
    }

    loading.value = true;

    if (shift?.value) close = false;

    let error, data;

    // If the selected entity type is a location, use the location creation endpoint
    if (selectedEntityType.value?.isLocation) {
      const result = await api.items.createLocation({
        name: form.name,
        description: form.description,
        parentId: form.location?.id || null,
        entityTypeId: selectedEntityType.value?.id || "",
        quantity: 1,
        tagIds: form.tags,
      });
      error = result.error;
      data = result.data;
    } else if (templateData.value) {
      // If a template is selected, use the template creation endpoint
      const templateRequest = {
        name: form.name,
        description: form.description,
        parentId: form.location.id as string,
        tagIds: form.tags,
        quantity: form.quantity,
        entityTypeId: selectedEntityType.value?.id || "",
      };

      const result = await api.templates.createItem(templateData.value.id, templateRequest);
      error = result.error;
      data = result.data;
    } else {
      // Normal item creation without template
      const out: EntityCreate = {
        parentId: form.parentId || (form.location.id as string),
        name: form.name,
        quantity: form.quantity,
        description: form.description,
        tagIds: form.tags,
        entityTypeId: selectedEntityType.value?.id || "",
      };

      const result = await api.items.create(out);
      error = result.error;
      data = result.data;
    }

    if (error) {
      loading.value = false;
      toast.error(
        t("components.entity.create_modal.toast.create_failed", {
          type: t(selectedEntityType.value ? selectedEntityType.value.name : "global.entity"),
        })
      );
      return;
    }

    toast.success(
      t("components.entity.create_modal.toast.create_success", {
        type: t(selectedEntityType.value ? selectedEntityType.value.name : "global.entity"),
      })
    );

    if (scannedProduct.value && !selectedEntityType.value?.isLocation) {
      await saveScannedIdentifiers(data.id, scannedProduct.value, bookDetails.value?.fields ?? []);
    }
    const wasScanned = !!scannedProduct.value;
    scannedProduct.value = null;
    duplicates.value = [];
    if (!selectedEntityType.value?.isLocation) {
      if (selectedEntityType.value?.id && !autoTyped.value) writeLast(LAST_TYPE_KEY, selectedEntityType.value.id);
      if (form.location?.id) writeLast(LAST_LOCATION_KEY, form.location.id as string);
    }

    if (form.photos.length > 0) {
      toast.info(t("components.entity.create_modal.toast.uploading_photos", { count: form.photos.length }));
      let uploadError = false;
      for (const photo of form.photos) {
        const { error: attachError } = await api.items.attachments.add(
          data.id,
          photo.file,
          photo.photoName,
          AttachmentTypes.Photo,
          photo.primary
        );

        if (attachError) {
          uploadError = true;
          toast.error(t("components.entity.create_modal.toast.upload_failed", { photoName: photo.photoName }));
          console.error(attachError);
        }
      }
      if (uploadError) {
        toast.warning(t("components.entity.create_modal.toast.some_photos_failed", { count: form.photos.length }));
      } else {
        toast.success(t("components.entity.create_modal.toast.upload_success", { count: form.photos.length }));
      }
    }

    form.name = "";
    form.quantity = 1;
    form.description = "";
    form.color = "";
    form.photos = [];
    form.tags = [];
    selectedTemplate.value = null;
    templateData.value = null;
    templateUserSelected.value = false;
    showTemplateDetails.value = false;
    focused.value = false;
    loading.value = false;

    if (!close && wasScanned) {
      // batch scanning: straight back to the camera for the next one
      toast.info("Ready for the next scan");
      openDialog(DialogID.Scanner);
      return;
    }

    if (close) {
      closeDialog(DialogID.CreateEntity);
      if (selectedEntityType.value?.isLocation) {
        navigateTo(`/location/${data.id}`);
      } else {
        navigateTo(`/item/${data.id}`);
      }
    }
  }

  // Home fork: keep the scanned barcode (as "ISBN" for books) plus the publisher/brand and
  // model number from the lookup. EntityCreate has no such fields, so set them right after.
  async function saveScannedIdentifiers(id: string, product: BarcodeProduct, extra: [string, string][] = []) {
    const code = (product.barcode || "").trim();
    if (!code) return;
    const fieldName = /^97[89]\d{10}$/.test(code) ? "ISBN" : "Barcode";

    const { data: item, error } = await api.items.get(id);
    if (error || !item) {
      console.error("Failed to load new item to save barcode:", error);
      return;
    }

    const fields = (item.fields || []).filter(f => f.name !== fieldName);
    for (const [name, textValue] of extra) {
      if (fields.some(f => f.name === name && f.textValue)) continue;
      const i = fields.findIndex(f => f.name === name);
      if (i >= 0) fields.splice(i, 1);
      fields.push({
        id: null,
        name,
        type: "text",
        textValue,
        numberValue: 0,
        booleanValue: false,
      } as unknown as EntityFieldData);
    }
    fields.push({
      id: null,
      name: fieldName,
      type: "text",
      textValue: code,
      numberValue: 0,
      booleanValue: false,
    } as unknown as EntityFieldData);

    // keep the book fields in the usual order: Subtitle, Author, ISBN, Publisher, ...
    const authorAt = fields.findIndex(f => f.name === "Author");
    if (authorAt >= 0) fields.splice(authorAt + 1, 0, fields.pop()!);

    const { error: updateError } = await api.items.update(id, {
      ...item,
      parentId: item.parent?.id || null,
      tagIds: (item.tags || []).map(t => t.id),
      entityTypeId: item.entityType!.id,
      purchasePrice: item.purchasePrice || 0,
      soldPrice: item.soldPrice || 0,
      manufacturer: item.manufacturer || product.manufacturer || extra.find(([n]) => n === "Publisher")?.[1] || "",
      modelNumber: item.modelNumber || product.modelNumber || (fieldName === "ISBN" ? code : ""),
      fields,
    } as unknown as EntityUpdate);

    if (updateError) {
      toast.error(`Couldn't save ${fieldName} ${code}`);
      console.error(updateError);
    }
  }

  function openQrScannerPage() {
    openDialog(DialogID.Scanner);
  }

  function openBarcodeDialog() {
    openDialog(DialogID.ProductImport);
  }
</script>
