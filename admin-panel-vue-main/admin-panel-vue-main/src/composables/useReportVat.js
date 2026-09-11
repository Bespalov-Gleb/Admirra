import { ref, watch } from "vue";

// Same monetary basis when moving between the list and a project report.
let saved = true;
try {
  saved = localStorage.getItem("admirra:report-vat") !== "false";
} catch {}
const includeVat = ref(saved);
watch(includeVat, (value) => {
  try {
    localStorage.setItem("admirra:report-vat", String(value));
  } catch {}
});
export const useReportVat = () => includeVat;
