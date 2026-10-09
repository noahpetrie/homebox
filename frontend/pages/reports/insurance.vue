<script setup lang="ts">
  // Home fork: a printable home-insurance inventory. Items grouped by room with photo, maker /
  // model / serial, location, purchase details, the price paid and an estimated current
  // replacement value (custom field "Replacement value", with "Valued from" saying where it came
  // from). Insured value = replacement value when known, else the price paid, times quantity.
  // Vehicles are listed separately and left out of the totals (they're insured on their own).
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";
  import { Button } from "@/components/ui/button";
  import MdiPrinter from "~icons/mdi/printer";
  import MdiDownload from "~icons/mdi/download";
  import MdiArrowLeft from "~icons/mdi/arrow-left";

  definePageMeta({ middleware: ["auth"], layout: false });
  useHead({ title: "HomeBox | Insurance inventory" });

  const api = useUserApi();
  const fmt = await useFormatCurrency();
  const flat = useFlatLocations();

  type Row = {
    id: string;
    name: string;
    maker: string;
    model: string;
    serial: string;
    path: string;
    room: string;
    bought: string;
    paid: number;
    replacement: number | null;
    valuedFrom: string;
    qty: number;
    insured: number;
    thumb: string;
    vehicle: boolean;
  };

  const rows = ref<Row[]>([]);
  const loading = ref(true);
  const progress = ref(0);

  const num = (v?: string) => {
    const n = Number(String(v ?? "").replace(/[^0-9.]/g, ""));
    return Number.isFinite(n) && n > 0 ? n : null;
  };
  const dateOnly = (v?: string | Date | null) => {
    const d = v ? String(v instanceof Date ? v.toISOString() : v) : "";
    return d && !d.startsWith("0001") ? d.slice(0, 10) : "";
  };

  onMounted(async () => {
    const { data } = await api.items.getAll({ pageSize: 1000 });
    const items = (data?.items ?? []).filter(i => !i.entityType?.isLocation && !i.archived);
    const out: Row[] = [];
    const queue = [...items];
    const worker = async () => {
      while (queue.length) {
        const s = queue.shift() as EntitySummary;
        const { data: d } = await api.items.get(s.id);
        progress.value++;
        if (!d) continue;
        const field = (n: string) => d.fields?.find(f => f.name === n)?.textValue ?? "";
        const path = (flat.value.find(l => l.id === d.parent?.id)?.treeString ?? d.parent?.name ?? "").replace(
          / > /g,
          " › "
        );
        const replacement = num(field("Replacement value"));
        const qty = d.quantity || 1;
        out.push({
          id: d.id,
          name: d.name,
          maker: d.manufacturer || field("Author") || field("Publisher"),
          model: d.modelNumber || "",
          serial: d.serialNumber || "",
          path,
          room: path.split(" › ")[0] || "Unassigned",
          bought: [dateOnly(d.purchaseDate), d.purchaseFrom].filter(Boolean).join(" · "),
          paid: d.purchasePrice || 0,
          replacement,
          valuedFrom: field("Valued from"),
          qty,
          insured: (replacement ?? (d.purchasePrice || 0)) * qty,
          thumb: s.imageId ? api.authURL(`/entities/${s.id}/attachments/${s.thumbnailId || s.imageId}`) : "",
          vehicle: d.entityType?.name === "Vehicle",
        });
      }
    };
    await Promise.all(Array.from({ length: 8 }, worker));
    rows.value = out;
    loading.value = false;
  });

  const insurable = computed(() => rows.value.filter(r => !r.vehicle));
  const vehicles = computed(() => rows.value.filter(r => r.vehicle));
  const rooms = computed(() => {
    const by = new Map<string, Row[]>();
    for (const r of insurable.value) by.set(r.room, [...(by.get(r.room) ?? []), r]);
    return [...by.entries()]
      .map(([room, list]) => ({
        room,
        list: list.sort((a, b) => b.insured - a.insured || a.name.localeCompare(b.name)),
        total: list.reduce((s, r) => s + r.insured, 0),
      }))
      .sort((a, b) => b.total - a.total);
  });
  const grand = computed(() => insurable.value.reduce((s, r) => s + r.insured, 0));
  const unvalued = computed(() => insurable.value.filter(r => !r.insured).length);
  const estimated = computed(() => insurable.value.filter(r => r.replacement !== null).length);
  const today = new Date().toISOString().slice(0, 10);

  function printPage() {
    window.print();
  }

  function downloadCsv() {
    const head = [
      "Room",
      "Location",
      "Item",
      "Maker",
      "Model",
      "Serial",
      "Quantity",
      "Purchased",
      "Price paid",
      "Replacement value",
      "Valued from",
      "Insured value",
    ];
    const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const lines = [head.map(esc).join(",")];
    for (const g of rooms.value)
      for (const r of g.list)
        lines.push(
          [
            g.room,
            r.path,
            r.name,
            r.maker,
            r.model,
            r.serial,
            r.qty,
            r.bought,
            r.paid || "",
            r.replacement ?? "",
            r.valuedFrom,
            r.insured.toFixed(2),
          ]
            .map(esc)
            .join(",")
        );
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `home-inventory-${today}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
</script>

<template>
  <div class="min-h-screen bg-background text-foreground print:bg-white print:text-black">
    <div class="mx-auto max-w-6xl p-4 sm:p-8 print:max-w-none print:p-0">
      <div class="mb-6 flex flex-wrap items-center gap-2 print:hidden">
        <Button variant="outline" size="sm" as-child>
          <NuxtLink to="/home"><MdiArrowLeft class="mr-1" /> Back</NuxtLink>
        </Button>
        <div class="grow" />
        <Button size="sm" variant="outline" :disabled="loading" @click="downloadCsv">
          <MdiDownload class="mr-1" /> Download CSV
        </Button>
        <Button size="sm" :disabled="loading" @click="printPage"
          ><MdiPrinter class="mr-1" /> Print / Save as PDF</Button
        >
      </div>

      <header class="mb-6 border-b pb-4">
        <h1 class="text-3xl font-bold">Home contents inventory</h1>
        <p class="mt-1 text-sm text-muted-foreground print:text-gray-600">Prepared {{ today }} from Homebox.</p>
        <div v-if="!loading" class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-lg border p-3">
            <div class="text-xs uppercase text-muted-foreground">Total insured value</div>
            <div class="text-2xl font-semibold">{{ fmt(grand) }}</div>
          </div>
          <div class="rounded-lg border p-3">
            <div class="text-xs uppercase text-muted-foreground">Items</div>
            <div class="text-2xl font-semibold">{{ insurable.length }}</div>
          </div>
          <div class="rounded-lg border p-3">
            <div class="text-xs uppercase text-muted-foreground">Rooms</div>
            <div class="text-2xl font-semibold">{{ rooms.length }}</div>
          </div>
          <div class="rounded-lg border p-3">
            <div class="text-xs uppercase text-muted-foreground">Estimated values</div>
            <div class="text-2xl font-semibold">{{ estimated }}</div>
          </div>
        </div>
        <p v-if="!loading" class="mt-3 text-xs text-muted-foreground print:text-gray-600">
          Insured value is the current replacement value where one is recorded (an estimate from current Canadian retail
          prices, source noted), otherwise the price paid, times quantity.
          <template v-if="unvalued"> {{ unvalued }} items have no value yet.</template>
        </p>
      </header>

      <p v-if="loading" class="py-16 text-center text-muted-foreground">Gathering items… {{ progress }}</p>

      <section v-for="g in rooms" :key="g.room" class="mb-8 break-inside-avoid-page">
        <div class="mb-2 flex items-baseline gap-3 border-b-2 pb-1">
          <h2 class="text-xl font-semibold">{{ g.room }}</h2>
          <span class="text-sm text-muted-foreground">{{ g.list.length }} items</span>
          <span class="ml-auto font-semibold">{{ fmt(g.total) }}</span>
        </div>
        <table class="w-full text-sm">
          <thead class="text-left text-xs uppercase text-muted-foreground print:text-gray-600">
            <tr>
              <th class="w-12 py-1"></th>
              <th class="py-1">Item</th>
              <th class="hidden py-1 md:table-cell print:table-cell">Purchased</th>
              <th class="py-1 text-right">Paid</th>
              <th class="py-1 text-right">Replacement</th>
              <th class="py-1 text-right">Insured</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in g.list" :key="r.id" class="break-inside-avoid border-t align-top">
              <td class="py-1.5 pr-2">
                <img v-if="r.thumb" :src="r.thumb" alt="" class="size-10 rounded bg-white object-contain" />
              </td>
              <td class="py-1.5 pr-2">
                <NuxtLink :to="`/item/${r.id}`" class="font-medium hover:underline print:no-underline">{{
                  r.name
                }}</NuxtLink>
                <span v-if="r.qty > 1" class="text-muted-foreground"> × {{ r.qty }}</span>
                <div class="text-xs text-muted-foreground print:text-gray-600">
                  {{ [r.maker, r.model].filter(Boolean).join(" · ") }}
                  <template v-if="r.serial"> · S/N {{ r.serial }}</template>
                </div>
                <div class="text-xs text-muted-foreground print:text-gray-600">{{ r.path }}</div>
              </td>
              <td class="hidden py-1.5 pr-2 text-xs md:table-cell print:table-cell">{{ r.bought }}</td>
              <td class="whitespace-nowrap py-1.5 text-right">{{ r.paid ? fmt(r.paid) : "" }}</td>
              <td class="whitespace-nowrap py-1.5 text-right">
                <template v-if="r.replacement">
                  {{ fmt(r.replacement) }}
                  <div
                    v-if="r.valuedFrom"
                    class="max-w-40 truncate text-[10px] text-muted-foreground"
                    :title="r.valuedFrom"
                  >
                    {{ r.valuedFrom }}
                  </div>
                </template>
              </td>
              <td class="whitespace-nowrap py-1.5 text-right font-medium">{{ r.insured ? fmt(r.insured) : "—" }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="vehicles.length" class="mb-8">
        <h2 class="border-b-2 pb-1 text-xl font-semibold">Vehicles (insured separately, not in the total)</h2>
        <ul class="mt-2 text-sm">
          <li v-for="v in vehicles" :key="v.id">
            {{ v.name }}
            <span class="text-muted-foreground">{{
              [v.model, v.serial && `VIN/S/N ${v.serial}`].filter(Boolean).join(" · ")
            }}</span>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
