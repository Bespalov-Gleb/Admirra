import { ref } from 'vue'

const isCollapsed = ref(false)
const isMobileMenuOpen = ref(false)

export function useSidebar() {
  const toggleCollapse = () => {
    isCollapsed.value = !isCollapsed.value
  }

  const toggleMobileMenu = () => {
    isMobileMenuOpen.value = !isMobileMenuOpen.value
  }

  const closeMobileMenu = () => {
    isMobileMenuOpen.value = false
  }

  return {
    isCollapsed,
    toggleCollapse,
    isMobileMenuOpen,
    toggleMobileMenu,
    closeMobileMenu
  }
}

