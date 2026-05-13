import { ref } from 'vue'

const isCollapsed = ref(false)
const isMobileMenuOpen = ref(false)
const isMobileViewport = ref(false)
let mediaQuery = null
let isMediaQueryInitialized = false

const handleViewportChange = (event) => {
  isMobileViewport.value = event.matches
  if (!event.matches) {
    isMobileMenuOpen.value = false
  }
}

const initSidebarViewport = () => {
  if (isMediaQueryInitialized || typeof window === 'undefined') return
  mediaQuery = window.matchMedia('(max-width: 1023.25px)')
  isMobileViewport.value = mediaQuery.matches
  mediaQuery.addEventListener?.('change', handleViewportChange)
  isMediaQueryInitialized = true
}

export function useSidebar() {
  initSidebarViewport()

  const toggleCollapse = () => {
    if (isMobileViewport.value) return
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
    isMobileViewport,
    isMobileMenuOpen,
    toggleMobileMenu,
    closeMobileMenu
  }
}
