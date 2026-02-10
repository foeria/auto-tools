import { ref, computed, onMounted, onUnmounted, type Ref } from 'vue'

export interface Bounds {
  x: number
  y: number
  width: number
  height: number
}

export interface ButtonBounds extends Bounds {
  id: string
  element: HTMLElement | null
  zIndex: number
  isValid: boolean
  isExpanded: boolean
  originalBounds: Bounds | null
  minSize: number
  label?: string
  disabled?: boolean
}

export interface HitTestResult {
  buttonId: string | null
  bounds: Bounds | null
  isValid: boolean
  isExpanded: boolean
  isOverlapping: boolean
  overlappingIds: string[]
  inputType: 'mouse' | 'touch' | 'stylus'
  timestamp: number
}

export interface BoundsConflict {
  buttonId1: string
  buttonId2: string
  overlapArea: Bounds
  zIndexWinner: string
  timestamp: number
}

export interface UseBoundsDetectionOptions {
  containerRef: Ref<HTMLElement | null>
  dpr?: number
  minSize?: number
  enableLogging?: boolean
  enableVisualFeedback?: boolean
}

const DEFAULT_MIN_SIZE = 10
const DEFAULT_DPR = 1
const DETECTION_DELAY = 16

interface PerformanceStats {
  memoryUsage: number
  memoryUsageMB: string
  buttonCount: number
  conflictCount: number
  lastHitResult: HitTestResult | null
  highlightedButton: string | null
  canvasBounds: Bounds | null
  dpr: number
}

