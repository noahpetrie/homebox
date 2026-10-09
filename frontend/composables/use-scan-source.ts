// Home fork: where the barcode being added came from, so "Create and add another" goes back
// to the camera only after a camera scan. After a handheld-scanner scan it just waits for
// the next scan instead of asking for camera access.
import { ref } from "vue";

export type ScanSource = "camera" | "handheld";
export const lastScanSource = ref<ScanSource | null>(null);
