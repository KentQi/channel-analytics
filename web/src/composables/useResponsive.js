/**
 * Responsive layout composable
 * Provides reactive breakpoint detection for mobile/tablet/desktop
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'

const BREAKPOINTS = {
  XS: 576,
  SM: 768,
  MD: 1024,
  LG: 1440
}

export function useResponsive() {
  const windowWidth = ref(window.innerWidth)

  const isXS = computed(() => windowWidth.value < BREAKPOINTS.XS)
  const isSM = computed(() => windowWidth.value >= BREAKPOINTS.XS && windowWidth.value < BREAKPOINTS.SM)
  const isMD = computed(() => windowWidth.value >= BREAKPOINTS.SM && windowWidth.value < BREAKPOINTS.MD)
  const isLG = computed(() => windowWidth.value >= BREAKPOINTS.MD && windowWidth.value < BREAKPOINTS.LG)
  const isXL = computed(() => windowWidth.value >= BREAKPOINTS.LG)

  const isMobile = computed(() => windowWidth.value < BREAKPOINTS.SM)
  const isTablet = computed(() => windowWidth.value >= BREAKPOINTS.SM && windowWidth.value < BREAKPOINTS.MD)
  const isDesktop = computed(() => windowWidth.value >= BREAKPOINTS.MD)

  const currentBreakpoint = computed(() => {
    if (isXS.value) return 'xs'
    if (isSM.value) return 'sm'
    if (isMD.value) return 'md'
    if (isLG.value) return 'lg'
    return 'xl'
  })

  function handleResize() {
    windowWidth.value = window.innerWidth
  }

  onMounted(() => {
    window.addEventListener('resize', handleResize, { passive: true })
    handleResize()
  })

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
  })

  return {
    windowWidth,
    isXS,
    isSM,
    isMD,
    isLG,
    isXL,
    isMobile,
    isTablet,
    isDesktop,
    currentBreakpoint,
    BREAKPOINTS
  }
}

/**
 * CSS class helper for responsive conditional rendering
 * Usage: <div :class="responsiveClass('hide-mobile', 'show-desktop')">
 */
export function useResponsiveClass() {
  const { isMobile, isTablet, isDesktop } = useResponsive()

  function responsiveClass(...classes) {
    return classes.join(' ')
  }

  return {
    isMobile,
    isTablet,
    isDesktop,
    responsiveClass
  }
}
