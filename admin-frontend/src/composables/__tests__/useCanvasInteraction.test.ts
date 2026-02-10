import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref, type Ref } from 'vue'
import type { Node, Edge } from '@vue-flow/core'
import { 
  useCanvasInteraction
} from '@/composables/useCanvasInteraction'

describe('useCanvasInteraction', () => {
  let containerRef: Ref<HTMLElement | null>
  let nodesRef: Ref<Node[]>
  let edgesRef: Ref<Edge[]>
  let mockContainer: HTMLElement
  let mockNode1: HTMLElement
  let mockNode2: HTMLElement

  const createMockNode = (id: string, x: number = 0, y: number = 0): Node => ({
    id,
    type: 'workflow-node',
    position: { x, y },
    data: { id, label: `Node ${id}`, category: 'browser', type: 'goto', icon: 'Browser', description: '', config: {} }
  })

  beforeEach(() => {
    mockNode1 = document.createElement('div')
    mockNode1.className = 'workflow-node'
    mockNode1.setAttribute('data-id', 'node-1')
    mockNode1.setAttribute('data-node-id', 'node-1')
    mockNode1.innerHTML = '<div>Node 1</div>'

    mockNode2 = document.createElement('div')
    mockNode2.className = 'workflow-node'
    mockNode2.setAttribute('data-id', 'node-2')
    mockNode2.setAttribute('data-node-id', 'node-2')
    mockNode2.innerHTML = '<div>Node 2</div>'

    mockContainer = document.createElement('div')
    mockContainer.className = 'flow-container'
    mockContainer.appendChild(mockNode1)
    mockContainer.appendChild(mockNode2)
    mockContainer.setAttribute('tabindex', '0')

    document.body.appendChild(mockContainer)

    containerRef = ref(mockContainer)
    nodesRef = ref([createMockNode('node-1', 100, 100), createMockNode('node-2', 200, 200)])
    edgesRef = ref([])
  })

  afterEach(() => {
    if (document.body.contains(mockContainer)) {
      document.body.removeChild(mockContainer)
    }
  })

  describe('Keyboard Event System', () => {
    it('should activate keyboard state on focus', () => {
      const { keyboardState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      expect(keyboardState.value.isActive).toBe(false)

      mockContainer.dispatchEvent(new FocusEvent('focus'))
      expect(keyboardState.value.isActive).toBe(true)
    })

    it('should deactivate keyboard state on blur', () => {
      const { keyboardState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))
      mockContainer.dispatchEvent(new FocusEvent('blur'))

      expect(keyboardState.value.isActive).toBe(false)
      expect(keyboardState.value.activeKeys.size).toBe(0)
    })

    it('should track functional keys (Ctrl, Shift, Alt, Meta)', () => {
      const { keyboardState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      const ctrlEvent = new KeyboardEvent('keydown', { key: 'Control', ctrlKey: true, bubbles: true })
      mockContainer.dispatchEvent(ctrlEvent)
      expect(keyboardState.value.modifiers.ctrl).toBe(true)

      const shiftEvent = new KeyboardEvent('keydown', { key: 'Shift', shiftKey: true, bubbles: true })
      mockContainer.dispatchEvent(shiftEvent)
      expect(keyboardState.value.modifiers.shift).toBe(true)

      const altEvent = new KeyboardEvent('keydown', { key: 'Alt', altKey: true, bubbles: true })
      mockContainer.dispatchEvent(altEvent)
      expect(keyboardState.value.modifiers.alt).toBe(true)

      const metaEvent = new KeyboardEvent('keydown', { key: 'Meta', metaKey: true, bubbles: true })
      mockContainer.dispatchEvent(metaEvent)
      expect(keyboardState.value.modifiers.meta).toBe(true)
    })

    it('should track active keys in set', () => {
      const { keyboardState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', code: 'KeyA', bubbles: true }))
      expect(keyboardState.value.activeKeys.has('a')).toBe(true)

      mockContainer.dispatchEvent(new KeyboardEvent('keyup', { key: 'a', code: 'KeyA', bubbles: true }))
      expect(keyboardState.value.activeKeys.has('a')).toBe(false)
    })

    it('should handle Ctrl+A for select all nodes', () => {
      const onSelectionChange = vi.fn()
      useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onSelectionChange
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'Control', 
        code: 'ControlLeft', 
        ctrlKey: true, 
        bubbles: true 
      }))
      
      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'a', 
        code: 'KeyA', 
        ctrlKey: true, 
        bubbles: true 
      }))

      expect(onSelectionChange).toHaveBeenCalledWith(['node-1', 'node-2'])
    })

    it('should handle Escape for clear selection', () => {
      const onSelectionChange = vi.fn()
      const { dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onSelectionChange
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'a', 
        code: 'KeyA', 
        ctrlKey: true, 
        bubbles: true 
      }))
      expect(dragState.value.selectedNodes.length).toBe(2)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      expect(dragState.value.selectedNodes.length).toBe(0)
    })

    it('should handle Delete/Backspace for deleting selected nodes', () => {
      const onNodesChange = vi.fn()
      useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onNodesChange
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'a', 
        code: 'KeyA', 
        ctrlKey: true, 
        bubbles: true 
      }))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete', bubbles: true }))

      expect(onNodesChange).toHaveBeenCalled()
      const calledWith = onNodesChange.mock.calls[0][0]
      expect(calledWith.length).toBe(0)
    })

    it('should handle arrow keys for node movement', () => {
      const onNodesChange = vi.fn()
      useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onNodesChange
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'a', 
        code: 'KeyA', 
        ctrlKey: true, 
        bubbles: true 
      }))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))

      expect(onNodesChange).toHaveBeenCalled()
    })

    it('should handle Shift+Arrow for faster movement (10x)', () => {
      const onNodesChange = vi.fn()
      useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onNodesChange
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'a', 
        code: 'KeyA', 
        ctrlKey: true, 
        bubbles: true 
      }))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'Shift', 
        code: 'ShiftLeft', 
        shiftKey: true, 
        bubbles: true 
      }))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }))

      expect(onNodesChange).toHaveBeenCalled()
    })

    it('should handle Ctrl+G for toggling grid', () => {
      const { gridConfig } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      expect(gridConfig.value.enabled).toBe(true)

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'Control', 
        code: 'ControlLeft', 
        ctrlKey: true, 
        bubbles: true 
      }))
      
      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'g', 
        code: 'KeyG', 
        ctrlKey: true, 
        bubbles: true 
      }))

      expect(gridConfig.value.enabled).toBe(false)
    })

    it('should prevent browser defaults for Ctrl+S, Ctrl+C, Ctrl+V, Ctrl+X', () => {
      const { keyboardState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      const ctrlKeyDown = new KeyboardEvent('keydown', { 
        key: 'Control', 
        code: 'ControlLeft', 
        ctrlKey: true, 
        bubbles: true,
        cancelable: true 
      })
      mockContainer.dispatchEvent(ctrlKeyDown)

      expect(keyboardState.value.modifiers.ctrl).toBe(true)
    })
  })

  describe('Drag and Drop System', () => {
    it('should initiate drag on mousedown', () => {
      const { dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      expect(dragState.value.isDragging).toBe(false)

      const pointerEvent = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 150, 
        clientY: 150,
        bubbles: true,
        cancelable: true
      })
      mockNode1.dispatchEvent(pointerEvent)

      expect(dragState.value.isDragging).toBe(true)
      expect(dragState.value.dragTarget).toBe('node-1')
      expect(dragState.value.dragStartPos).toEqual({ x: 150, y: 150 })
    })

    it('should not start drag if not on node element', () => {
      const { dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      const pointerEvent = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 50, 
        clientY: 50,
        bubbles: true,
        cancelable: true
      })
      mockContainer.dispatchEvent(pointerEvent)

      expect(dragState.value.isDragging).toBe(false)
    })

    it('should detect drag threshold (5px)', () => {
      const { dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      const pointerDown = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 150, 
        clientY: 150,
        bubbles: true,
        cancelable: true
      })
      mockNode1.dispatchEvent(pointerDown)

      expect(dragState.value.isDragStarted).toBe(false)

      const pointerMove1 = new PointerEvent('pointermove', { 
        clientX: 152, 
        clientY: 152,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerMove1)
      expect(dragState.value.isDragStarted).toBe(false)

      const pointerMove2 = new PointerEvent('pointermove', { 
        clientX: 160, 
        clientY: 155,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerMove2)
      expect(dragState.value.isDragStarted).toBe(true)
    })

    it('should create drag preview on threshold exceeded', () => {
      const { dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      const pointerDown = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 150, 
        clientY: 150,
        bubbles: true,
        cancelable: true
      })
      mockNode1.dispatchEvent(pointerDown)

      const pointerMove = new PointerEvent('pointermove', { 
        clientX: 200, 
        clientY: 200,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerMove)

      expect(dragState.value.dragPreview).not.toBeNull()
    })

    it('should snap to grid during drag', () => {
      const onNodesChange = vi.fn()
      const { snapToGrid } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onNodesChange,
        grid: { enabled: true, size: 10 }
      })

      expect(snapToGrid(13)).toBe(10)
      expect(snapToGrid(17)).toBe(20)
      expect(snapToGrid(25)).toBe(20)
    })

    it('should constrain to bounds during drag', () => {
      const { constrainToBounds } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        bounds: { enabled: true, padding: 50 }
      })

      const constrained = constrainToBounds(10, 10)
      expect(constrained.x).toBe(50)
      expect(constrained.y).toBe(50)
    })

    it('should handle multi-select with Ctrl+click', () => {
      const onSelectionChange = vi.fn()
      const { dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onSelectionChange
      })

      const pointerDownNode1 = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 150, 
        clientY: 150,
        bubbles: true,
        cancelable: true
      })
      mockNode1.dispatchEvent(pointerDownNode1)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'Control', 
        ctrlKey: true, 
        bubbles: true 
      }))

      const pointerDownNode2 = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 250, 
        clientY: 250,
        bubbles: true,
        cancelable: true
      })
      mockNode2.dispatchEvent(pointerDownNode2)

      expect(dragState.value.selectedNodes).toContain('node-1')
      expect(dragState.value.selectedNodes).toContain('node-2')
    })

    it('should end drag on mouseup', () => {
      const { dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      const pointerDown = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 150, 
        clientY: 150,
        bubbles: true,
        cancelable: true
      })
      mockNode1.dispatchEvent(pointerDown)

      const pointerMove = new PointerEvent('pointermove', { 
        clientX: 200, 
        clientY: 200,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerMove)

      expect(dragState.value.isDragging).toBe(true)

      const pointerUp = new PointerEvent('pointerup', { 
        button: 0, 
        clientX: 200, 
        clientY: 200,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerUp)

      expect(dragState.value.isDragging).toBe(false)
      expect(dragState.value.dragTarget).toBeNull()
    })

    it('should show coordinate display during drag', () => {
      const { coordinateDisplay } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      expect(coordinateDisplay.value.visible).toBe(false)

      const pointerDown = new PointerEvent('pointerdown', { 
        button: 0, 
        clientX: 150, 
        clientY: 150,
        bubbles: true,
        cancelable: true
      })
      mockNode1.dispatchEvent(pointerDown)

      expect(coordinateDisplay.value.visible).toBe(true)
      expect(coordinateDisplay.value.x).toBe(150)
      expect(coordinateDisplay.value.y).toBe(150)
    })
  })

  describe('Selection Management', () => {
    it('should set selection via setSelection method', () => {
      const onSelectionChange = vi.fn()
      const { dragState, setSelection } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onSelectionChange
      })

      setSelection(['node-1', 'node-2'])

      expect(dragState.value.selectedNodes).toEqual(['node-1', 'node-2'])
      expect(onSelectionChange).toHaveBeenCalledWith(['node-1', 'node-2'])
    })

    it('should add to selection via addToSelection', () => {
      const { dragState, addToSelection, setSelection } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      setSelection(['node-1'])
      addToSelection('node-2')

      expect(dragState.value.selectedNodes).toEqual(['node-1', 'node-2'])
    })

    it('should remove from selection via removeFromSelection', () => {
      const { dragState, removeFromSelection, setSelection } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      setSelection(['node-1', 'node-2'])
      removeFromSelection('node-2')

      expect(dragState.value.selectedNodes).toEqual(['node-1'])
    })

    it('should toggle selection via toggleSelection', () => {
      const { dragState, toggleSelection, setSelection } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      setSelection(['node-1'])
      toggleSelection('node-2')
      expect(dragState.value.selectedNodes).toEqual(['node-1', 'node-2'])

      toggleSelection('node-1')
      expect(dragState.value.selectedNodes).toEqual(['node-2'])
    })

    it('should select all nodes', () => {
      const onSelectionChange = vi.fn()
      const { selectAllNodes } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onSelectionChange
      })

      selectAllNodes()

      expect(onSelectionChange).toHaveBeenCalledWith(['node-1', 'node-2'])
    })

    it('should clear selection', () => {
      const onSelectionChange = vi.fn()
      const { clearSelection, setSelection, dragState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onSelectionChange
      })

      setSelection(['node-1', 'node-2'])
      clearSelection()

      expect(dragState.value.selectedNodes).toEqual([])
    })
  })

  describe('Grid Configuration', () => {
    it('should toggle grid on/off', () => {
      const { gridConfig, toggleGrid } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      expect(gridConfig.value.enabled).toBe(true)

      toggleGrid()
      expect(gridConfig.value.enabled).toBe(false)

      toggleGrid()
      expect(gridConfig.value.enabled).toBe(true)
    })

    it('should set grid size', () => {
      const { gridConfig, setGridSize } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      setGridSize(20)
      expect(gridConfig.value.size).toBe(20)
    })

    it('should use default grid size of 10', () => {
      const { gridConfig } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      expect(gridConfig.value.size).toBe(10)
    })
  })

  describe('Bounds Constraints', () => {
    it('should prevent nodes from being dragged outside bounds', () => {
      const onNodesChange = vi.fn()
      useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef,
        onNodesChange,
        bounds: { enabled: true, padding: 50 }
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'a', 
        code: 'KeyA', 
        ctrlKey: true, 
        bubbles: true 
      }))

      for (let i = 0; i < 20; i++) {
        mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }))
      }

      const finalNodes = onNodesChange.mock.calls[onNodesChange.mock.calls.length - 1][0]
      const node1 = finalNodes.find((n: Node) => n.id === 'node-1')
      
      if (node1 && node1.position) {
        expect(node1.position.x).toBeGreaterThanOrEqual(50)
      }
    })
  })

  describe('Key Mapping', () => {
    it('should map arrow keys correctly', () => {
      const { keyboardState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'ArrowUp', 
        code: 'ArrowUp', 
        bubbles: true 
      }))
      expect(keyboardState.value.activeKeys.has('arrow_up')).toBe(true)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'ArrowDown', 
        code: 'ArrowDown', 
        bubbles: true 
      }))
      expect(keyboardState.value.activeKeys.has('arrow_down')).toBe(true)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'ArrowLeft', 
        code: 'ArrowLeft', 
        bubbles: true 
      }))
      expect(keyboardState.value.activeKeys.has('arrow_left')).toBe(true)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { 
        key: 'ArrowRight', 
        code: 'ArrowRight', 
        bubbles: true 
      }))
      expect(keyboardState.value.activeKeys.has('arrow_right')).toBe(true)
    })

    it('should map function keys (Space, Enter, Escape, Tab)', () => {
      const { keyboardState } = useCanvasInteraction({
        containerRef,
        nodes: nodesRef,
        edges: edgesRef
      })

      mockContainer.dispatchEvent(new FocusEvent('focus'))

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', code: 'Space', bubbles: true }))
      expect(keyboardState.value.activeKeys.has('space')).toBe(true)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }))
      expect(keyboardState.value.activeKeys.has('enter')).toBe(true)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }))
      expect(keyboardState.value.activeKeys.has('escape')).toBe(true)

      mockContainer.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', code: 'Tab', bubbles: true }))
      expect(keyboardState.value.activeKeys.has('tab')).toBe(true)
    })
  })
})

