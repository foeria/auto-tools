import { ref, computed, onMounted, onUnmounted, type Ref } from 'vue'
import type { Node, Edge } from '@vue-flow/core'

export interface DragState {
  isDragging: boolean
  isDragStarted: boolean
  dragTarget: string | null
  dragStartPos: { x: number; y: number }
  currentPos: { x: number; y: number }
  previewPosition: { x: number; y: number } | null
  selectedNodes: string[]
  dragPreview: HTMLElement | null
}

export interface KeyboardState {
  isActive: boolean
  activeKeys: Set<string>
  modifiers: {
    ctrl: boolean
    shift: boolean
    alt: boolean
    meta: boolean
  }
}

export interface GridConfig {
  enabled: boolean
  size: number
}

export interface BoundsConfig {
  enabled: boolean
  padding: number
}

export interface UseCanvasInteractionOptions {
  containerRef: Ref<HTMLElement | null>
  nodes: Ref<Node[]>
  edges: Ref<Edge[]>
  onNodesChange?: (nodes: Node[]) => void
  onNodePositionChange?: (nodeId: string, position: { x: number; y: number }) => void
  onSelectionChange?: (nodeIds: string[]) => void
  grid?: Partial<GridConfig>
  bounds?: Partial<BoundsConfig>
}

const DEFAULT_GRID: GridConfig = {
  enabled: true,
  size: 10
}

const DEFAULT_BOUNDS: BoundsConfig = {
  enabled: true,
  padding: 50
}

const DRAG_THRESHOLD = 5

