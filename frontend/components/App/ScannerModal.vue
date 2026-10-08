<template>
  <Dialog :dialog-id="DialogID.Scanner">
    <DialogScrollContent>
      <DialogHeader>
        <DialogTitle>{{ t("scanner.title") }}</DialogTitle>
      </DialogHeader>
      <div>
        <div
          v-if="errorMessage"
          class="mb-5 flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 p-4 text-destructive"
          role="alert"
        >
          <MdiAlertCircleOutline class="text-destructive" />
          <span class="text-sm font-medium">{{ errorMessage }}</span>
        </div>
        <div
          v-if="detectedBarcode"
          class="mb-5 flex flex-col items-center gap-2 rounded-md border border-accent-foreground bg-accent p-4 text-accent-foreground"
          role="alert"
        >
          <div class="flex">
            <MdiBarcode class="mr-2" />
            <span class="flex-1 text-center text-sm font-medium">
              {{ detectedBarcodeType }} {{ $t("scanner.barcode_detected_message") }}:
              <strong>{{ detectedBarcode }}</strong>
            </span>
          </div>

          <ButtonGroup>
            <Button :disabled="loading" type="submit" @click="handleButtonClick">
              {{ $t("scanner.barcode_fetch_data") }}
            </Button>
          </ButtonGroup>
        </div>
        <div class="relative">
          <!-- eslint-disable-next-line tailwindcss/no-custom-classname -->
          <video
            ref="video"
            class="aspect-[4/3] w-full rounded-lg bg-muted object-cover shadow"
            poster="data:image/gif,AAAA"
            autoplay
            muted
            playsinline
          />
          <!-- Home fork: aiming guide -->
          <div
            class="pointer-events-none absolute inset-x-[12%] top-1/2 h-[28%] -translate-y-1/2 rounded-lg border-2 border-white/80 shadow-[0_0_0_9999px_rgba(0,0,0,0.25)]"
          />
          <p class="absolute inset-x-0 bottom-2 text-center text-xs font-medium text-white drop-shadow">
            {{ detectedBarcode ? "" : "Hold the barcode inside the box, about 15 cm away" }}
          </p>
        </div>
        <div class="mt-4 flex flex-col gap-3">
          <Select v-model="selectedSource" @update:model-value="rememberSource">
            <SelectTrigger class="w-full">
              <SelectValue :placeholder="t('scanner.select_video_source')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="source in sources" :key="source.deviceId" :value="source.deviceId">
                {{ source.label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="sm" class="w-full text-muted-foreground" @click="openArMode">
            <MdiCameraOutline class="mr-2" />
            {{ t("scanner_ar.ar_mode") }}: look inside boxes by pointing at Homebox QR labels
          </Button>
        </div>
      </div>
    </DialogScrollContent>
  </Dialog>
</template>

<script setup lang="ts">
  // Home fork: product barcodes are decoded with zxing-cpp (WebAssembly, via the
  // barcode-detector package AR mode already uses) instead of the pure-JS @zxing/library
  // reader, from a 1080p stream on the best back camera, about 8 times a second. A product
  // barcode opens the lookup straight away once it has been read twice in a row.
  import { computed, ref, watch } from "vue";
  import { BarcodeDetector, prepareZXingModule } from "barcode-detector";
  import { useI18n } from "vue-i18n";
  import { DialogID } from "@/components/ui/dialog-provider/utils";
  import { Dialog, DialogHeader, DialogScrollContent, DialogTitle } from "@/components/ui/dialog";
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
  import { Button, ButtonGroup } from "@/components/ui/button";
  import MdiBarcode from "~icons/mdi/barcode";
  import MdiAlertCircleOutline from "~icons/mdi/alert-circle-outline";
  import MdiCameraOutline from "~icons/mdi/camera-outline";
  import { useDialog } from "@/components/ui/dialog-provider";

  const { t } = useI18n();
  const { activeDialog, openDialog, closeDialog } = useDialog();
  const open = computed(() => activeDialog && activeDialog.value === DialogID.Scanner);

  const sources = ref<MediaDeviceInfo[]>([]);
  const selectedSource = ref<string | null>(null);
  const loading = ref(false);
  const video = ref<HTMLVideoElement>();
  const errorMessage = ref<string | null>(null);
  const detectedBarcode = ref<string>("");
  const detectedBarcodeType = ref<string>("");

  // Only set when the user picks a camera by hand (the old key also stored automatic picks).
  const CHOSEN_DEVICE_ID_KEY = "homebox:scannerCameraId";
  const PRODUCT_FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e"];
  const SCAN_INTERVAL_MS = 120;

  let detector: BarcodeDetector | null = null;
  let stream: MediaStream | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let session = 0;
  let lastCode = "";

  const handleError = (error: unknown) => {
    console.error("Scanner error:", error);
    errorMessage.value = t("scanner.error");
  };

  const handleButtonClick = () => {
    openDialog(DialogID.ProductImport, { params: { barcode: detectedBarcode.value } });
  };

  const openArMode = () => {
    closeDialog(DialogID.Scanner);
    navigateTo("/scanner-ar");
  };

  // iPhones list many cameras. The virtual multi-lens cameras switch to the macro lens up
  // close, which suits barcodes; telephoto and ultra-wide on their own focus badly there.
  function cameraScore(label: string): number {
    const l = label.toLowerCase();
    if (l.includes("front")) return 0;
    if (l.includes("triple")) return 6;
    if (l.includes("dual wide")) return 5;
    if (l.includes("dual")) return 4;
    if (l.includes("telephoto") || l.includes("ultra")) return 1;
    if (l.includes("back") || l.includes("rear") || l.includes("environment")) return 3;
    return 2;
  }

  function rememberSource(id: unknown) {
    try {
      if (typeof id === "string") localStorage.setItem(CHOSEN_DEVICE_ID_KEY, id);
    } catch (e) {
      console.debug("failed to persist selected camera", e);
    }
  }

  const startScanner = async () => {
    errorMessage.value = null;
    if (!(navigator && navigator.mediaDevices && "enumerateDevices" in navigator.mediaDevices)) {
      errorMessage.value = t("scanner.unsupported");
      return;
    }

    // Start fetching the decoder while the camera spins up.
    prepareZXingModule({ fireImmediately: true }).catch(e => console.warn("zxing preload failed", e));

    try {
      try {
        const probe = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } } });
        probe.getTracks().forEach(track => track.stop());
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "NotAllowedError") {
          errorMessage.value = t("scanner.permission_denied");
          return;
        }
        throw err;
      }

      const devices = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === "videoinput");
      sources.value = devices;
      if (devices.length === 0) {
        errorMessage.value = t("scanner.no_sources");
        return;
      }

      let chosen: string | null = null;
      try {
        chosen = localStorage.getItem(CHOSEN_DEVICE_ID_KEY);
      } catch (e) {
        console.debug("failed to read selected camera", e);
      }
      const best = [...devices].sort((a, b) => cameraScore(b.label) - cameraScore(a.label))[0]!;
      selectedSource.value = devices.find(d => d.deviceId === chosen)?.deviceId ?? best.deviceId;
    } catch (err) {
      handleError(err);
    }
  };

  function stopStream() {
    session++;
    if (timer) clearTimeout(timer);
    timer = null;
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
    if (video.value) video.value.srcObject = null;
  }

  const stopScanner = () => {
    stopStream();
    sources.value = [];
    selectedSource.value = null;
    loading.value = false;
    lastCode = "";
  };

  function onCode(rawValue: string, format: string) {
    if (format === "qr_code") {
      try {
        const url = new URL(rawValue);
        if (!url.pathname.startsWith("/")) throw new Error(t("scanner.invalid_url"));
        loading.value = true;
        closeDialog(DialogID.Scanner);
        navigateTo(url.pathname.replace(/[^a-zA-Z0-9-_/]/g, ""));
      } catch (err) {
        handleError(err);
      }
      return;
    }

    // Require two matching reads in a row so a half-seen barcode can't slip through.
    if (rawValue !== lastCode) {
      lastCode = rawValue;
      return;
    }
    detectedBarcode.value = rawValue;
    detectedBarcodeType.value = format.toUpperCase().replace("_", "-");
    loading.value = true;
    stopStream();
    navigator.vibrate?.(60);
    openDialog(DialogID.ProductImport, { params: { barcode: rawValue } });
    loading.value = false;
  }

  async function scanLoop(mySession: number) {
    if (mySession !== session) return;
    const el = video.value;
    if (detector && el && el.readyState >= 2 && !loading.value) {
      try {
        const found = await detector.detect(el);
        if (mySession !== session) return;
        const code = found.find(b => PRODUCT_FORMATS.includes(b.format)) ?? found.find(b => b.format === "qr_code");
        if (code) onCode(code.rawValue, code.format);
      } catch (err) {
        console.debug("detect failed", err);
      }
    }
    if (mySession === session) timer = setTimeout(() => scanLoop(mySession), SCAN_INTERVAL_MS);
  }

  watch(open, async isOpen => {
    if (isOpen) {
      detectedBarcode.value = "";
      lastCode = "";
      await startScanner();
    } else {
      stopScanner();
    }
  });

  watch(selectedSource, async newSource => {
    if (!open.value || !newSource) return;
    stopStream();
    const mySession = session;

    try {
      detector ??= new BarcodeDetector({ formats: [...PRODUCT_FORMATS, "qr_code"] as never });
      const constraints: MediaTrackConstraints = {
        deviceId: { exact: newSource },
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      };
      const s = await navigator.mediaDevices.getUserMedia({ video: constraints });
      if (mySession !== session) {
        s.getTracks().forEach(track => track.stop());
        return;
      }
      stream = s;
      const track = s.getVideoTracks()[0];
      try {
        await track?.applyConstraints({ advanced: [{ focusMode: "continuous" } as MediaTrackConstraintSet] });
      } catch {
        // not supported everywhere (e.g. Safari); autofocus is on by default there
      }
      video.value!.srcObject = s;
      await video.value!.play().catch(() => {});
      scanLoop(mySession);
    } catch (err) {
      handleError(err);
    }
  });

  onUnmounted(() => {
    stopScanner();
  });
</script>
