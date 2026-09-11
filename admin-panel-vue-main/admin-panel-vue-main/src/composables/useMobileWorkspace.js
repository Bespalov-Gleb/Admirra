import { reactive, watchEffect, onUnmounted } from "vue";

// The app header stays outside the scrolling main. Pages supply its mobile scope.
const emptyState = () => ({
  mode: "",
  title: "",
  avatar: "",
  count: 0,
  pickedUp: false,
  alerts: 0,
  openOptions: null,
  optionsLabel: "",
  selectedScope: false,
  selectScope: null,
});
export const mobileWorkspace = reactive(emptyState());
let activeOwner;
export function useMobileWorkspace(getState) {
  const owner = Symbol("mobile-workspace");
  activeOwner = owner;
  watchEffect(() => {
    const state = getState();
    if (activeOwner === owner)
      Object.assign(mobileWorkspace, emptyState(), state);
  });
  onUnmounted(() => {
    if (activeOwner === owner) {
      activeOwner = null;
      Object.assign(mobileWorkspace, emptyState());
    }
  });
}