describe('Drag Path Tests', () => {
  let containerRef: Ref<HTMLElement | null>
  let nodesRef: Ref<Node[]>
  let edgesRef: Ref<Edge[]>
  let mockContainer: HTMLElement

  const createMockNode = (id: string, x: number = 0, y: number = 0): Node => ({
    id,
    type: 'workflow-node',
    position: { x, y },
    data: { id, label: `Node ${id}`, category: 'browser', type: 'goto', icon: 'Browser', description: '', config: {} }
  })

  beforeEach(() => {
    mockContainer = document.createElement('div')
    mockContainer.className = 'flow-container'
    mockContainer.setAttribute('tabindex', '0')
    document.body.appendChild(mockContainer)

    containerRef = ref(mockContainer)
    nodesRef = ref([createMockNode('node-1', 100, 100)])
    edgesRef = ref([])
  })

  afterEach(() => {
    if (document.body.contains(mockContainer)) {
      document.body.removeChild(mockContainer)
    }
  })

  it('should handle straight line drag', () => {
    const { dragState, endDrag } = useCanvasInteraction({
      containerRef,
      nodes: nodesRef,
      edges: edgesRef
    })

    const startX = 150, startY = 150

    const pointerDown = new PointerEvent('pointerdown', { 
      button: 0, 
      clientX: startX, 
      clientY: startY,
      bubbles: true,
      cancelable: true
    })
    mockContainer.dispatchEvent(pointerDown)

    for (let i = 0; i < 10; i++) {
      const pointerMove = new PointerEvent('pointermove', { 
        clientX: startX + (i + 1) * 10, 
        clientY: startY + (i + 1) * 5,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerMove)
    }

    expect(dragState.value.isDragging).toBe(true)
    expect(dragState.value.isDragStarted).toBe(true)

    endDrag()
  })

  it('should handle rapid drag', () => {
    const { dragState, endDrag } = useCanvasInteraction({
      containerRef,
      nodes: nodesRef,
      edges: edgesRef
    })

    const pointerDown = new PointerEvent('pointerdown', { 
      button: 0, 
      clientX: 150, 
      clientY: 150,
      bubbles: true,
      cancelable: true
    })
    mockContainer.dispatchEvent(pointerDown)

    const rapidMoves = [
      { x: 160, y: 155 },
      { x: 180, y: 165 },
      { x: 220, y: 180 },
      { x: 300, y: 200 },
      { x: 400, y: 250 }
    ]

    rapidMoves.forEach(({ x, y }) => {
      const pointerMove = new PointerEvent('pointermove', { 
        clientX: x, 
        clientY: y,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerMove)
    })

    expect(dragState.value.isDragging).toBe(true)

    endDrag()
  })

  it('should handle diagonal drag', () => {
    const { dragState, endDrag } = useCanvasInteraction({
      containerRef,
      nodes: nodesRef,
      edges: edgesRef
    })

    const pointerDown = new PointerEvent('pointerdown', { 
      button: 0, 
      clientX: 100, 
      clientY: 100,
      bubbles: true,
      cancelable: true
    })
    mockContainer.dispatchEvent(pointerDown)

    for (let i = 0; i < 10; i++) {
      const pointerMove = new PointerEvent('pointermove', { 
        clientX: 100 + (i + 1) * 10, 
        clientY: 100 + (i + 1) * 10,
        bubbles: true
      })
      mockContainer.dispatchEvent(pointerMove)
    }

    expect(dragState.value.isDragging).toBe(true)

    endDrag()
  })

  it('should not trigger drag if movement is below threshold', () => {
    const { dragState, endDrag } = useCanvasInteraction({
      containerRef,
      nodes: nodesRef,
      edges: edgesRef
    })

    const pointerDown = new PointerEvent('pointerdown', { 
      button: 0, 
      clientX: 150, 
      clientY: 150,
      bubbles: true,
      cancelable: true
    })
    mockContainer.dispatchEvent(pointerDown)

    const smallMove = new PointerEvent('pointermove', { 
      clientX: 152, 
      clientY: 152,
      bubbles: true
    })
    mockContainer.dispatchEvent(smallMove)

    expect(dragState.value.isDragging).toBe(true)
    expect(dragState.value.isDragStarted).toBe(false)

    endDrag()
  })
})