export function useCanvasInteraction(options: UseCanvasInteractionOptions) {
  const { containerRef, nodes, edges, onNodesChange, onNodePositionChange, onSelectionChange } = options

  const gridConfig = { ...DEFAULT_GRID, ...options.grid }
  const boundsConfig = { ...DEFAULT_BOUNDS, ...options.bounds }

  const keyboardState = ref<KeyboardState>({
    isActive: false,
    activeKeys: new Set(),
    modifiers: {
      ctrl: false,
      shift: false,
      alt: false,
      meta: false
    }
  })

  const dragState = ref<DragState>({
    isDragging: false,
    isDragStarted: false,
    dragTarget: null,
    dragStartPos: { x: 0, y: 0 },
    currentPos: { x: 0, y: 0 },
    previewPosition: null,
    selectedNodes: [],
    dragPreview: null
  })

  const coordinateDisplay = ref({
    visible: false,
    x: 0,
    y: 0
  })

  const keyMap: Record<string, string> = {
    'Escape': 'escape',
    'Enter': 'enter',
    'Backspace': 'backspace',
    'Delete': 'delete',
    'Tab': 'tab',
    'Space': 'space',
    'ArrowUp': 'arrow_up',
    'ArrowDown': 'arrow_down',
    'ArrowLeft': 'arrow_left',
    'ArrowRight': 'arrow_right',
    'KeyA': 'a',
    'KeyC': 'c',
    'KeyV': 'v',
    'KeyX': 'x',
    'KeyY': 'y',
    'KeyZ': 'z',
    'KeyD': 'd',
    'KeyS': 's',
    'KeyG': 'g',
    'KeyL': 'l',
    'KeyF': 'f',
    'KeyH': 'h',
    'KeyK': 'k',
    'KeyR': 'r',
    'KeyW': 'w',
    'Digit1': '1',
    'Digit2': '2',
    'Digit3': '3',
    'Digit4': '4',
    'Digit5': '5',
    'Numpad1': '1',
    'Numpad2': '2',
    'Numpad3': '3',
    'Numpad4': '4',
    'Numpad5': '5'
  }

  const functionalKeys = new Set(['ctrl', 'shift', 'alt', 'meta', 'escape', 'tab', 'enter', 'space'])

  const isFunctionalKey = (key: string): boolean => {
    return functionalKeys.has(key) || key.startsWith('ctrl') || key.startsWith('shift') || 
           key.startsWith('alt') || key.startsWith('meta')
  }

  const snapToGrid = (value: number): number => {
    if (!gridConfig.enabled) return value
    return Math.round(value / gridConfig.size) * gridConfig.size
  }

  const constrainToBounds = (x: number, y: number, nodeWidth: number = 160, nodeHeight: number = 80): { x: number; y: number } => {
    if (!boundsConfig.enabled || !containerRef.value) {
      return { x, y }
    }

    const container = containerRef.value
    const containerRect = container.getBoundingClientRect()

    let constrainedX = x
    let constrainedY = y

    if (x < boundsConfig.padding) {
      constrainedX = boundsConfig.padding
    } else if (x + nodeWidth > containerRect.width - boundsConfig.padding) {
      constrainedX = containerRect.width - boundsConfig.padding - nodeWidth
    }

    if (y < boundsConfig.padding) {
      constrainedY = boundsConfig.padding
    } else if (y + nodeHeight > containerRect.height - boundsConfig.padding) {
      constrainedY = containerRect.height - boundsConfig.padding - nodeHeight
    }

    return { x: constrainedX, y: constrainedY }
  }

  const createDragPreview = (nodeId: string, clientX: number, clientY: number): HTMLElement | null => {
    if (!containerRef.value) return null

    const nodeElement = containerRef.value.querySelector(`[data-node-id="${nodeId}"]`)
    if (!nodeElement) return null

    const preview = nodeElement.cloneNode(true) as HTMLElement
    preview.style.position = 'fixed'
    preview.style.pointerEvents = 'none'
    preview.style.opacity = '0.6'
    preview.style.zIndex = '9999'
    preview.style.transform = 'translate(-50%, -50%)'
    preview.style.transition = 'none'
    preview.classList.add('drag-preview')

    document.body.appendChild(preview)
    updateDragPreviewPosition(preview, clientX, clientY)

    return preview
  }

  const updateDragPreviewPosition = (preview: HTMLElement, clientX: number, clientY: number) => {
    preview.style.left = `${clientX}px`
    preview.style.top = `${clientY}px`
  }

  const removeDragPreview = (preview: HTMLElement | null) => {
    if (preview && preview.parentNode) {
      preview.parentNode.removeChild(preview)
    }
  }

  const handleKeyDown = (event: KeyboardEvent) => {
    if (!keyboardState.value.isActive) return

    const key = event.key.toLowerCase()
    const keyName = keyMap[event.code] || key.toLowerCase()

    keyboardState.value.activeKeys.add(keyName)

    keyboardState.value.modifiers = {
      ctrl: event.ctrlKey || event.metaKey,
      shift: event.shiftKey,
      alt: event.altKey,
      meta: event.metaKey
    }

    if (isFunctionalKey(keyName)) {
      return
    }

    const ctrlPressed = keyboardState.value.modifiers.ctrl
    const shiftPressed = keyboardState.value.modifiers.shift

    switch (keyName) {
      case 'a':
        if (ctrlPressed) {
          event.preventDefault()
          selectAllNodes()
        }
        break
      case 'escape':
        clearSelection()
        break
      case 'delete':
      case 'backspace':
        deleteSelectedNodes()
        break
      case 'g':
        if (ctrlPressed) {
          event.preventDefault()
          toggleGrid()
        }
        break
      case 'arrow_up':
        event.preventDefault()
        moveNodes(0, -1, shiftPressed ? 10 : 1)
        break
      case 'arrow_down':
        event.preventDefault()
        moveNodes(0, 1, shiftPressed ? 10 : 1)
        break
      case 'arrow_left':
        event.preventDefault()
        moveNodes(-1, 0, shiftPressed ? 10 : 1)
        break
      case 'arrow_right':
        event.preventDefault()
        moveNodes(1, 0, shiftPressed ? 10 : 1)
        break
    }
  }

  const handleKeyUp = (event: KeyboardEvent) => {
    const key = event.key.toLowerCase()
    const keyName = keyMap[event.code] || key.toLowerCase()

    keyboardState.value.activeKeys.delete(keyName)

    keyboardState.value.modifiers = {
      ctrl: event.ctrlKey || event.metaKey,
      shift: event.shiftKey,
      alt: event.altKey,
      meta: event.metaKey
    }
  }

  const handleFocus = () => {
    keyboardState.value.isActive = true
  }

  const handleBlur = () => {
    keyboardState.value.isActive = false
    keyboardState.value.activeKeys.clear()
    keyboardState.value.modifiers = {
      ctrl: false,
      shift: false,
      alt: false,
      meta: false
    }
    endDrag()
  }

  const handleMouseDown = (event: PointerEvent) => {
    const target = event.target as HTMLElement
    const nodeElement = target.closest('.workflow-node')
    
    if (!nodeElement) {
      clearSelection()
      return
    }

    const nodeId = nodeElement.getAttribute('data-id') || nodeElement.getAttribute('data-node-id')
    if (!nodeId) return

    event.preventDefault()
    event.stopPropagation()

    const ctrlPressed = keyboardState.value.modifiers.ctrl
    const shiftPressed = keyboardState.value.modifiers.shift

    if (shiftPressed) {
      addToSelection(nodeId)
    } else if (!ctrlPressed) {
      if (!dragState.value.selectedNodes.includes(nodeId)) {
        setSelection([nodeId])
      }
    }

    dragState.value.isDragging = true
    dragState.value.isDragStarted = false
    dragState.value.dragTarget = nodeId
    dragState.value.dragStartPos = { x: event.clientX, y: event.clientY }
    dragState.value.currentPos = { x: event.clientX, y: event.clientY }

    if (ctrlPressed) {
      toggleSelection(nodeId)
    } else if (dragState.value.selectedNodes.length > 0) {
      dragState.value.dragPreview = createDragPreview(dragState.value.dragTarget, event.clientX, event.clientY)
    }

    coordinateDisplay.value.visible = true
    coordinateDisplay.value.x = event.clientX
    coordinateDisplay.value.y = event.clientY

    containerRef.value?.setPointerCapture(event.pointerId)
  }

  const handleMouseMove = (event: PointerEvent) => {
    const dx = event.clientX - dragState.value.dragStartPos.x
    const dy = event.clientY - dragState.value.dragStartPos.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    coordinateDisplay.value.x = event.clientX
    coordinateDisplay.value.y = event.clientY

    if (!dragState.value.isDragging) return

    if (!dragState.value.isDragStarted && distance >= DRAG_THRESHOLD) {
      dragState.value.isDragStarted = true
      if (!dragState.value.dragPreview && dragState.value.dragTarget) {
        dragState.value.dragPreview = createDragPreview(dragState.value.dragTarget, event.clientX, event.clientY)
      }
    }

    if (dragState.value.isDragStarted && dragState.value.dragTarget && dragState.value.dragPreview) {
      updateDragPreviewPosition(dragState.value.dragPreview, event.clientX, event.clientY)

      const container = containerRef.value
      if (container) {
        const rect = container.getBoundingClientRect()
        const relativeX = event.clientX - rect.left
        const relativeY = event.clientY - rect.top

        const snappedX = snapToGrid(relativeX)
        const snappedY = snapToGrid(relativeY)

        const { x: constrainedX, y: constrainedY } = constrainToBounds(snappedX, snappedY)

        dragState.value.previewPosition = { x: constrainedX, y: constrainedY }
      }
    }
  }

  const handleMouseUp = (event: PointerEvent) => {
    if (!dragState.value.isDragging) return

    const dx = event.clientX - dragState.value.dragStartPos.x
    const dy = event.clientY - dragState.value.dragStartPos.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (dragState.value.isDragStarted && distance >= DRAG_THRESHOLD) {
      if (dragState.value.previewPosition) {
        requestAnimationFrame(() => {
          applyNodePositions(dragState.value.previewPosition!)
        })
      }
    }

    removeDragPreview(dragState.value.dragPreview)
    dragState.value.dragPreview = null

    dragState.value.isDragging = false
    dragState.value.isDragStarted = false
    dragState.value.dragTarget = null
    dragState.value.previewPosition = null
    coordinateDisplay.value.visible = false

    containerRef.value?.releasePointerCapture(event.pointerId)
  }

  const applyNodePositions = (offset: { x: number; y: number }) => {
    const selectedNodes = dragState.value.selectedNodes
    if (selectedNodes.length === 0) return

    const updatedNodes = nodes.value.map(node => {
      if (selectedNodes.includes(node.id)) {
        const newPosition = {
          x: (node.position?.x || 0) + offset.x,
          y: (node.position?.y || 0) + offset.y
        }

        const { x, y } = constrainToBounds(newPosition.x, newPosition.y)
        const snappedPosition = {
          x: snapToGrid(x),
          y: snapToGrid(y)
        }

        if (onNodePositionChange) {
          onNodePositionChange(node.id, snappedPosition)
        }

        return {
          ...node,
          position: snappedPosition
        }
      }
      return node
    })

    if (onNodesChange) {
      onNodesChange(updatedNodes)
    }
  }

  const setSelection = (nodeIds: string[]) => {
    dragState.value.selectedNodes = nodeIds
    if (onSelectionChange) {
      onSelectionChange(nodeIds)
    }
  }

  const addToSelection = (nodeId: string) => {
    if (!dragState.value.selectedNodes.includes(nodeId)) {
      setSelection([...dragState.value.selectedNodes, nodeId])
    }
  }

  const removeFromSelection = (nodeId: string) => {
    setSelection(dragState.value.selectedNodes.filter(id => id !== nodeId))
  }

  const toggleSelection = (nodeId: string) => {
    if (dragState.value.selectedNodes.includes(nodeId)) {
      removeFromSelection(nodeId)
    } else {
      addToSelection(nodeId)
    }
  }

  const selectAllNodes = () => {
    const allNodeIds = nodes.value.map(n => n.id)
    setSelection(allNodeIds)
  }

  const clearSelection = () => {
    setSelection([])
  }

  const deleteSelectedNodes = () => {
    const selectedIds = dragState.value.selectedNodes
    if (selectedIds.length === 0) return

    const updatedNodes = nodes.value.filter(n => !selectedIds.includes(n.id))
    edges.value = edges.value.filter(
      e => !selectedIds.includes(e.source) && !selectedIds.includes(e.target)
    )

    if (onNodesChange) {
      onNodesChange(updatedNodes)
    }

    clearSelection()
  }

  const moveNodes = (dx: number, dy: number, multiplier: number = 1) => {
    const selectedIds = dragState.value.selectedNodes
    if (selectedIds.length === 0) return

    const deltaX = dx * gridConfig.size * multiplier
    const deltaY = dy * gridConfig.size * multiplier

    const updatedNodes = nodes.value.map(node => {
      if (selectedIds.includes(node.id)) {
        const currentPos = node.position || { x: 0, y: 0 }
        const newPosition = {
          x: snapToGrid(currentPos.x + deltaX),
          y: snapToGrid(currentPos.y + deltaY)
        }
        const { x, y } = constrainToBounds(newPosition.x, newPosition.y)

        if (onNodePositionChange) {
          onNodePositionChange(node.id, { x, y })
        }

        return { ...node, position: { x, y } }
      }
      return node
    })

    if (onNodesChange) {
      onNodesChange(updatedNodes)
    }
  }

  const toggleGrid = () => {
    gridConfig.enabled = !gridConfig.enabled
  }

  const setGridSize = (size: number) => {
    gridConfig.size = size
  }

  const endDrag = () => {
    removeDragPreview(dragState.value.dragPreview)
    dragState.value.isDragging = false
    dragState.value.isDragStarted = false
    dragState.value.dragTarget = null
    dragState.value.previewPosition = null
    coordinateDisplay.value.visible = false
  }

  const initEventListeners = () => {
    const container = containerRef.value
    if (!container) return

    container.addEventListener('keydown', handleKeyDown, { passive: false })
    container.addEventListener('keyup', handleKeyUp, { passive: false })
    container.addEventListener('focus', handleFocus)
    container.addEventListener('blur', handleBlur)

    container.addEventListener('pointerdown', handleMouseDown, { passive: false })
    container.addEventListener('pointermove', handleMouseMove, { passive: true })
    container.addEventListener('pointerup', handleMouseUp, { passive: false })
    container.addEventListener('pointercancel', handleMouseUp, { passive: false })
    container.addEventListener('pointerleave', handleMouseUp, { passive: false })
  }

  const removeEventListeners = () => {
    const container = containerRef.value
    if (!container) return

    container.removeEventListener('keydown', handleKeyDown)
    container.removeEventListener('keyup', handleKeyUp)
    container.removeEventListener('focus', handleFocus)
    container.removeEventListener('blur', handleBlur)

    container.removeEventListener('pointerdown', handleMouseDown)
    container.removeEventListener('pointermove', handleMouseMove)
    container.removeEventListener('pointerup', handleMouseUp)
    container.removeEventListener('pointercancel', handleMouseUp)
    container.removeEventListener('pointerleave', handleMouseUp)
  }

  onMounted(() => {
    initEventListeners()
  })

  onUnmounted(() => {
    removeEventListeners()
  })

  return {
    keyboardState: computed(() => keyboardState.value),
    dragState: computed(() => dragState.value),
    coordinateDisplay: computed(() => coordinateDisplay.value),
    gridConfig: computed(() => gridConfig),
    snapToGrid,
    constrainToBounds,
    setSelection,
    addToSelection,
    removeFromSelection,
    toggleSelection,
    selectAllNodes,
    clearSelection,
    deleteSelectedNodes,
    moveNodes,
    toggleGrid,
    setGridSize,
    endDrag
  }
}
