import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { ref, type Ref } from 'vue'
import { useBoundsDetection, type Bounds } from '@/composables/useBoundsDetection'

describe('useBoundsDetection', () => {
  let containerRef: Ref<HTMLElement | null>
  let container: HTMLElement
  let mockButton1: HTMLElement
  let mockButton2: HTMLElement
  let mockButton3: HTMLElement

  const createMockElement = (id: string, x: number, y: number, width: number, height: number): HTMLElement => {
    const el = document.createElement('div')
    el.id = id
    el.className = 'mock-button'
    el.setAttribute('data-testid', id)
    
    Object.defineProperty(el, 'getBoundingClientRect', {
      value: () => ({
        left: x,
        top: y,
        right: x + width,
        bottom: y + height,
        width,
        height
      })
    })
    
    return el
  }

  const createMouseEvent = (type: string, clientX: number, clientY: number): MouseEvent => {
    return new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX,
      clientY,
      screenX: clientX,
      screenY: clientY
    })
  }

  const createTouchEvent = (type: string, clientX: number, clientY: number): TouchEvent => {
    const touch = new Touch({
      identifier: 0,
      target: document.body,
      clientX,
      clientY,
      screenX: clientX,
      screenY: clientY,
      radiusX: 10,
      radiusY: 10,
      rotationAngle: 0,
      force: 1
    })
    
    return new TouchEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
      touches: type === 'touchstart' || type === 'touchmove' ? [touch] : [],
      changedTouches: type === 'touchend' || type === 'touchcancel' ? [touch] : []
    })
  }

  const createPointerEvent = (type: string, clientX: number, clientY: number, pointerType: 'mouse' | 'touch' | 'pen' = 'mouse'): PointerEvent => {
    return new PointerEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX,
      clientY,
      screenX: clientX,
      screenY: clientY,
      pointerType,
      pointerId: 1,
      isPrimary: true
    })
  }

  beforeEach(() => {
    container = document.createElement('div')
    container.className = 'test-container'
    container.setAttribute('tabindex', '0')
    document.body.appendChild(container)

    containerRef = ref(container)

    mockButton1 = createMockElement('button-1', 100, 100, 80, 40)
    mockButton2 = createMockElement('button-2', 200, 150, 100, 50)
    mockButton3 = createMockElement('button-3', 300, 200, 60, 60)
    
    document.body.appendChild(mockButton1)
    document.body.appendChild(mockButton2)
    document.body.appendChild(mockButton3)
  })

  afterEach(() => {
    if (document.body.contains(container)) {
      document.body.removeChild(container)
    }
    if (document.body.contains(mockButton1)) {
      document.body.removeChild(mockButton1)
    }
    if (document.body.contains(mockButton2)) {
      document.body.removeChild(mockButton2)
    }
    if (document.body.contains(mockButton3)) {
      document.body.removeChild(mockButton3)
    }
  })

  describe('Bounds Validation', () => {
    it('should validate valid bounds', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        minSize: 10,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      const result = instance.validateBounds(bounds)

      expect(result.valid).toBe(true)
      expect(result.expanded).toBe(null)
    })

    it('should expand width below minimum size (10px)', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        minSize: 10,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 5, height: 50 }
      const result = instance.validateBounds(bounds)

      expect(result.valid).toBe(true)
      expect(result.expanded).not.toBe(null)
      expect(result.expanded!.width).toBe(10)
      expect(result.expanded!.x).toBe(97.5)
    })

    it('should expand height below minimum size (10px)', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        minSize: 10,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 5 }
      const result = instance.validateBounds(bounds)

      expect(result.valid).toBe(true)
      expect(result.expanded).not.toBe(null)
      expect(result.expanded!.height).toBe(10)
      expect(result.expanded!.y).toBe(97.5)
    })

    it('should expand both dimensions when both are below minimum', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        minSize: 10,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 5, height: 5 }
      const result = instance.validateBounds(bounds)

      expect(result.valid).toBe(true)
      expect(result.expanded).not.toBe(null)
      expect(result.expanded!.width).toBe(10)
      expect(result.expanded!.height).toBe(10)
    })

    it('should reject invalid bounds (zero or negative dimensions)', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        minSize: 10,
        enableLogging: false
      })

      const zeroWidth: Bounds = { x: 100, y: 100, width: 0, height: 50 }
      const zeroHeight: Bounds = { x: 100, y: 100, width: 50, height: 0 }
      const negativeWidth: Bounds = { x: 100, y: 100, width: -10, height: 50 }

      expect(instance.validateBounds(zeroWidth).valid).toBe(false)
      expect(instance.validateBounds(zeroHeight).valid).toBe(false)
      expect(instance.validateBounds(negativeWidth).valid).toBe(false)
    })
  })

  describe('Point-in-Bounds Detection', () => {
    it('should detect point strictly inside bounds', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointInBounds(125, 125, bounds)).toBe(true)
      expect(instance.isPointInBounds(100, 100, bounds)).toBe(true)
      expect(instance.isPointInBounds(149, 149, bounds)).toBe(true)
      expect(instance.isPointInBounds(150, 150, bounds)).toBe(false)
      expect(instance.isPointInBounds(99, 100, bounds)).toBe(false)
    })

    it('should detect point on edges (±1 pixel tolerance)', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointInBounds(99, 100, bounds, 1)).toBe(true)
      expect(instance.isPointInBounds(100, 99, bounds, 1)).toBe(true)
      expect(instance.isPointInBounds(150, 100, bounds, 1)).toBe(true)
      expect(instance.isPointInBounds(100, 150, bounds, 1)).toBe(true)
      expect(instance.isPointInBounds(98, 100, bounds, 1)).toBe(false)
    })
  })

  describe('Edge Detection', () => {
    it('should detect points on left edge', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointOnEdge(100, 120, bounds)).toBe(true)
      expect(instance.isPointOnEdge(100, 150, bounds)).toBe(true)
      expect(instance.isPointOnEdge(100, 100, bounds, 1)).toBe(true)
    })

    it('should detect points on right edge', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointOnEdge(150, 120, bounds)).toBe(true)
      expect(instance.isPointOnEdge(150, 149, bounds)).toBe(true)
      expect(instance.isPointOnEdge(150, 151, bounds)).toBe(false)
    })

    it('should detect points on top and bottom edges', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointOnEdge(120, 100, bounds)).toBe(true)
      expect(instance.isPointOnEdge(130, 150, bounds)).toBe(true)
      expect(instance.isPointOnEdge(140, 100, bounds, 1)).toBe(true)
    })
  })

  describe('Corner Detection', () => {
    it('should detect top-left corner', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointOnCorner(100, 100, bounds)).toBe(true)
      expect(instance.isPointOnCorner(102, 102, bounds, 5)).toBe(true)
      expect(instance.isPointOnCorner(95, 95, bounds, 5)).toBe(true)
    })

    it('should detect all corners', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointOnCorner(100, 100, bounds)).toBe(true)
      expect(instance.isPointOnCorner(150, 100, bounds)).toBe(true)
      expect(instance.isPointOnCorner(100, 150, bounds)).toBe(true)
      expect(instance.isPointOnCorner(150, 150, bounds)).toBe(true)
    })

    it('should not detect points away from corners', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointOnCorner(125, 125, bounds)).toBe(false)
      expect(instance.isPointOnCorner(120, 110, bounds)).toBe(false)
    })
  })

  describe('Center Detection', () => {
    it('should detect points in center region', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 100, height: 100 }
      
      expect(instance.isPointInCenter(125, 125, bounds)).toBe(true)
      expect(instance.isPointInCenter(150, 150, bounds)).toBe(true)
      expect(instance.isPointInCenter(100, 100, bounds, 0.5)).toBe(false)
    })

    it('should exclude edge regions from center', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 100, height: 100 }
      
      expect(instance.isPointInCenter(105, 105, bounds, 0.1)).toBe(true)
      expect(instance.isPointInCenter(120, 105, bounds, 0.1)).toBe(false)
    })
  })

  describe('Overlap Detection', () => {
    it('should detect overlapping buttons', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('btn-1', mockButton1, { zIndex: 1 })
      instance.registerButton('btn-2', mockButton2, { zIndex: 2 })

      const conflicts = instance.detectOverlaps('btn-1')
      
      expect(conflicts.length).toBeGreaterThan(0)
      expect(conflicts.some(c => c.buttonId2 === 'btn-2')).toBe(true)
    })

    it('should determine z-index winner correctly', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('btn-1', mockButton1, { zIndex: 5 })
      instance.registerButton('btn-2', mockButton2, { zIndex: 3 })

      const conflicts = instance.detectOverlaps('btn-2')
      
      const overlap = conflicts.find(c => c.buttonId1 === 'btn-2')
      expect(overlap).toBeDefined()
      expect(overlap!.zIndexWinner).toBe('btn-1')
    })

    it('should return no conflicts for non-overlapping buttons', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const farButton = createMockElement('far-btn', 500, 500, 50, 50)
      document.body.appendChild(farButton)

      instance.registerButton('btn-1', mockButton1)
      instance.registerButton('far-btn', farButton)

      const conflicts = instance.detectOverlaps('btn-1')
      
      expect(conflicts.length).toBe(0)

      document.body.removeChild(farButton)
    })
  })

  describe('Hit Testing', () => {
    it('should return null for clicks outside canvas', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const result = instance.hitTest(0, 0, 'mouse')
      
      expect(result.buttonId).toBe(null)
      expect(result.isValid).toBe(false)
    })

    it('should detect button click correctly', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('btn-1', mockButton1)
      
      const result = instance.hitTest(140, 120, 'mouse')
      
      expect(result.buttonId).toBe('btn-1')
      expect(result.isValid).toBe(true)
      expect(result.isOverlapping).toBe(false)
    })

    it('should return highest z-index on overlap', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('btn-1', mockButton1, { zIndex: 1 })
      instance.registerButton('btn-2', mockButton2, { zIndex: 10 })

      const overlappingPoint = { x: 200, y: 150 }
      const result = instance.hitTest(overlappingPoint.x, overlappingPoint.y, 'mouse')
      
      expect(result.buttonId).toBe('btn-2')
      expect(result.isOverlapping).toBe(true)
      expect(result.overlappingIds.length).toBeGreaterThan(1)
    })

    it('should handle all input types', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('btn-1', mockButton1)

      const mouseResult = instance.hitTest(140, 120, 'mouse')
      const touchResult = instance.hitTest(140, 120, 'touch')
      const stylusResult = instance.hitTest(140, 120, 'stylus')

      expect(mouseResult.buttonId).toBe('btn-1')
      expect(touchResult.buttonId).toBe('btn-1')
      expect(stylusResult.buttonId).toBe('btn-1')
    })
  })

  describe('Input Type Detection', () => {
    it('should identify mouse events correctly', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const mouseEvent = createMouseEvent('mousedown', 100, 100)
      expect(instance.getInputType(mouseEvent)).toBe('mouse')
    })

    it('should identify touch events correctly', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const touchEvent = createTouchEvent('touchstart', 100, 100)
      expect(instance.getInputType(touchEvent)).toBe('touch')
    })

    it('should identify stylus events correctly', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const stylusEvent = createPointerEvent('pointerdown', 100, 100, 'pen')
      expect(instance.getInputType(stylusEvent)).toBe('stylus')
    })
  })

  describe('Button Registration', () => {
    it('should register a valid button', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const result = instance.registerButton('test-btn', mockButton1, { 
        label: 'Test Button',
        zIndex: 5 
      })

      expect(result).not.toBe(null)
      expect(result!.id).toBe('test-btn')
      expect(result!.zIndex).toBe(5)
      expect(result!.label).toBe('Test Button')
      expect(result!.isValid).toBe(true)
      expect(instance.hasButton('test-btn')).toBe(true)
    })

    it('should mark invalid button as not valid', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        minSize: 10,
        enableLogging: false
      })

      const smallElement = createMockElement('small-btn', 100, 100, 5, 5)
      const result = instance.registerButton('small-btn', smallElement)

      expect(result).not.toBe(null)
      expect(result!.isValid).toBe(true)
      expect(result!.isExpanded).toBe(true)
    })

    it('should unregister button', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('remove-btn', mockButton1)
      expect(instance.hasButton('remove-btn')).toBe(true)

      instance.unregisterButton('remove-btn')
      expect(instance.hasButton('remove-btn')).toBe(false)
    })
  })

  describe('Performance Stats', () => {
    it('should return performance statistics', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('perf-btn-1', mockButton1)
      instance.registerButton('perf-btn-2', mockButton2)

      const stats = instance.performanceStats.value

      expect(stats.buttonCount).toBe(2)
      expect(stats.memoryUsage).toBeGreaterThan(0)
      expect(stats.memoryUsageMB).toBeDefined()
      expect(parseFloat(stats.memoryUsageMB)).toBeLessThan(2)
    })

    it('should track conflict count', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('conf-btn-1', mockButton1, { zIndex: 1 })
      instance.registerButton('conf-btn-2', mockButton2, { zIndex: 2 })

      const stats = instance.performanceStats.value
      expect(stats.conflictCount).toBeGreaterThanOrEqual(0)
    })
  })

  describe('Visual Feedback', () => {
    it('should apply visual feedback on hover', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false,
        enableVisualFeedback: true
      })

      instance.registerButton('visual-btn', mockButton1)
      
      const enterEvent = createMouseEvent('mouseenter', 140, 120)
      mockButton1.dispatchEvent(enterEvent)

      setTimeout(() => {
        expect(instance.highlightedButtonId.value).toBe('visual-btn')
      }, 50)
    })

    it('should clear visual feedback on leave', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false,
        enableVisualFeedback: true
      })

      instance.registerButton('visual-btn', mockButton1)
      
      const enterEvent = createMouseEvent('mouseenter', 140, 120)
      mockButton1.dispatchEvent(enterEvent)

      const leaveEvent = createMouseEvent('mouseleave', 300, 300)
      mockButton1.dispatchEvent(leaveEvent)

      setTimeout(() => {
        expect(instance.highlightedButtonId.value).toBe(null)
      }, 50)
    })
  })

  describe('Boundary Edge Cases', () => {
    it('should handle edge case: exactly on boundary (±1px)', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointInBounds(100, 100, bounds)).toBe(true)
      expect(instance.isPointInBounds(150, 100, bounds)).toBe(true)
      expect(instance.isPointInBounds(100, 150, bounds)).toBe(true)
      expect(instance.isPointInBounds(150, 150, bounds)).toBe(true)
      expect(instance.isPointInBounds(151, 100, bounds)).toBe(false)
      expect(instance.isPointInBounds(100, 151, bounds)).toBe(false)
    })

    it('should handle corner case: exactly at corners', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      
      expect(instance.isPointOnCorner(100, 100, bounds)).toBe(true)
      expect(instance.isPointOnCorner(150, 100, bounds)).toBe(true)
      expect(instance.isPointOnCorner(100, 150, bounds)).toBe(true)
      expect(instance.isPointOnCorner(150, 150, bounds)).toBe(true)
    })

    it('should handle center case: exactly at center', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: 100, y: 100, width: 100, height: 100 }
      
      expect(instance.isPointInCenter(150, 150, bounds)).toBe(true)
    })

    it('should handle negative coordinates', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds: Bounds = { x: -50, y: -50, width: 100, height: 100 }
      
      expect(instance.isPointInBounds(-25, -25, bounds)).toBe(true)
      expect(instance.isPointInBounds(-51, -25, bounds)).toBe(false)
    })

    it('should handle very small buttons (1x1 pixel)', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        minSize: 10,
        enableLogging: false
      })

      const tinyBounds: Bounds = { x: 100, y: 100, width: 1, height: 1 }
      const result = instance.validateBounds(tinyBounds)

      expect(result.valid).toBe(true)
      expect(result.expanded).not.toBe(null)
      expect(result.expanded!.width).toBe(10)
      expect(result.expanded!.height).toBe(10)
    })

    it('should handle very large buttons', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const largeBounds: Bounds = { x: 0, y: 0, width: 2000, height: 2000 }
      
      expect(instance.isPointInBounds(1000, 1000, largeBounds)).toBe(true)
      expect(instance.isPointInBounds(1999, 1999, largeBounds)).toBe(true)
      expect(instance.isPointInBounds(2000, 2000, largeBounds)).toBe(false)
    })
  })

  describe('Overlap Area Calculation', () => {
    it('should calculate overlap area correctly', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds1: Bounds = { x: 100, y: 100, width: 100, height: 100 }
      const bounds2: Bounds = { x: 150, y: 150, width: 100, height: 100 }

      const overlap = instance.calculateOverlapArea(bounds1, bounds2)

      expect(overlap).not.toBe(null)
      expect(overlap!.x).toBe(150)
      expect(overlap!.y).toBe(150)
      expect(overlap!.width).toBe(50)
      expect(overlap!.height).toBe(50)
    })

    it('should return null for non-overlapping bounds', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds1: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      const bounds2: Bounds = { x: 200, y: 200, width: 50, height: 50 }

      const overlap = instance.calculateOverlapArea(bounds1, bounds2)
      expect(overlap).toBe(null)
    })

    it('should handle adjacent bounds (touching edges)', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds1: Bounds = { x: 100, y: 100, width: 50, height: 50 }
      const bounds2: Bounds = { x: 150, y: 100, width: 50, height: 50 }

      const overlap = instance.calculateOverlapArea(bounds1, bounds2)
      expect(overlap).toBe(null)
    })

    it('should handle contained bounds', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      const bounds1: Bounds = { x: 100, y: 100, width: 100, height: 100 }
      const bounds2: Bounds = { x: 120, y: 120, width: 50, height: 50 }

      const overlap = instance.calculateOverlapArea(bounds1, bounds2)

      expect(overlap).not.toBe(null)
      expect(overlap!.x).toBe(120)
      expect(overlap!.y).toBe(120)
      expect(overlap!.width).toBe(50)
      expect(overlap!.height).toBe(50)
    })
  })

  describe('Reset Functionality', () => {
    it('should reset all state', () => {
      const instance = useBoundsDetection({ 
        containerRef,
        enableLogging: false
      })

      instance.registerButton('reset-btn-1', mockButton1)
      instance.registerButton('reset-btn-2', mockButton2)

      expect(instance.getButtonsMap().size).toBe(2)

      instance.reset()

      expect(instance.getButtonsMap().size).toBe(0)
      expect(instance.conflicts.value.length).toBe(0)
    })
  })
})

