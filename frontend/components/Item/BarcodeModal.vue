<template>
  <Dialog :dialog-id="DialogID.ProductImport">
    <DialogContent :class="'w-full md:max-w-xl lg:max-w-4xl'">
      <DialogHeader>
        <DialogTitle>{{ $t("components.item.product_import.title") }}</DialogTitle>
      </DialogHeader>

      <div
        v-if="errorMessage"
        class="flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 p-4 text-destructive"
        role="alert"
      >
        <MdiAlertCircleOutline class="text-destructive" />
        <span class="text-sm font-medium">{{ errorMessage }}</span>
      </div>

      <div class="flex items-center gap-3">
        <FormTextField
          v-model="barcode"
          :disabled="searching"
          class="w-[30%]"
          :label="$t('components.item.product_import.barcode')"
          @keyup.enter="retrieveProductInfo(barcode)"
        />
        <Button
          :variant="searching ? 'destructive' : 'default'"
          class="mt-auto h-10"
          @click="retrieveProductInfo(barcode)"
        >
          <MdiLoading v-if="searching" class="animate-spin" />
          <div v-if="!searching" class="relative mx-2">
            <div class="absolute inset-0 flex items-center justify-center">
              <MdiBarcode class="size-5 group-hover:hidden" />
            </div>
          </div>
          {{ searching ? $t("global.cancel") : $t("components.item.product_import.search_item") }}
        </Button>
      </div>

      <Separator />

      <!-- Home fork: one selectable row per result; long titles wrap instead of running into
           the next column. -->
      <div v-if="products && products.length" class="flex max-h-[50vh] flex-col gap-2 overflow-y-auto">
        <button
          v-for="(p, index) in products"
          :key="index"
          type="button"
          class="flex items-center gap-4 rounded-lg border-2 bg-card p-3 text-left transition-colors hover:bg-accent/50"
          :class="selectedRow === index ? 'border-primary bg-accent/40' : 'border-transparent'"
          @click="selectProduct(index)"
        >
          <img
            v-if="p.imageBase64"
            :src="p.imageBase64"
            class="h-24 w-16 shrink-0 rounded object-contain"
            alt="Product's photo"
          />
          <div v-else class="flex h-24 w-16 shrink-0 items-center justify-center rounded bg-muted">
            <MdiBarcode class="size-6 opacity-40" />
          </div>
          <div class="min-w-0 grow">
            <div class="font-medium leading-snug">{{ p.item.name }}</div>
            <div class="mt-1 text-sm text-muted-foreground">
              {{ [p.manufacturer, p.modelNumber].filter(Boolean).join(" · ") }}
            </div>
            <div class="mt-1 text-xs text-muted-foreground">
              {{ p.search_engine_name }}
            </div>
          </div>
          <div
            class="flex size-5 shrink-0 items-center justify-center rounded-full border-2"
            :class="selectedRow === index ? 'border-primary bg-primary' : 'border-muted-foreground/40'"
          >
            <div v-if="selectedRow === index" class="size-2 rounded-full bg-primary-foreground" />
          </div>
        </button>
      </div>

      <DialogFooter>
        <Button type="button" :disabled="selectedRow === -1" @click="createItem">
          {{ $t("components.item.product_import.import_selected") }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
  import { useI18n } from "vue-i18n";
  import { DialogID } from "@/components/ui/dialog-provider/utils";
  import { Button } from "~/components/ui/button";
  import type { BarcodeProduct } from "~~/lib/api/types/data-contracts";
  import { useDialog } from "~/components/ui/dialog-provider";
  import MdiAlertCircleOutline from "~icons/mdi/alert-circle-outline";
  import MdiBarcode from "~icons/mdi/barcode";
  import MdiLoading from "~icons/mdi/loading";
  import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
  import { Separator } from "@/components/ui/separator";
  import FormTextField from "@/components/Form/TextField.vue";

  const { openDialog, registerOpenDialogCallback } = useDialog();
  const { t } = useI18n();

  const searching = ref(false);
  const barcode = ref<string>("");
  const products = ref<BarcodeProduct[] | null>(null);
  const selectedRow = ref(-1);
  const errorMessage = ref<string | null>(null);

  onMounted(() => {
    const cleanup = registerOpenDialogCallback(DialogID.ProductImport, params => {
      selectedRow.value = -1;
      searching.value = false;
      errorMessage.value = null;

      if (params?.barcode) {
        // Reset if the barcode is different
        if (params.barcode !== barcode.value) {
          barcode.value = params.barcode;

          retrieveProductInfo(barcode.value).then(() => {
            console.log("Processing finished");
          });
        }
      } else {
        barcode.value = "";
        products.value = null;
      }
    });

    onUnmounted(cleanup);
  });

  const api = useUserApi();

  function createItem() {
    if (
      products.value !== null &&
      products.value.length > 0 &&
      selectedRow.value >= 0 &&
      selectedRow.value < products.value.length
    ) {
      const p = products.value![selectedRow.value];
      openDialog(DialogID.CreateEntity, {
        params: {
          baseType: "item",
          product: p,
        },
      });
    }
  }

  async function retrieveProductInfo(barcode: string) {
    errorMessage.value = null;

    if (!barcode || barcode.trim().length === 0 || !/^[0-9]+$/.test(barcode)) {
      errorMessage.value = t("components.item.product_import.error_invalid_barcode");
      console.error(errorMessage.value);
      return;
    }

    products.value = null;
    searching.value = true;

    try {
      const result = await api.products.searchFromBarcode(barcode.trim());
      if (result.error) {
        errorMessage.value = t("errors.api_failure") + result.error;
        console.error(errorMessage.value);
      } else {
        if (result.data === undefined || result.data.length === undefined || result.data.length === 0) {
          errorMessage.value = t("components.item.product_import.error_not_found");
        }

        products.value = result.data;
        // Home fork: a single match is selected straight away
        if (result.data?.length === 1) selectedRow.value = 0;
      }
    } catch (error) {
      errorMessage.value = t("components.item.product_import.error_exception") + error;
      console.error(errorMessage.value);
    } finally {
      searching.value = false;
    }
  }

  function selectProduct(index: number) {
    // Unselect if already selected
    if (selectedRow.value === index) {
      selectedRow.value = -1;
      return;
    }

    selectedRow.value = index;
  }
</script>

<style>
  tr.selected {
    background-color: hsl(var(--primary));
    color: hsl(var(--background));
  }

  tr:hover.selected {
    background-color: hsl(var(--primary));
  }
</style>