export function useBoundsDetection(options: UseBoundsDetectionOptions) {
  const { 
    containerRef, 
    dpr = DEFAULT_DPR, 
    minSize = DEFAULT_MIN_SIZE,
    enableLogging = true,
    enableVisualFeedback = true
  } = options

  const buttons = ref<Map<string, ButtonBounds>>(new Map())
  const canvasBounds = ref<Bounds | null>(null)
  const isDetecting = ref(false)
  const lastHitResult = ref<HitTestResult | null>(null)
  const conflicts = ref<BoundsConflict[]>([])
  const highlightedButtonId = ref<string | null>(null)
  
  const memoryUsage = ref(0)
  let originalStyles: Map<string, string> = new Map()

  function log(level: 'info' | 'warn' | 'error', message: string, data?: unknown): void {
    if (!enableLogging) return
    const timestamp = new Date().toISOString()
    const prefix = `[BoundsDetection][${timestamp}] [${level.toUpperCase()}]`
    switch (level) {
      case 'warn':
        console.warn(prefix, message, data || '')
        break
      case 'error':
        console.error(prefix, message, data || '')
        break
      default:
        console.log(prefix, message, data || '')
    }
  }

  function getDPR(): number {
    if (typeof window !== 'undefined' && window.devicePixelRatio) {
      return window.devicePixelRatio
    }
    return dpr
  }

  function updateCanvasBounds(): Bounds | null {
    if (!containerRef.value) {
      log('warn', 'Container ref is null, cannot update canvas bounds')
      return null
    }

    const rect = containerRef.value.getBoundingClientRect()
    const bounds: Bounds = {
      x: rect.left,
      y: rect.top,
      width: rect.width,
      height: rect.height
    }

    canvasBounds.value = bounds
    log('info', 'Canvas bounds updated', bounds)
    return bounds
  }

  interface ValidationResult {
    valid: boolean
    expanded: Bounds | null
    reason?: string
  }

  function validateBounds(bounds: Bounds): ValidationResult {
    const adjustedBounds = { ...bounds }
    let isExpanded = false
    let reason: string | undefined

    if (bounds.width < minSize) {
      const diff = minSize - bounds.width
      adjustedBounds.x = bounds.x - diff / 2
      adjustedBounds.width = minSize
      isExpanded = true
      reason = `Width expanded from ${bounds.width}px to ${minSize}px`
    }

    if (bounds.height < minSize) {
      const diff = minSize - bounds.height
      adjustedBounds.y = bounds.y - diff / 2
      adjustedBounds.height = minSize
      isExpanded = true
      reason = reason 
        ? `${reason}; Height expanded from ${bounds.height}px to ${minSize}px`
        : `Height expanded from ${bounds.height}px to ${minSize}px`
    }

    if (bounds.width <= 0 || bounds.height <= 0) {
      return { valid: false, expanded: null, reason: 'Invalid dimensions (width or height <= 0)' }
    }

    return { valid: true, expanded: isExpanded ? adjustedBounds : null, reason }
  }

  function isPointInBounds(px: number, py: number, bounds: Bounds, tolerance: number = 0): boolean {
    const adjustedX = bounds.x - tolerance
    const adjustedY = bounds.y - tolerance
    const adjustedWidth = bounds.width + tolerance * 2
    const adjustedHeight = bounds.height + tolerance * 2

    return (
      px >= adjustedX &&
      px <= adjustedX + adjustedWidth &&
      py >= adjustedY &&
      py <= adjustedY + adjustedHeight
    )
  }

  function isPointOnEdge(px: number, py: number, bounds: Bounds, edgeWidth: number = 1): boolean {
    const onLeftEdge = Math.abs(px - bounds.x) <= edgeWidth
    const onRightEdge = Math.abs(px - (bounds.x + bounds.width)) <= edgeWidth
    const onTopEdge = Math.abs(py - bounds.y) <= edgeWidth
    const onBottomEdge = Math.abs(py - (bounds.y + bounds.height)) <= edgeWidth

    const inHorizontal = px >= bounds.x - edgeWidth && px <= bounds.x + bounds.width + edgeWidth
    const inVertical = py >= bounds.y - edgeWidth && py <= bounds.y + bounds.height + edgeWidth

    return (onLeftEdge || onRightEdge) && inVertical || (onTopEdge || onBottomEdge) && inHorizontal
  }

  function isPointOnCorner(px: number, py: number, bounds: Bounds, cornerSize: number = 5): boolean {
    const onTopLeft = Math.abs(px - bounds.x) <= cornerSize && Math.abs(py - bounds.y) <= cornerSize
    const onTopRight = Math.abs(px - (bounds.x + bounds.width)) <= cornerSize && Math.abs(py - bounds.y) <= cornerSize
    const onBottomLeft = Math.abs(px - bounds.x) <= cornerSize && Math.abs(py - (bounds.y + bounds.height)) <= cornerSize
    const onBottomRight = Math.abs(px - (bounds.x + bounds.width)) <= cornerSize && Math.abs(py - (bounds.y + bounds.height)) <= cornerSize

    return onTopLeft || onTopRight || onBottomLeft || onBottomRight
  }

  function isPointInCenter(px: number, py: number, bounds: Bounds, centerThreshold: number = 0.3): boolean {
    const centerX = bounds.x + bounds.width / 2
    const centerY = bounds.y + bounds.height / 2
    const maxDistX = bounds.width * centerThreshold / 2
    const maxDistY = bounds.height * centerThreshold / 2

    return (
      px >= centerX - maxDistX &&
      px <= centerX + maxDistX &&
      py >= centerY - maxDistY &&
      py <= centerY + maxDistY
    )
  }

  function calculateOverlapArea(bounds1: Bounds, bounds2: Bounds): Bounds | null {
    const x1 = Math.max(bounds1.x, bounds2.x)
    const y1 = Math.max(bounds1.y, bounds2.y)
    const x2 = Math.min(bounds1.x + bounds1.width, bounds2.x + bounds2.width)
    const y2 = Math.min(bounds1.y + bounds1.height, bounds2.y + bounds2.height)

    if (x1 >= x2 || y1 >= y2) {
      return null
    }

    return {
      x: x1,
      y: y1,
      width: x2 - x1,
      height: y2 - y1
    }
  }

  function detectOverlaps(buttonId: string): BoundsConflict[] {
    const newConflicts: BoundsConflict[] = []
    const button = buttons.value.get(buttonId)
    
    if (!button || !button.isValid) return []

    buttons.value.forEach((otherButton, otherId) => {
      if (otherId === buttonId || !otherButton.isValid) return

      const overlapArea = calculateOverlapArea(button, otherButton)
      if (overlapArea) {
        const winner = button.zIndex >= otherButton.zIndex ? buttonId : otherId
        newConflicts.push({
          buttonId1: buttonId,
          buttonId2: otherId,
          overlapArea,
          zIndexWinner: winner,
          timestamp: Date.now()
        })

        log('warn', `Overlap detected between ${buttonId} and ${otherId}`, {
          overlapArea,
          zIndexWinner: winner
        })
      }
    })

    return newConflicts
  }

  function getInputType(event: MouseEvent | TouchEvent | PointerEvent): 'mouse' | 'touch' | 'stylus' {
    if ('pointerType' in event) {
      const pointerEvent = event as PointerEvent
      if (pointerEvent.pointerType === 'pen') return 'stylus'
      if (pointerEvent.pointerType === 'touch') return 'touch'
      return 'mouse'
    }
    
    if (event instanceof TouchEvent) {
      return 'touch'
    }
    
    return 'mouse'
  }

  interface Coordinates {
    x: number
    y: number
    screenX: number
    screenY: number
  }

  function getEventCoordinates(event: MouseEvent | TouchEvent | PointerEvent): Coordinates | null {
    let clientX = 0, clientY = 0, screenX = 0, screenY = 0

    if (event instanceof TouchEvent) {
      if (event.touches.length > 0) {
        clientX = event.touches[0]!.clientX
        clientY = event.touches[0]!.clientY
        screenX = event.touches[0]!.screenX
        screenY = event.touches[0]!.screenY
      } else if (event.changedTouches.length > 0) {
        clientX = event.changedTouches[0]!.clientX
        clientY = event.changedTouches[0]!.clientY
        screenX = event.changedTouches[0]!.screenX
        screenY = event.changedTouches[0]!.screenY
      }
    } else {
      clientX = event.clientX
      clientY = event.clientY
      screenX = event.screenX
      screenY = event.screenY
    }

    return { x: clientX, y: clientY, screenX, screenY }
  }

  function hitTest(
    x: number,
    y: number,
    inputType: 'mouse' | 'touch' | 'stylus'
  ): HitTestResult {
    const startTime = performance.now()

    if (!canvasBounds.value) {
      updateCanvasBounds()
    }

    if (canvasBounds.value && !isPointInBounds(x, y, canvasBounds.value)) {
      log('warn', `Click coordinates (${x}, ${y}) are outside canvas bounds`, {
        canvasBounds: canvasBounds.value
      })
      
      return {
        buttonId: null,
        bounds: null,
        isValid: false,
        isExpanded: false,
        isOverlapping: false,
        overlappingIds: [],
        inputType,
        timestamp: Date.now()
      }
    }

    let selectedButton: ButtonBounds | null = null
    let maxZIndex = -Infinity
    const overlappingIds: string[] = []

    const buttonsArray = Array.from(buttons.value.entries())
    for (const [buttonId, button] of buttonsArray) {
      if (!button.isValid) continue

      const bounds = button.originalBounds || button
      if (isPointInBounds(x, y, bounds)) {
        overlappingIds.push(buttonId)

        if (button.zIndex > maxZIndex) {
          maxZIndex = button.zIndex
          selectedButton = button
        }
      }
    }

    if (selectedButton) {
      const isOverlapping = overlappingIds.length > 1
      const buttonId = selectedButton.id
      if (isOverlapping) {
        const newConflicts = detectOverlaps(buttonId)
        conflicts.value = [...conflicts.value, ...newConflicts].slice(-100)
      }

      const endTime = performance.now()
      const detectionTime = endTime - startTime
      if (detectionTime > DETECTION_DELAY) {
        log('warn', `Detection time exceeded 16ms: ${detectionTime.toFixed(2)}ms`)
      }

      const result: HitTestResult = {
        buttonId,
        bounds: {
          x: selectedButton.x,
          y: selectedButton.y,
          width: selectedButton.width,
          height: selectedButton.height
        },
        isValid: selectedButton.isValid,
        isExpanded: selectedButton.isExpanded,
        isOverlapping,
        overlappingIds,
        inputType,
        timestamp: Date.now()
      }

      lastHitResult.value = result

      if (enableVisualFeedback) {
        updateVisualFeedback(buttonId)
      }

      return result
    }

    if (enableVisualFeedback && highlightedButtonId.value) {
      clearVisualFeedback()
    }

    return {
      buttonId: null,
      bounds: null,
      isValid: false,
      isExpanded: false,
      isOverlapping: false,
      overlappingIds: [],
      inputType,
      timestamp: Date.now()
    }
  }

  function updateVisualFeedback(buttonId: string | null): void {
    if (!enableVisualFeedback || !containerRef.value) return

    if (highlightedButtonId.value && highlightedButtonId.value !== buttonId) {
      clearVisualFeedback()
    }

    if (buttonId && highlightedButtonId.value !== buttonId) {
      const button = buttons.value.get(buttonId)
      if (!button || !button.element) return

      const element = button.element
      const currentStyle = element.getAttribute('style') || ''
      originalStyles.set(buttonId, currentStyle)

      element.style.outline = '2px solid #409eff'
      element.style.outlineOffset = '2px'
      element.style.transition = 'outline 0.15s ease, outline-offset 0.15s ease'
      element.style.cursor = 'pointer'

      highlightedButtonId.value = buttonId
      log('info', `Visual feedback enabled for button: ${buttonId}`)
    }
  }

  function clearVisualFeedback(): void {
    if (!enableVisualFeedback) return

    if (highlightedButtonId.value) {
      const button = buttons.value.get(highlightedButtonId.value)
      if (button && button.element) {
        const originalStyle = originalStyles.get(highlightedButtonId.value)
        if (originalStyle !== undefined) {
          button.element.setAttribute('style', originalStyle)
        } else {
          button.element.style.outline = ''
          button.element.style.outlineOffset = ''
          button.element.style.transition = ''
          button.element.style.cursor = ''
        }
      }
      originalStyles.delete(highlightedButtonId.value)
      highlightedButtonId.value = null
    }
  }

  function registerButton(
    id: string,
    element: HTMLElement,
    options?: {
      zIndex?: number
      label?: string
      disabled?: boolean
      customBounds?: Bounds
    }
  ): ButtonBounds | null {
    if (!element) {
      log('error', `Cannot register button with null element: ${id}`)
      return null
    }

    const rect = options?.customBounds 
      ? null 
      : element.getBoundingClientRect()
    
    const bounds: Bounds = options?.customBounds || {
      x: rect!.left,
      y: rect!.top,
      width: rect!.width,
      height: rect!.height
    }

    const validation = validateBounds(bounds)
    if (!validation.valid) {
      log('warn', `Button ${id} has invalid bounds`, { bounds, reason: validation.reason })
    }

    const currentDpr = getDPR()
    const scaledBounds: Bounds = {
      x: bounds.x * currentDpr,
      y: bounds.y * currentDpr,
      width: bounds.width * currentDpr,
      height: bounds.height * currentDpr
    }

    const buttonBounds: ButtonBounds = {
      id,
      element,
      zIndex: options?.zIndex ?? 1,
      isValid: validation.valid,
      isExpanded: validation.expanded !== null,
      originalBounds: validation.expanded ? bounds : null,
      minSize: minSize,
      label: options?.label,
      disabled: options?.disabled ?? false,
      ...scaledBounds
    }

    buttons.value.set(id, buttonBounds)
    log('info', `Button ${id} registered`, {
      bounds: scaledBounds,
      isValid: buttonBounds.isValid,
      isExpanded: buttonBounds.isExpanded,
      originalBounds: buttonBounds.originalBounds
    })

    return buttonBounds
  }

  function unregisterButton(id: string): void {
    if (highlightedButtonId.value === id) {
      clearVisualFeedback()
    }

    const removed = buttons.value.delete(id)
    if (removed) {
      originalStyles.delete(id)
      log('info', `Button ${id} unregistered`)
    }
  }

  function updateButtonBounds(id: string, newBounds: Bounds): ButtonBounds | null {
    const button = buttons.value.get(id)
    if (!button) {
      log('warn', `Button ${id} not found for bounds update`)
      return null
    }

    const validation = validateBounds(newBounds)
    const currentDpr = getDPR()

    const scaledBounds: Bounds = validation.expanded
      ? {
          x: validation.expanded.x * currentDpr,
          y: validation.expanded.y * currentDpr,
          width: validation.expanded.width * currentDpr,
          height: validation.expanded.height * currentDpr
        }
      : {
          x: newBounds.x * currentDpr,
          y: newBounds.y * currentDpr,
          width: newBounds.width * currentDpr,
          height: newBounds.height * currentDpr
        }

    Object.assign(button, scaledBounds)
    button.isValid = validation.valid
    button.isExpanded = validation.expanded !== null
    button.originalBounds = validation.expanded ? newBounds : null

    log('info', `Button ${id} bounds updated`, {
      newBounds: scaledBounds,
      isValid: button.isValid,
      isExpanded: button.isExpanded
    })

    return button
  }

  function handlePointerEvent(event: MouseEvent | TouchEvent | PointerEvent): HitTestResult | null {
    event.preventDefault?.()
    event.stopPropagation?.()

    const coords = getEventCoordinates(event)
    if (!coords) {
      log('warn', 'Could not get event coordinates')
      return null
    }

    const inputType = getInputType(event)
    return hitTest(coords.x, coords.y, inputType)
  }

  function handleEnterLeave(event: MouseEvent | TouchEvent | PointerEvent): void {
    const coords = getEventCoordinates(event)
    if (!coords) return

    let foundButton = false
    buttons.value.forEach((button, buttonId) => {
      if (!button.isValid) return

      const bounds = button.originalBounds || button
      if (isPointInBounds(coords.x, coords.y, bounds)) {
        foundButton = true
        if (highlightedButtonId.value !== buttonId) {
          updateVisualFeedback(buttonId)
        }
      }
    })

    if (!foundButton) {
      clearVisualFeedback()
    }
  }

  function estimateMemoryUsage(): number {
    let totalBytes = 0

    buttons.value.forEach(() => {
      totalBytes += 128
    })

    conflicts.value.forEach(() => {
      totalBytes += 128
    })

    originalStyles.forEach((style) => {
      totalBytes += style.length * 2
    })

    return totalBytes
  }

  function getPerformanceStats(): PerformanceStats {
    const memoryBytes = estimateMemoryUsage()
    memoryUsage.value = memoryBytes

    return {
      memoryUsage: memoryBytes,
      memoryUsageMB: (memoryBytes / (1024 * 1024)).toFixed(2),
      buttonCount: buttons.value.size,
      conflictCount: conflicts.value.length,
      lastHitResult: lastHitResult.value,
      highlightedButton: highlightedButtonId.value,
      canvasBounds: canvasBounds.value,
      dpr: getDPR()
    }
  }

  function reset(): void {
    buttons.value.clear()
    conflicts.value = []
    clearVisualFeedback()
    canvasBounds.value = null
    lastHitResult.value = null
    originalStyles.clear()
    log('info', 'Bounds detection system reset')
  }

  function initEventListeners(): void {
    const container = containerRef.value
    if (!container) {
      log('warn', 'Cannot initialize event listeners: container is null')
      return
    }

    container.addEventListener('pointerdown', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('pointermove', handleEnterLeave as unknown as EventListener, { passive: true })
    container.addEventListener('pointerenter', handleEnterLeave as unknown as EventListener, { passive: true })
    container.addEventListener('pointerleave', handleEnterLeave as unknown as EventListener, { passive: true })
    container.addEventListener('pointerup', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('pointercancel', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('click', handlePointerEvent as unknown as EventListener, { passive: false })

    container.addEventListener('touchstart', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('touchmove', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('touchend', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('touchcancel', handlePointerEvent as unknown as EventListener, { passive: false })

    container.addEventListener('mousedown', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('mousemove', handleEnterLeave as unknown as EventListener, { passive: true })
    container.addEventListener('mouseenter', handleEnterLeave as unknown as EventListener, { passive: true })
    container.addEventListener('mouseleave', handleEnterLeave as unknown as EventListener, { passive: true })
    container.addEventListener('mouseup', handlePointerEvent as unknown as EventListener, { passive: false })
    container.addEventListener('click', handlePointerEvent as unknown as EventListener, { passive: false })

    log('info', 'Event listeners initialized')

    const resizeObserver = new ResizeObserver(() => {
      updateCanvasBounds()
    })
    resizeObserver.observe(container)

    window.addEventListener('resize', () => {
      updateCanvasBounds()
    }, { passive: true })

    window.addEventListener('scroll', () => {
      updateCanvasBounds()
    }, { passive: true })

    updateCanvasBounds()
  }

  function removeEventListeners(): void {
    const container = containerRef.value
    if (container) {
      container.removeEventListener('pointerdown', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('pointermove', handleEnterLeave as unknown as EventListener)
      container.removeEventListener('pointerenter', handleEnterLeave as unknown as EventListener)
      container.removeEventListener('pointerleave', handleEnterLeave as unknown as EventListener)
      container.removeEventListener('pointerup', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('pointercancel', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('click', handlePointerEvent as unknown as EventListener)

      container.removeEventListener('touchstart', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('touchmove', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('touchend', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('touchcancel', handlePointerEvent as unknown as EventListener)

      container.removeEventListener('mousedown', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('mousemove', handleEnterLeave as unknown as EventListener)
      container.removeEventListener('mouseenter', handleEnterLeave as unknown as EventListener)
      container.removeEventListener('mouseleave', handleEnterLeave as unknown as EventListener)
      container.removeEventListener('mouseup', handlePointerEvent as unknown as EventListener)
      container.removeEventListener('click', handlePointerEvent as unknown as EventListener)
    }

    clearVisualFeedback()
    log('info', 'Event listeners removed')
  }

  onMounted(() => {
    initEventListeners()
    log('info', 'Bounds detection system mounted')
  })

  onUnmounted(() => {
    removeEventListeners()
    reset()
    log('info', 'Bounds detection system unmounted')
  })

  return {
    buttons: computed(() => buttons.value),
    canvasBounds: computed(() => canvasBounds.value),
    isDetecting: computed(() => isDetecting.value),
    lastHitResult: computed(() => lastHitResult.value),
    conflicts: computed(() => conflicts.value),
    highlightedButtonId: computed(() => highlightedButtonId.value),
    performanceStats: computed(() => getPerformanceStats()),
    
    registerButton,
    unregisterButton,
    updateButtonBounds,
    hitTest,
    validateBounds,
    isPointInBounds,
    isPointOnEdge,
    isPointOnCorner,
    isPointInCenter,
    detectOverlaps,
    calculateOverlapArea,
    updateCanvasBounds,
    getPerformanceStats,
    clearVisualFeedback,
    getInputType,
    reset,
    getButtonsMap: () => buttons.value,
    hasButton: (id: string) => buttons.value.has(id)
  }
}