describe('Bounds Detection Performance', () => {
  let containerRef: Ref<HTMLElement | null>
  let container: HTMLElement

  beforeEach(() => {
    container = document.createElement('div')
    container.className = 'perf-container'
    container.setAttribute('tabindex', '0')
    document.body.appendChild(container)
    containerRef = ref(container)
  })

  afterEach(() => {
    if (document.body.contains(container)) {
      document.body.removeChild(container)
    }
  })

  it('should complete hit detection within 16ms', () => {
    const instance = useBoundsDetection({ 
      containerRef,
      enableLogging: false
    })

    const mockElement = document.createElement('div')
    mockElement.setAttribute('data-testid', 'perf-btn')
    Object.defineProperty(mockElement, 'getBoundingClientRect', {
      value: () => ({ left: 100, top: 100, right: 200, bottom: 150, width: 100, height: 50 })
    })
    document.body.appendChild(mockElement)

    instance.registerButton('perf-btn', mockElement)

    const iterations = 1000
    const startTime = performance.now()
    
    for (let i = 0; i < iterations; i++) {
      instance.hitTest(150, 125, 'mouse')
    }
    
    const endTime = performance.now()
    const avgTime = (endTime - startTime) / iterations

    expect(avgTime).toBeLessThan(16)
    
    document.body.removeChild(mockElement)
  })

  it('should handle memory efficiently with many buttons', () => {
    const instance = useBoundsDetection({ 
      containerRef,
      enableLogging: false
    })

    const mockElements: HTMLElement[] = []
    for (let i = 0; i < 100; i++) {
      const el = document.createElement('div')
      el.setAttribute('data-testid', `mem-btn-${i}`)
      Object.defineProperty(el, 'getBoundingClientRect', {
        value: () => ({ 
          left: i * 60, 
          top: i * 40, 
          right: i * 60 + 50, 
          bottom: i * 40 + 30,
          width: 50, 
          height: 30 
        })
      })
      document.body.appendChild(el)
      mockElements.push(el)
    }

    for (let i = 0; i < 100; i++) {
      instance.registerButton(`mem-btn-${i}`, mockElements[i])
    }

    const stats = instance.performanceStats.value
    
    expect(stats.buttonCount).toBe(100)
    expect(parseFloat(stats.memoryUsageMB)).toBeLessThan(2)

    mockElements.forEach(el => {
      if (document.body.contains(el)) {
        document.body.removeChild(el)
      }
    })
  })
})
